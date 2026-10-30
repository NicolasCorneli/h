"""Registro e avaliação do consentimento de imagem (RNF05).

Aqui ficam as decisões que não podem estar no aplicativo:

* a **versão do termo** é a vigente no servidor, nunca a que o aplicativo informar;
* **menor de 18** só tem decisão registrada com responsável legal identificado;
* a avaliação da captura (`liberar_captura`) é pré-condição de qualquer simulação.

Nenhum registro é alterado: revogar é inserir uma linha nova (o gatilho do banco recusa
`UPDATE`), o que preserva a trilha histórica exigida pelo art. 37 da LGPD.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.erros import ConsentimentoInvalido, NaoEncontrado, ValidacaoFalhou
from app.models import Cliente, Consentimento, DecisaoConsentimento, TipoTermo, Usuario
from app.repositories import consultas
from app.schemas.consentimento import (
    BloqueioOut,
    ConsentimentoOut,
    NovaDecisao,
    ResponsavelLegal,
    ResumoConsentimentoOut,
)
from app.services.regras_consentimento import (
    avaliar_captura,
    exige_responsavel,
    faixa_etaria,
    precisa_revalidar,
    status_de,
)

log = logging.getLogger(__name__)

ROTULOS = {
    "pendente": "Consentimento pendente",
    "aceito": "Consentimento aceito",
    "recusado": "Uso de imagem recusado",
    "revogado": "Consentimento cancelado",
}


def _como_saida(registro: Consentimento | None) -> ConsentimentoOut | None:
    if registro is None:
        return None
    responsavel = (
        ResponsavelLegal(nome=registro.responsavel_nome, parentesco=registro.responsavel_parentesco)
        if registro.responsavel_nome and registro.responsavel_parentesco
        else None
    )
    return ConsentimentoOut(
        id=registro.id,
        cliente_id=registro.cliente_id,
        usuario_id=registro.usuario_id,
        decisao=registro.decisao,
        versao_termo=registro.versao_termo,
        registrado_em=registro.registrado_em,
        forma_obtencao=registro.forma_obtencao,
        confirmado_por=registro.confirmado_por,
        responsavel=responsavel,
        faixa_etaria=registro.faixa_etaria,
        observacao=registro.observacao,
    )


def _versao_vigente(sessao: Session) -> str:
    termo = consultas.termo_vigente(sessao, TipoTermo.cliente)
    if termo is None:
        raise NaoEncontrado("Nenhuma versão do termo do cliente está publicada.")
    return termo.versao


def resumo(sessao: Session, cliente: Cliente) -> ResumoConsentimentoOut:
    registro = consultas.ultimo_consentimento(sessao, cliente.id)
    return montar_resumo(cliente, registro, _versao_vigente(sessao))


def montar_resumo(
    cliente: Cliente, registro: Consentimento | None, versao_vigente: str
) -> ResumoConsentimentoOut:
    decisao = registro.decisao if registro else None
    versao_aceita = registro.versao_termo if registro else None
    status = status_de(decisao)
    revalidar = precisa_revalidar(decisao, versao_aceita, versao_vigente)
    bloqueio = avaliar_captura(cliente.nome, decisao, versao_aceita, versao_vigente)

    return ResumoConsentimentoOut(
        status=status,
        rotulo="Aceito em versão anterior" if revalidar else ROTULOS[status],
        revalidar=revalidar,
        registro=_como_saida(registro),
        versao_vigente=versao_vigente,
        exige_responsavel=exige_responsavel(cliente.data_nascimento),
        bloqueio=(
            BloqueioOut(motivo=bloqueio.motivo, titulo=bloqueio.titulo, descricao=bloqueio.descricao)
            if bloqueio
            else None
        ),
    )


def historico(sessao: Session, cliente: Cliente) -> list[ConsentimentoOut]:
    registros = consultas.historico_consentimentos(sessao, cliente.id)
    return [saida for saida in (_como_saida(r) for r in registros) if saida is not None]


def registrar_decisao(
    sessao: Session, usuario: Usuario, cliente: Cliente, dados: NovaDecisao
) -> ResumoConsentimentoOut:
    anterior = consultas.ultimo_consentimento(sessao, cliente.id)

    if dados.decisao is DecisaoConsentimento.revogado:
        if anterior is None or anterior.decisao is not DecisaoConsentimento.aceito:
            raise ValidacaoFalhou(
                "Não há consentimento ativo para cancelar.",
                codigo="sem_consentimento_ativo",
            )
        # A revogação se refere ao texto que foi aceito, não ao texto vigente hoje.
        termo = anterior.termo
    else:
        termo = consultas.termo_vigente(sessao, TipoTermo.cliente)
        if termo is None:
            raise NaoEncontrado("Nenhuma versão do termo do cliente está publicada.")

    responsavel_obrigatorio = exige_responsavel(cliente.data_nascimento)
    if responsavel_obrigatorio and dados.responsavel is None:
        raise ValidacaoFalhou(
            "Cliente menor de 18 anos: a decisão precisa ser confirmada pelo responsável legal "
            "(LGPD, art. 14).",
            codigo="responsavel_obrigatorio",
            detalhes=[{"campo": "responsavel"}],
        )
    if not responsavel_obrigatorio and dados.responsavel is not None:
        raise ValidacaoFalhou(
            "Responsável legal só se aplica a cliente menor de 18 anos.",
            codigo="responsavel_nao_aplicavel",
            detalhes=[{"campo": "responsavel"}],
        )

    registro = Consentimento(
        cliente_id=cliente.id,
        usuario_id=usuario.id,
        decisao=dados.decisao,
        termo_id=termo.id,
        versao_termo=termo.versao,
        forma_obtencao=dados.forma_obtencao,
        confirmado_por=dados.confirmado_por,
        responsavel_nome=dados.responsavel.nome if dados.responsavel else None,
        responsavel_parentesco=dados.responsavel.parentesco if dados.responsavel else None,
        faixa_etaria=faixa_etaria(cliente.data_nascimento),
        observacao=dados.observacao,
    )
    sessao.add(registro)
    sessao.commit()
    sessao.refresh(registro)
    log.info(
        "consentimento registrado: cliente=%s decisao=%s versao=%s",
        cliente.id,
        registro.decisao.value,
        registro.versao_termo,
    )
    return montar_resumo(cliente, registro, _versao_vigente(sessao))


def liberar_captura(sessao: Session, cliente: Cliente) -> Consentimento:
    """Porta única da simulação: devolve o registro que autoriza, ou levanta 403.

    É a tradução da regra crítica da seção 8 da especificação: sem consentimento aceito
    **na versão vigente**, nenhuma imagem chega ao provedor de IA.
    """
    versao_vigente = _versao_vigente(sessao)
    registro = consultas.ultimo_consentimento(sessao, cliente.id)
    bloqueio = avaliar_captura(
        cliente.nome,
        registro.decisao if registro else None,
        registro.versao_termo if registro else None,
        versao_vigente,
    )
    if bloqueio is not None:
        log.info("captura bloqueada: cliente=%s motivo=%s", cliente.id, bloqueio.motivo)
        raise ConsentimentoInvalido(
            bloqueio.descricao, motivo=bloqueio.motivo, titulo=bloqueio.titulo
        )
    assert registro is not None  # garantido por avaliar_captura
    return registro
