"""Fábrica do provedor de IA, escolhido por `AI_PROVIDER`."""

from __future__ import annotations

from app.core.config import obter_config
from app.services.ai.base import (
    EntradaSimulacao,
    FalhaDoProvedor,
    ProvedorIA,
    SaidaSimulacao,
)


def obter_provedor() -> ProvedorIA:
    """Instanciado por chamada: a configuração pode mudar entre execuções e testes."""
    if obter_config().ai_provider == "replicate":
        from app.services.ai.replicate import ProvedorReplicate

        return ProvedorReplicate()

    from app.services.ai.fake import ProvedorLocal

    return ProvedorLocal()


__all__ = [
    "EntradaSimulacao",
    "FalhaDoProvedor",
    "ProvedorIA",
    "SaidaSimulacao",
    "obter_provedor",
]
