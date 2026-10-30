"""Normalização de texto usada para comparar rótulos e procurar termos."""

from __future__ import annotations

import re
import unicodedata


def normalizar(texto: str) -> str:
    """Minúsculas, sem acento, hífen como espaço: a forma usada nas comparações."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", sem_acento.lower().replace("-", " ")).strip()
