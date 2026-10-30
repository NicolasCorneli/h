"""Escolha do driver de armazenamento a partir da configuração."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import obter_config
from app.services.storage.base import (
    ArmazenamentoObjetos,
    ChaveInvalida,
    ErroDeArmazenamento,
    ObjetoNaoEncontrado,
    montar_chave,
    prefixo_do_cliente,
    prefixo_do_usuario,
)


@lru_cache
def obter_armazenamento() -> ArmazenamentoObjetos:
    config = obter_config()
    if config.storage_driver == "s3":
        from app.services.storage.s3 import ArmazenamentoS3

        return ArmazenamentoS3(config)

    from app.services.storage.local import ArmazenamentoLocal

    return ArmazenamentoLocal(config.storage_dir)


__all__ = [
    "ArmazenamentoObjetos",
    "ChaveInvalida",
    "ErroDeArmazenamento",
    "ObjetoNaoEncontrado",
    "montar_chave",
    "obter_armazenamento",
    "prefixo_do_cliente",
    "prefixo_do_usuario",
]
