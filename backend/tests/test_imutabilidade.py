"""Imutabilidade garantida pelo banco, não pelo código da aplicação.

Estes testes atacam as tabelas por SQL direto, passando por cima de qualquer regra de
serviço. É o que sustenta a afirmação do TCC: o histórico de consentimentos não pode ser
reescrito nem por quem tem acesso ao banco pela aplicação.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.session import engine
from app.models import Consentimento, DecisaoConsentimento, FormaObtencao, TipoTermo
from app.repositories import consultas


@pytest.fixture
def consentimento_gravado(sessao, usuario_direto, cliente_direto):
    usuario = usuario_direto()
    cliente = cliente_direto(usuario)
    termo = consultas.termo_vigente(sessao, TipoTermo.cliente)
    assert termo is not None
    registro = Consentimento(
        cliente_id=cliente.id,
        usuario_id=usuario.id,
        decisao=DecisaoConsentimento.aceito,
        termo_id=termo.id,
        versao_termo=termo.versao,
        forma_obtencao=FormaObtencao.tela_dispositivo,
        confirmado_por=cliente.nome,
        observacao="",
    )
    sessao.add(registro)
    sessao.commit()
    sessao.refresh(registro)
    return usuario, cliente, registro


def test_update_em_consentimento_e_recusado(consentimento_gravado):
    _, _, registro = consentimento_gravado
    with engine.begin() as conexao, pytest.raises(IntegrityError) as erro:
        conexao.execute(
            text("UPDATE consentimentos SET decisao = 'revogado' WHERE id = :id"),
            {"id": registro.id},
        )
    assert "imutaveis" in str(erro.value)


def test_delete_isolado_de_consentimento_e_recusado(consentimento_gravado):
    _, _, registro = consentimento_gravado
    with engine.begin() as conexao, pytest.raises(IntegrityError):
        conexao.execute(
            text("DELETE FROM consentimentos WHERE id = :id"), {"id": registro.id}
        )


def test_exclusao_do_cliente_leva_o_consentimento(consentimento_gravado):
    """O art. 18 precisa funcionar: em cascata, a exclusão é permitida."""
    _, cliente, _ = consentimento_gravado
    with engine.begin() as conexao:
        conexao.execute(text("DELETE FROM clientes WHERE id = :id"), {"id": cliente.id})
        restantes = conexao.execute(
            text("SELECT count(*) FROM consentimentos WHERE cliente_id = :id"),
            {"id": cliente.id},
        ).scalar()
    assert restantes == 0


def test_exclusao_da_conta_leva_o_consentimento(consentimento_gravado):
    usuario, _, _ = consentimento_gravado
    with engine.begin() as conexao:
        conexao.execute(text("DELETE FROM usuarios WHERE id = :id"), {"id": usuario.id})
        restantes = conexao.execute(
            text("SELECT count(*) FROM consentimentos WHERE usuario_id = :id"),
            {"id": usuario.id},
        ).scalar()
    assert restantes == 0


def test_texto_do_termo_publicado_nao_muda():
    with engine.begin() as conexao, pytest.raises(IntegrityError) as erro:
        conexao.execute(
            text("UPDATE termos SET titulo = 'outro título' WHERE tipo = 'cliente'")
        )
    assert "publique uma nova versao" in str(erro.value)


def test_marcacao_de_vigencia_pode_mudar():
    """Publicar uma versão nova exige mexer na vigência — e só nela."""
    with engine.begin() as conexao:
        conexao.execute(
            text("UPDATE termos SET vigente = false WHERE tipo = 'cliente' AND versao = '1.0'")
        )
        conexao.execute(
            text("UPDATE termos SET vigente = true WHERE tipo = 'cliente' AND versao = '1.0'")
        )


def test_apenas_uma_versao_vigente_por_tipo():
    with engine.begin() as conexao, pytest.raises(IntegrityError):
        conexao.execute(
            text("UPDATE termos SET vigente = true WHERE tipo = 'cliente' AND versao = '0.9'")
        )


def test_apenas_uma_simulacao_preferida_por_cliente(sessao, usuario_direto, cliente_direto):
    """O índice único parcial não depende da aplicação se comportar bem."""
    from app.models import Imagem, Simulacao, StatusSimulacao, TipoImagem

    usuario = usuario_direto()
    cliente = cliente_direto(usuario)
    termo = consultas.termo_vigente(sessao, TipoTermo.cliente)
    assert termo is not None
    registro = Consentimento(
        cliente_id=cliente.id,
        usuario_id=usuario.id,
        decisao=DecisaoConsentimento.aceito,
        termo_id=termo.id,
        versao_termo=termo.versao,
        forma_obtencao=FormaObtencao.tela_dispositivo,
        confirmado_por=cliente.nome,
    )
    sessao.add(registro)
    sessao.flush()

    def nova_simulacao(preferida: bool) -> Simulacao:
        sufixo = uuid.uuid4().hex[:8]
        entrada = Imagem(
            usuario_id=usuario.id,
            cliente_id=cliente.id,
            tipo=TipoImagem.entrada,
            chave_objeto=f"teste/{cliente.id}/{sufixo}-entrada.jpg",
            mime="image/jpeg",
            bytes=10,
            largura=720,
            altura=960,
        )
        saida = Imagem(
            usuario_id=usuario.id,
            cliente_id=cliente.id,
            tipo=TipoImagem.saida,
            chave_objeto=f"teste/{cliente.id}/{sufixo}-saida.jpg",
            mime="image/jpeg",
            bytes=10,
            largura=720,
            altura=960,
        )
        sessao.add_all([entrada, saida])
        sessao.flush()
        return Simulacao(
            cliente_id=cliente.id,
            usuario_id=usuario.id,
            consentimento_id=registro.id,
            img_entrada_id=entrada.id,
            img_saida_id=saida.id,
            estilo="Bob curto",
            cor="Loiro mel",
            status=StatusSimulacao.concluida,
            provedor="teste",
            modelo_ia="teste",
            preferida=preferida,
        )

    sessao.add(nova_simulacao(True))
    sessao.commit()
    sessao.add(nova_simulacao(True))
    with pytest.raises(IntegrityError):
        sessao.commit()
    sessao.rollback()
