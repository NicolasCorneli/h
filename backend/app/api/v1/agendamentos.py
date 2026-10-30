"""RF06 — agenda."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.dependencies import SessaoDep, UsuarioDep
from app.core.erros import NaoEncontrado
from app.repositories import consultas
from app.schemas.agendamento import (
    AgendamentoAtualizacao,
    AgendamentoEntrada,
    AgendamentoOut,
    Cancelamento,
    Conclusao,
    ConclusaoOut,
    MudancaDeStatus,
)
from app.schemas.atendimento import AtendimentoOut
from app.services import agendamentos as servico

router = APIRouter(prefix="/agendamentos", tags=["agenda"])


def _do_usuario(sessao, usuario, agendamento_id: uuid.UUID):
    agendamento = consultas.agendamento_do_usuario(sessao, usuario.id, agendamento_id)
    if agendamento is None:
        raise NaoEncontrado("Agendamento não encontrado.")
    return agendamento


@router.get("", response_model=list[AgendamentoOut])
def listar(
    usuario: UsuarioDep,
    sessao: SessaoDep,
    cliente_id: Annotated[uuid.UUID | None, Query(alias="clienteId")] = None,
) -> list[AgendamentoOut]:
    return [
        AgendamentoOut.model_validate(agendamento)
        for agendamento in consultas.agendamentos_do_usuario(sessao, usuario.id, cliente_id)
    ]


@router.post("", response_model=AgendamentoOut, status_code=status.HTTP_201_CREATED)
def criar(dados: AgendamentoEntrada, usuario: UsuarioDep, sessao: SessaoDep) -> AgendamentoOut:
    return AgendamentoOut.model_validate(servico.criar(sessao, usuario, dados))


@router.get("/{agendamento_id}", response_model=AgendamentoOut)
def detalhar(
    agendamento_id: uuid.UUID, usuario: UsuarioDep, sessao: SessaoDep
) -> AgendamentoOut:
    return AgendamentoOut.model_validate(_do_usuario(sessao, usuario, agendamento_id))


@router.patch("/{agendamento_id}", response_model=AgendamentoOut)
def atualizar(
    agendamento_id: uuid.UUID,
    dados: AgendamentoAtualizacao,
    usuario: UsuarioDep,
    sessao: SessaoDep,
) -> AgendamentoOut:
    agendamento = _do_usuario(sessao, usuario, agendamento_id)
    return AgendamentoOut.model_validate(servico.atualizar(sessao, usuario, agendamento, dados))


@router.patch("/{agendamento_id}/status", response_model=AgendamentoOut)
def mudar_status(
    agendamento_id: uuid.UUID,
    dados: MudancaDeStatus,
    usuario: UsuarioDep,
    sessao: SessaoDep,
) -> AgendamentoOut:
    agendamento = _do_usuario(sessao, usuario, agendamento_id)
    return AgendamentoOut.model_validate(
        servico.mudar_status(sessao, usuario, agendamento, dados.status)
    )


@router.post("/{agendamento_id}/confirmar", response_model=AgendamentoOut)
def confirmar(agendamento_id: uuid.UUID, usuario: UsuarioDep, sessao: SessaoDep) -> AgendamentoOut:
    """Pendente → confirmado. Repetir não tem efeito."""
    agendamento = _do_usuario(sessao, usuario, agendamento_id)
    return AgendamentoOut.model_validate(servico.confirmar(sessao, agendamento))


@router.post("/{agendamento_id}/cancelar", response_model=AgendamentoOut)
def cancelar(
    agendamento_id: uuid.UUID, dados: Cancelamento, usuario: UsuarioDep, sessao: SessaoDep
) -> AgendamentoOut:
    """Cancela preservando o registro. Repetir não tem efeito."""
    agendamento = _do_usuario(sessao, usuario, agendamento_id)
    return AgendamentoOut.model_validate(servico.cancelar(sessao, agendamento, dados.motivo))


@router.post("/{agendamento_id}/concluir", response_model=ConclusaoOut)
def concluir(
    agendamento_id: uuid.UUID, dados: Conclusao, usuario: UsuarioDep, sessao: SessaoDep
) -> ConclusaoOut:
    """Conclui e cria o atendimento, na mesma transação. Repetir devolve o mesmo."""
    agendamento = _do_usuario(sessao, usuario, agendamento_id)
    atendimento = servico.concluir(sessao, usuario, agendamento, dados)
    sessao.refresh(agendamento)
    return ConclusaoOut(
        agendamento=AgendamentoOut.model_validate(agendamento),
        atendimento=AtendimentoOut.model_validate(atendimento),
    )


@router.delete("/{agendamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(agendamento_id: uuid.UUID, usuario: UsuarioDep, sessao: SessaoDep) -> None:
    servico.excluir(sessao, _do_usuario(sessao, usuario, agendamento_id))
