"""Agrupa os routers da versão 1 da API."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    agendamentos,
    atendimentos,
    auth,
    catalogo,
    clientes,
    imagens,
    simulacoes,
    termos,
    usuarios,
)

router = APIRouter(prefix="/api/v1")

for modulo in (
    auth,
    usuarios,
    clientes,
    simulacoes,
    atendimentos,
    agendamentos,
    termos,
    imagens,
    catalogo,
):
    router.include_router(modulo.router)
