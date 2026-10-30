"""Dependências do FastAPI: sessão, usuário autenticado e acesso a cliente.

`cliente_do_usuario` é o ponto único por onde passa qualquer acesso a dados de cliente.
Como a consulta sempre filtra pelo dono, trocar o id na URL resulta em 404 — e não em
vazamento. Responder 404 (e não 403) evita confirmar que aquele identificador existe.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Path, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.erros import NaoAutenticado, NaoEncontrado
from app.core.security import TokenInvalido, ler_dados_do_token
from app.db.session import obter_sessao
from app.models import Cliente, Usuario

SessaoDep = Annotated[Session, Depends(obter_sessao)]


def _token_do_cabecalho(request: Request) -> str:
    autorizacao = request.headers.get("Authorization", "")
    prefixo = "Bearer "
    if not autorizacao.startswith(prefixo):
        raise NaoAutenticado("Informe o token de acesso.")
    return autorizacao[len(prefixo) :].strip()


def usuario_atual(request: Request, sessao: SessaoDep) -> Usuario:
    try:
        dados = ler_dados_do_token(_token_do_cabecalho(request), "access")
    except TokenInvalido:
        raise NaoAutenticado("Sessão expirada ou token inválido.") from None

    usuario = sessao.get(Usuario, dados.usuario_id)
    if usuario is None or not usuario.ativo:
        # A conta pode ter sido excluída com o token ainda válido.
        raise NaoAutenticado("Conta não encontrada.")
    if dados.versao_sessao != usuario.versao_sessao:
        # Senha trocada ou "sair de todos os aparelhos" depois que este token saiu.
        raise NaoAutenticado("Sessão encerrada. Entre de novo.", codigo="sessao_encerrada")
    return usuario


UsuarioDep = Annotated[Usuario, Depends(usuario_atual)]


def cliente_do_usuario(
    cliente_id: Annotated[uuid.UUID, Path(alias="cliente_id")],
    usuario: UsuarioDep,
    sessao: SessaoDep,
) -> Cliente:
    cliente = sessao.scalar(
        select(Cliente).where(Cliente.id == cliente_id, Cliente.usuario_id == usuario.id)
    )
    if cliente is None:
        raise NaoEncontrado("Cliente não encontrado.")
    return cliente


ClienteDep = Annotated[Cliente, Depends(cliente_do_usuario)]
