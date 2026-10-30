from __future__ import annotations

from datetime import date

from app.models.enums import TipoTermo
from app.schemas.base import ModeloBase


class SecaoTermoOut(ModeloBase):
    titulo: str
    texto: str
    destaque: bool = False


class TermoOut(ModeloBase):
    """Mesma forma de `Termo` no aplicativo, mais `tipo` e `vigente`."""

    tipo: TipoTermo
    versao: str
    vigente_desde: date
    vigente: bool
    titulo: str
    resumo: str
    secoes: list[SecaoTermoOut]
