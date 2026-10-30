"""Integridade entre banco e armazenamento: nada de registro órfão nem arquivo esquecido.

A pergunta que estes testes respondem é simples e incômoda: depois de excluir, sobra
alguma coisa? Um registro apontando para o vazio, ou um arquivo de imagem que ninguém
mais referencia — e que, no caso deste sistema, é a fotografia de uma pessoa que pediu
para ser apagada (art. 18, VI da LGPD).

A verificação é feita nos dois lugares ao mesmo tempo: contagem no banco e varredura do
diretório do storage.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import obter_config
from app.db.session import engine
from tests.fabricas import arquivo_de_foto

ACEITE = {
    "decisao": "aceito",
    "formaObtencao": "tela_dispositivo",
    "confirmadoPor": "Marina Alves",
    "observacao": "",
}


def contar(tabela: str) -> int:
    with engine.begin() as conexao:
        return conexao.execute(text(f"SELECT count(*) FROM {tabela}")).scalar_one()


def arquivos_no_storage() -> set[Path]:
    raiz = Path(obter_config().storage_dir)
    if not raiz.exists():
        return set()
    return {caminho for caminho in raiz.rglob("*") if caminho.is_file()}


def amanha() -> str:
    base = datetime.now(UTC) + timedelta(days=1)
    return base.replace(hour=10, minute=0, second=0, microsecond=0).isoformat()


@pytest.fixture
def cliente_completo(cliente_http: TestClient, conta):
    """Um cliente com absolutamente tudo pendurado nele."""
    cabecalhos, usuario = conta()
    cliente = cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": "Marina Alves", "telefone": "1"}
    ).json()
    cliente_http.post(
        f"/api/v1/clientes/{cliente['id']}/consentimentos", headers=cabecalhos, json=ACEITE
    )
    cliente_http.post(
        f"/api/v1/clientes/{cliente['id']}/foto",
        headers=cabecalhos,
        files={"arquivo": ("perfil.jpg", arquivo_de_foto()["foto"][1], "image/jpeg")},
    )
    simulacao = cliente_http.post(
        "/api/v1/simulacoes",
        headers=cabecalhos,
        data={
            "clienteId": cliente["id"],
            "corte": "Bob curto",
            "cor": "Ruivo intenso",
            "observacoes": "",
        },
        files=arquivo_de_foto(),
    ).json()
    atendimento = cliente_http.post(
        "/api/v1/atendimentos",
        headers=cabecalhos,
        json={
            "clienteId": cliente["id"],
            "simulacaoId": simulacao["id"],
            "descricao": "Coloração",
            "dataServico": date.today().isoformat(),
            "observacoes": "",
        },
    ).json()
    cliente_http.post(
        "/api/v1/agendamentos",
        headers=cabecalhos,
        json={
            "clienteId": cliente["id"],
            "dataHora": amanha(),
            "servico": "Retoque",
            "duracaoMin": 60,
            "lembrete": False,
        },
    )
    return {
        "cabecalhos": cabecalhos,
        "usuario": usuario,
        "cliente": cliente,
        "simulacao": simulacao,
        "atendimento": atendimento,
    }


def test_o_cenario_realmente_criou_tudo(cliente_completo):
    """Canário: sem dado criado, os testes de exclusão passariam de graça."""
    assert contar("clientes") == 1
    assert contar("consentimentos") >= 1
    assert contar("imagens") >= 2, "esperado ao menos foto de perfil e entrada da simulação"
    assert contar("simulacoes") == 1
    assert contar("atendimentos") == 1
    assert contar("agendamentos") == 1
    assert arquivos_no_storage(), "nenhum arquivo foi gravado no storage"


def test_excluir_cliente_nao_deixa_orfao_no_banco(cliente_http: TestClient, cliente_completo):
    """Art. 18, VI — a exclusão tem de alcançar tudo o que pende do cliente."""
    resposta = cliente_http.delete(
        f"/api/v1/clientes/{cliente_completo['cliente']['id']}",
        headers=cliente_completo["cabecalhos"],
    )
    assert resposta.status_code == 204

    for tabela in ("clientes", "consentimentos", "imagens", "simulacoes", "agendamentos"):
        assert contar(tabela) == 0, f"sobrou registro em {tabela}"

    # O atendimento é histórico de serviço do profissional, e sobrevive — mas sem
    # referência pendente para a simulação apagada.
    with engine.begin() as conexao:
        pendentes = conexao.execute(
            text("SELECT count(*) FROM atendimentos WHERE simulacao_id IS NOT NULL")
        ).scalar_one()
    assert pendentes == 0, "atendimento ficou apontando para simulação inexistente"


def test_excluir_cliente_nao_deixa_arquivo_no_storage(cliente_http: TestClient, cliente_completo):
    """O arquivo é a fotografia de uma pessoa: apagar a linha e deixar o objeto não serve."""
    antes = arquivos_no_storage()
    assert antes, "o cenário precisa de arquivos gravados"

    cliente_http.delete(
        f"/api/v1/clientes/{cliente_completo['cliente']['id']}",
        headers=cliente_completo["cabecalhos"],
    )

    depois = arquivos_no_storage()
    assert depois == set(), f"arquivos esquecidos no storage: {sorted(str(a) for a in depois)}"


def test_excluir_conta_nao_deixa_nada(cliente_http: TestClient, cliente_completo):
    cliente_http.request(
        "DELETE",
        "/api/v1/usuarios/me",
        headers=cliente_completo["cabecalhos"],
        json={"senha": "senha-de-teste-123"},
    )

    for tabela in (
        "usuarios",
        "clientes",
        "consentimentos",
        "imagens",
        "simulacoes",
        "atendimentos",
        "agendamentos",
        "ciencias",
    ):
        assert contar(tabela) == 0, f"sobrou registro em {tabela} depois de excluir a conta"
    assert arquivos_no_storage() == set(), "sobrou arquivo depois de excluir a conta"


def test_excluir_imagens_preserva_o_historico(cliente_http: TestClient, cliente_completo):
    """Art. 18, VI sem perder o art. 37: apagar imagem não apaga o registro do serviço."""
    resposta = cliente_http.delete(
        f"/api/v1/clientes/{cliente_completo['cliente']['id']}/simulacoes",
        headers=cliente_completo["cabecalhos"],
    )
    assert resposta.status_code in (200, 204)

    assert contar("simulacoes") == 0
    assert contar("atendimentos") == 1, "o histórico de atendimento foi apagado junto"
    assert contar("consentimentos") >= 1, "o registro de consentimento foi apagado junto"

    historico = cliente_http.get(
        f"/api/v1/clientes/{cliente_completo['cliente']['id']}/historico",
        headers=cliente_completo["cabecalhos"],
    ).json()
    assert len(historico) == 1
    assert historico[0]["simulacaoId"] is None, "o vínculo com a simulação não foi anulado"


def test_termos_sobrevivem_a_exclusao_de_tudo(cliente_http: TestClient, cliente_completo):
    """Os termos são dado de sistema, vindos da migration: não pertencem a conta alguma."""
    antes = contar("termos")
    assert antes >= 1

    cliente_http.request(
        "DELETE",
        "/api/v1/usuarios/me",
        headers=cliente_completo["cabecalhos"],
        json={"senha": "senha-de-teste-123"},
    )
    assert contar("termos") == antes


# --- Exclusão de uma simulação só ----------------------------------------------


def chaves_da_simulacao(simulacao_id: str) -> set[Path]:
    """Os arquivos (entrada e saída) de uma simulação, no storage."""
    with engine.begin() as conexao:
        chaves = conexao.execute(
            text(
                "SELECT i.chave_objeto FROM imagens i JOIN simulacoes s"
                " ON i.id IN (s.img_entrada_id, s.img_saida_id) WHERE s.id = :id"
            ),
            {"id": simulacao_id},
        ).scalars()
        return {Path(obter_config().storage_dir) / chave for chave in chaves}


def nova_simulacao(cliente_http: TestClient, cabecalhos, cliente_id: str, **extra) -> dict:
    criada = cliente_http.post(
        "/api/v1/simulacoes",
        headers=cabecalhos,
        data={"clienteId": cliente_id, "corte": "Pixie", "cor": "Loiro", "observacoes": "", **extra},
        files=arquivo_de_foto(),
    )
    assert criada.status_code == 202, criada.text
    # O TestClient roda a geração em segundo plano ao fim da requisição.
    return cliente_http.get(f"/api/v1/simulacoes/{criada.json()['id']}", headers=cabecalhos).json()


def test_excluir_uma_simulacao_apaga_so_ela_e_as_imagens_dela(cliente_http: TestClient, cliente_completo):
    cabecalhos = cliente_completo["cabecalhos"]
    cliente_id = cliente_completo["cliente"]["id"]
    alvo = cliente_completo["simulacao"]["id"]
    # A excluída é a preferida e está vinculada ao atendimento: os casos que mais pesam.
    assert cliente_http.post(f"/api/v1/simulacoes/{alvo}/preferida", headers=cabecalhos).status_code == 200
    outra = nova_simulacao(cliente_http, cabecalhos, cliente_id)
    assert outra["status"] == "concluida"

    arquivos_do_alvo = chaves_da_simulacao(alvo)
    arquivos_da_outra = chaves_da_simulacao(outra["id"])
    assert len(arquivos_do_alvo) == 2 and all(a.exists() for a in arquivos_do_alvo)
    antes = arquivos_no_storage()
    imagens_antes = contar("imagens")

    resposta = cliente_http.delete(f"/api/v1/simulacoes/{alvo}", headers=cabecalhos)
    assert resposta.status_code == 204, resposta.text

    # Banco: a simulação e as duas imagens dela saíram; nada mais.
    assert cliente_http.get(f"/api/v1/simulacoes/{alvo}", headers=cabecalhos).status_code == 404
    restantes = cliente_http.get(f"/api/v1/clientes/{cliente_id}/simulacoes", headers=cabecalhos).json()
    assert [s["id"] for s in restantes] == [outra["id"]]
    assert contar("imagens") == imagens_antes - 2
    # Storage: só os dois arquivos dela; a outra simulação e a foto de perfil ficam.
    assert arquivos_no_storage() == antes - arquivos_do_alvo
    assert all(a.exists() for a in arquivos_da_outra)
    cliente = cliente_http.get(f"/api/v1/clientes/{cliente_id}", headers=cabecalhos).json()
    assert cliente["fotoUri"], "a foto de perfil não é da simulação e não pode sair"
    # O atendimento é histórico de serviço: continua, sem apontar para o que não existe.
    historico = cliente_http.get(f"/api/v1/clientes/{cliente_id}/historico", headers=cabecalhos).json()
    assert [(h["id"], h["simulacaoId"]) for h in historico] == [(cliente_completo["atendimento"]["id"], None)]
    # E o consentimento, que é o registro da decisão, também.
    assert contar("consentimentos") >= 1

    # Repetir a exclusão: já não existe.
    assert cliente_http.delete(f"/api/v1/simulacoes/{alvo}", headers=cabecalhos).status_code == 404


def test_simulacao_em_processamento_nao_e_excluida(cliente_http: TestClient, cliente_completo):
    cabecalhos = cliente_completo["cabecalhos"]
    falhou = nova_simulacao(cliente_http, cabecalhos, cliente_completo["cliente"]["id"], demoFalharIa="true")
    assert falhou["status"] == "falhou"
    # Uma geração ainda em curso: a tarefa em segundo plano vai gravar nela.
    with engine.begin() as conexao:
        conexao.execute(text("UPDATE simulacoes SET status = 'processando' WHERE id = :id"), {"id": falhou["id"]})

    recusada = cliente_http.delete(f"/api/v1/simulacoes/{falhou['id']}", headers=cabecalhos)
    assert recusada.status_code == 409
    assert recusada.json()["erro"]["codigo"] == "simulacao_em_processamento"
    assert cliente_http.get(f"/api/v1/simulacoes/{falhou['id']}", headers=cabecalhos).status_code == 200
    assert chaves_da_simulacao(falhou["id"]), "a foto de entrada não pode sair com a exclusão recusada"

    # Terminada (aqui, com falha), pode ser excluída, e a foto enviada sai junto.
    with engine.begin() as conexao:
        conexao.execute(text("UPDATE simulacoes SET status = 'falhou' WHERE id = :id"), {"id": falhou["id"]})
    arquivos = chaves_da_simulacao(falhou["id"])
    assert len(arquivos) == 1, "simulação que falhou só tem a foto de entrada"
    assert cliente_http.delete(f"/api/v1/simulacoes/{falhou['id']}", headers=cabecalhos).status_code == 204
    assert not any(a.exists() for a in arquivos)
