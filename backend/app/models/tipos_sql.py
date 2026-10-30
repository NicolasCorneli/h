"""Apoio para declarar enums nativos do PostgreSQL a partir dos enums Python."""

from __future__ import annotations

import enum
from typing import TypeVar

from sqlalchemy import Enum as EnumSQL

E = TypeVar("E", bound=enum.Enum)


def enum_pg(classe: type[E], nome: str) -> EnumSQL:
    """Enum nativo cujo valor gravado é o `value` do membro (e não o nome)."""
    return EnumSQL(
        classe,
        name=nome,
        values_callable=lambda c: [membro.value for membro in c],
        native_enum=True,
    )
