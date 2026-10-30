"""RF03 — histórico de atendimentos."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.dependencies import SessaoDep, UsuarioDep
from app.core.erros import NaoEncontrado
from app.repositories import consultas
from app.schemas.atendimento import AtendimentoAtualizacao, AtendimentoEntrada, AtendimentoOut
from app.services import atendimentos as servico

router = APIRouter(prefix="/atendimentos", tags=["atendimentos"])


def _do_usuario(sessao, usuario, atendimento_id: uuid.UUID):
    atendimento = consultas.atendimento_do_usuario(sessao, usuario.id, atendimento_id)
    if atendimento is None:
        raise NaoEncontrado("Atendimento não encontrado.")
    return atendimento


@router.get("", response_model=list[AtendimentoOut])
def listar(
    usuario: UsuarioDep,
    sessao: SessaoDep,
    cliente_id: Annotated[uuid.UUID | None, Query(alias="clienteId")] = None,
) -> list[AtendimentoOut]:
    return [
        AtendimentoOut.model_validate(atendimento)
        for atendimento in consultas.atendimentos_do_usuario(sessao, usuario.id, cliente_id)
    ]


@router.post("", response_model=AtendimentoOut, status_code=status.HTTP_201_CREATED)
def criar(dados: AtendimentoEntrada, usuario: UsuarioDep, sessao: SessaoDep) -> AtendimentoOut:
    return AtendimentoOut.model_validate(servico.criar(sessao, usuario, dados))


@router.get("/{atendimento_id}", response_model=AtendimentoOut)
def detalhar(
    atendimento_id: uuid.UUID, usuario: UsuarioDep, sessao: SessaoDep
) -> AtendimentoOut:
    return AtendimentoOut.model_validate(_do_usuario(sessao, usuario, atendimento_id))


@router.patch("/{atendimento_id}", response_model=AtendimentoOut)
def atualizar(
    atendimento_id: uuid.UUID,
    dados: AtendimentoAtualizacao,
    usuario: UsuarioDep,
    sessao: SessaoDep,
) -> AtendimentoOut:
    atendimento = _do_usuario(sessao, usuario, atendimento_id)
    return AtendimentoOut.model_validate(
        servico.atualizar(sessao, usuario, atendimento, dados)
    )


@router.delete("/{atendimento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(atendimento_id: uuid.UUID, usuario: UsuarioDep, sessao: SessaoDep) -> None:
    """Só atendimentos avulsos; os vindos da agenda se corrigem (`PATCH`)."""
    servico.excluir(sessao, _do_usuario(sessao, usuario, atendimento_id))
