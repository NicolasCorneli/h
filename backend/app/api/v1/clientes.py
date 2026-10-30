"""RF02 — clientes e as consultas que a tela de perfil precisa.

Todas as rotas aninhadas recebem o cliente pela dependência `ClienteDep`, que já conferiu
a propriedade. Nenhuma delas consulta o banco por `cliente_id` cru.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Query, UploadFile, status

from app.core.dependencies import ClienteDep, SessaoDep, UsuarioDep
from app.repositories import consultas
from app.schemas.agendamento import AgendamentoOut
from app.schemas.atendimento import AtendimentoOut
from app.schemas.cliente import ClienteAtualizacao, ClienteEntrada, ClienteOut
from app.schemas.consentimento import ConsentimentoOut, NovaDecisao, ResumoConsentimentoOut
from app.schemas.simulacao import SimulacaoOut
from app.services import clientes as servico
from app.services import consentimento as servico_consentimento
from app.services import imagens as servico_imagens
from app.services import simulacao as servico_simulacao
from app.services.validacao_foto import ler_envio, validar_e_normalizar

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.get("", response_model=list[ClienteOut])
def listar(
    usuario: UsuarioDep,
    sessao: SessaoDep,
    busca: Annotated[str | None, Query(max_length=120)] = None,
) -> list[ClienteOut]:
    return servico.listar(sessao, usuario, busca)


@router.post("", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def criar(dados: ClienteEntrada, usuario: UsuarioDep, sessao: SessaoDep) -> ClienteOut:
    cliente = servico.criar(sessao, usuario, dados)
    return servico.como_saida(sessao, usuario, cliente)


@router.get("/{cliente_id}", response_model=ClienteOut)
def detalhar(cliente: ClienteDep, usuario: UsuarioDep, sessao: SessaoDep) -> ClienteOut:
    return servico.como_saida(sessao, usuario, cliente)


@router.patch("/{cliente_id}", response_model=ClienteOut)
def atualizar(
    dados: ClienteAtualizacao, cliente: ClienteDep, usuario: UsuarioDep, sessao: SessaoDep
) -> ClienteOut:
    atualizado = servico.atualizar(sessao, cliente, dados)
    return servico.como_saida(sessao, usuario, atualizado)


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(cliente: ClienteDep, usuario: UsuarioDep, sessao: SessaoDep) -> None:
    servico.excluir(sessao, usuario, cliente)


# --- Consentimento --------------------------------------------------------


@router.get("/{cliente_id}/consentimento", response_model=ResumoConsentimentoOut)
def consentimento_atual(cliente: ClienteDep, sessao: SessaoDep) -> ResumoConsentimentoOut:
    return servico_consentimento.resumo(sessao, cliente)


@router.get("/{cliente_id}/consentimentos", response_model=list[ConsentimentoOut])
def historico_consentimentos(cliente: ClienteDep, sessao: SessaoDep) -> list[ConsentimentoOut]:
    return servico_consentimento.historico(sessao, cliente)


@router.post(
    "/{cliente_id}/consentimentos",
    response_model=ResumoConsentimentoOut,
    status_code=status.HTTP_201_CREATED,
)
def registrar_decisao(
    dados: NovaDecisao, cliente: ClienteDep, usuario: UsuarioDep, sessao: SessaoDep
) -> ResumoConsentimentoOut:
    """Aceite, recusa ou revogação. Cada chamada cria um registro novo — nada é alterado."""
    return servico_consentimento.registrar_decisao(sessao, usuario, cliente, dados)


# --- Consultas do perfil --------------------------------------------------


@router.get("/{cliente_id}/historico", response_model=list[AtendimentoOut])
def historico(cliente: ClienteDep, usuario: UsuarioDep, sessao: SessaoDep) -> list[AtendimentoOut]:
    return [
        AtendimentoOut.model_validate(atendimento)
        for atendimento in consultas.atendimentos_do_usuario(sessao, usuario.id, cliente.id)
    ]


@router.get("/{cliente_id}/simulacoes", response_model=list[SimulacaoOut])
def simulacoes(cliente: ClienteDep, usuario: UsuarioDep, sessao: SessaoDep) -> list[SimulacaoOut]:
    servico_simulacao.expirar_processando(sessao, usuario.id)
    return [
        servico_simulacao.como_saida(simulacao, usuario.id)
        for simulacao in consultas.simulacoes_do_cliente(sessao, cliente.id)
    ]


@router.get("/{cliente_id}/agendamentos", response_model=list[AgendamentoOut])
def agendamentos(
    cliente: ClienteDep, usuario: UsuarioDep, sessao: SessaoDep
) -> list[AgendamentoOut]:
    return [
        AgendamentoOut.model_validate(agendamento)
        for agendamento in consultas.agendamentos_do_usuario(sessao, usuario.id, cliente.id)
    ]


# --- Imagens --------------------------------------------------------------


@router.delete("/{cliente_id}/simulacoes", status_code=status.HTTP_204_NO_CONTENT)
def excluir_simulacoes(cliente: ClienteDep, usuario: UsuarioDep, sessao: SessaoDep) -> None:
    """Apaga imagens e simulações do cliente. O histórico de atendimentos permanece."""
    servico_imagens.excluir_simulacoes_do_cliente(sessao, usuario, cliente)


@router.post("/{cliente_id}/foto", response_model=ClienteOut)
def enviar_foto(
    cliente: ClienteDep,
    usuario: UsuarioDep,
    sessao: SessaoDep,
    arquivo: Annotated[UploadFile, File(alias="arquivo")],
) -> ClienteOut:
    """Foto de perfil do cliente — identificação no cadastro, não simulação.

    Passa pela mesma validação técnica das demais imagens, sem exigir detecção de rosto:
    o profissional pode querer registrar uma referência de corte.
    """
    foto = validar_e_normalizar(ler_envio(arquivo.file), validar_rosto=False)
    servico_imagens.substituir_foto_de_perfil(sessao, usuario, cliente, foto)
    return servico.como_saida(sessao, usuario, cliente)


@router.delete("/{cliente_id}/foto", status_code=status.HTTP_204_NO_CONTENT)
def remover_foto(cliente: ClienteDep, sessao: SessaoDep) -> None:
    servico_imagens.remover_foto_de_perfil(sessao, cliente)
