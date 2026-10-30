"""Termos versionados.

Público: o aplicativo precisa do texto antes de haver sessão (a tela de responsabilidades
aparece no primeiro acesso) e o texto não é dado pessoal.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import SessaoDep
from app.core.erros import NaoEncontrado
from app.models import TipoTermo
from app.repositories import consultas
from app.schemas.termo import TermoOut

router = APIRouter(prefix="/termos", tags=["termos"])


@router.get("/{tipo}", response_model=TermoOut)
def vigente(tipo: TipoTermo, sessao: SessaoDep) -> TermoOut:
    termo = consultas.termo_vigente(sessao, tipo)
    if termo is None:
        raise NaoEncontrado(f"Nenhum termo do tipo {tipo.value} está publicado.")
    return TermoOut.model_validate(termo)


@router.get("/{tipo}/{versao}", response_model=TermoOut)
def por_versao(tipo: TipoTermo, versao: str, sessao: SessaoDep) -> TermoOut:
    """Texto exato de uma versão já aceita — é o que o cliente leu naquele dia."""
    termo = consultas.termo_por_versao(sessao, tipo, versao)
    if termo is None:
        raise NaoEncontrado(f"Versão {versao} não encontrada.")
    return TermoOut.model_validate(termo)
