"""Catálogo de estilos, cores e serviços aceitos pelo servidor."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.simulacao import CatalogoOut
from app.services.catalogo import SERVICOS, rotulos_de_cor, rotulos_de_estilo

router = APIRouter(prefix="/catalogo", tags=["catálogo"])


@router.get("", response_model=CatalogoOut)
def catalogo() -> CatalogoOut:
    return CatalogoOut(
        estilos=rotulos_de_estilo(), cores=rotulos_de_cor(), servicos=list(SERVICOS)
    )
