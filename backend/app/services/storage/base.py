"""Contrato do armazenamento de objetos.

O PostgreSQL guarda apenas metadados (tabela `imagens`); o binário vive aqui. Dois
drivers implementam este contrato: `local` (disco, padrão em desenvolvimento) e `s3`
(S3, MinIO ou Supabase Storage). Nenhum outro módulo sabe qual está em uso.
"""

from __future__ import annotations

import re
import uuid
from abc import ABC, abstractmethod

from app.models.enums import TipoImagem

#: Chaves são geradas pelo servidor a partir de UUIDs. O nome enviado pelo cliente nunca
#: participa da chave — é a proteção contra *path traversal*.
PADRAO_CHAVE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9/_.-]{0,399}$")

EXTENSAO_POR_MIME = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class ChaveInvalida(ValueError):
    pass


def validar_chave(chave: str) -> str:
    if not PADRAO_CHAVE.match(chave) or ".." in chave or chave.endswith("/"):
        raise ChaveInvalida(f"chave de objeto inválida: {chave!r}")
    return chave


def montar_chave(
    usuario_id: uuid.UUID,
    cliente_id: uuid.UUID | None,
    tipo: TipoImagem,
    mime: str,
    simulacao_id: uuid.UUID | None = None,
) -> str:
    """`usuarios/{u}/clientes/{c}/simulacoes/{s}/entrada.jpg` e variantes."""
    extensao = EXTENSAO_POR_MIME.get(mime, "bin")
    partes = [f"usuarios/{usuario_id}"]
    if cliente_id is not None:
        partes.append(f"clientes/{cliente_id}")
    if simulacao_id is not None:
        partes.append(f"simulacoes/{simulacao_id}")
    partes.append(f"{tipo.value}-{uuid.uuid4().hex[:12]}.{extensao}")
    return validar_chave("/".join(partes))


def prefixo_do_usuario(usuario_id: uuid.UUID) -> str:
    return f"usuarios/{usuario_id}/"


def prefixo_do_cliente(usuario_id: uuid.UUID, cliente_id: uuid.UUID) -> str:
    return f"usuarios/{usuario_id}/clientes/{cliente_id}/"


class ArmazenamentoObjetos(ABC):
    @abstractmethod
    def salvar(self, chave: str, conteudo: bytes, mime: str) -> None: ...

    @abstractmethod
    def obter(self, chave: str) -> bytes: ...

    @abstractmethod
    def excluir(self, chave: str) -> None: ...

    @abstractmethod
    def excluir_prefixo(self, prefixo: str) -> int:
        """Remove tudo sob o prefixo e devolve a quantidade de objetos apagados."""

    def url_temporaria(self, chave: str) -> str | None:
        """URL pré-assinada do próprio storage, quando existir.

        `None` significa que a API deve entregar os bytes ela mesma — é o caso do driver
        local. Em nenhuma hipótese se devolve URL pública permanente.
        """
        return None


class ObjetoNaoEncontrado(KeyError):
    pass


class ErroDeArmazenamento(OSError):
    """O storage não respondeu ou recusou a operação (rede, credencial, bucket).

    Herda de `OSError` para que quem já trata falha de disco trate esta também. A API a
    responde com 503: é indisponibilidade, não erro de quem pediu nem defeito do sistema.
    """
