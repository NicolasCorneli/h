"""Driver de disco — padrão em desenvolvimento.

Dispensa contêiner extra e funciona sem rede. Não serve URL própria: os bytes saem pelo
endpoint `GET /api/v1/imagens/{id}`, que exige assinatura válida.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from app.services.storage.base import (
    ArmazenamentoObjetos,
    ObjetoNaoEncontrado,
    validar_chave,
)


class ArmazenamentoLocal(ArmazenamentoObjetos):
    def __init__(self, raiz: Path) -> None:
        self.raiz = raiz.resolve()
        self.raiz.mkdir(parents=True, exist_ok=True)

    def _caminho(self, chave: str) -> Path:
        destino = (self.raiz / validar_chave(chave)).resolve()
        # Cinto e suspensório: mesmo com a chave validada, confirma que o caminho final
        # permanece dentro da raiz.
        if not destino.is_relative_to(self.raiz):
            raise ValueError("caminho fora do diretório de armazenamento")
        return destino

    def salvar(self, chave: str, conteudo: bytes, mime: str) -> None:
        destino = self._caminho(chave)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo)

    def obter(self, chave: str) -> bytes:
        destino = self._caminho(chave)
        if not destino.is_file():
            raise ObjetoNaoEncontrado(chave)
        return destino.read_bytes()

    def excluir(self, chave: str) -> None:
        destino = self._caminho(chave)
        destino.unlink(missing_ok=True)

    def excluir_prefixo(self, prefixo: str) -> int:
        base = self._caminho(prefixo.rstrip("/"))
        if not base.exists():
            return 0
        quantidade = sum(1 for caminho in base.rglob("*") if caminho.is_file())
        shutil.rmtree(base, ignore_errors=True)
        return quantidade
