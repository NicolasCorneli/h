"""Driver S3 — compatível com AWS S3, MinIO e Supabase Storage.

Ativado por `STORAGE_DRIVER=s3`. Aqui a URL temporária é pré-assinada pelo próprio
storage, com expiração; a API apenas redireciona.

Toda falha do serviço (rede, credencial, bucket inexistente) sai como
`ErroDeArmazenamento`, que a API responde com 503. Antes, uma exceção do `botocore`
subia sem tratamento e virava erro 500.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from app.core.config import Configuracao
from app.services.storage.base import (
    ArmazenamentoObjetos,
    ErroDeArmazenamento,
    ObjetoNaoEncontrado,
    validar_chave,
)

T = TypeVar("T")


class ArmazenamentoS3(ArmazenamentoObjetos):
    def __init__(self, config: Configuracao) -> None:
        import boto3  # importado sob demanda: o driver local não precisa de boto3
        from botocore.config import Config as ConfigBotocore

        self.bucket = config.storage_bucket
        self.expira_s = config.url_imagem_minutos * 60
        self.cliente: Any = boto3.client(
            "s3",
            endpoint_url=config.storage_url or None,
            aws_access_key_id=config.storage_key or None,
            aws_secret_access_key=config.storage_secret or None,
            region_name=config.storage_regiao,
            # Sem tempo limite, um storage que não responde prende a requisição (e a
            # conexão do banco que ela segura) indefinidamente. O modo `standard` repete
            # as falhas transitórias com espera crescente.
            config=ConfigBotocore(
                connect_timeout=5,
                read_timeout=30,
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )

    def _executar(self, operacao: str, chamada: Callable[[], T]) -> T:
        from botocore.exceptions import BotoCoreError, ClientError

        try:
            return chamada()
        except ClientError as erro:
            codigo = erro.response.get("Error", {}).get("Code", "?")
            raise ErroDeArmazenamento(f"S3 recusou {operacao}: {codigo}") from erro
        except BotoCoreError as erro:
            raise ErroDeArmazenamento(f"S3 indisponível ao {operacao}: {type(erro).__name__}") from erro

    def salvar(self, chave: str, conteudo: bytes, mime: str) -> None:
        self._executar(
            "gravar",
            lambda: self.cliente.put_object(
                Bucket=self.bucket, Key=validar_chave(chave), Body=conteudo, ContentType=mime
            ),
        )

    def obter(self, chave: str) -> bytes:
        from botocore.exceptions import ClientError

        try:
            resposta = self._executar(
                "ler",
                lambda: self.cliente.get_object(Bucket=self.bucket, Key=validar_chave(chave)),
            )
        except ErroDeArmazenamento as erro:
            causa = erro.__cause__
            if isinstance(causa, ClientError) and causa.response.get("Error", {}).get("Code") in {
                "NoSuchKey",
                "404",
            }:
                raise ObjetoNaoEncontrado(chave) from causa
            raise
        return self._executar("ler", lambda: resposta["Body"].read())

    def excluir(self, chave: str) -> None:
        self._executar(
            "apagar",
            lambda: self.cliente.delete_object(Bucket=self.bucket, Key=validar_chave(chave)),
        )

    def excluir_prefixo(self, prefixo: str) -> int:
        def apagar_tudo() -> int:
            paginador = self.cliente.get_paginator("list_objects_v2")
            total = 0
            for pagina in paginador.paginate(Bucket=self.bucket, Prefix=prefixo):
                objetos = [{"Key": item["Key"]} for item in pagina.get("Contents", [])]
                if not objetos:
                    continue
                resposta = self.cliente.delete_objects(
                    Bucket=self.bucket, Delete={"Objects": objetos, "Quiet": True}
                )
                # `delete_objects` responde 200 mesmo quando parte falha: a lista de erros
                # vem no corpo. Ignorá-la deixaria fotos no bucket depois de um pedido de
                # eliminação.
                falhas = resposta.get("Errors") or []
                if falhas:
                    raise ErroDeArmazenamento(
                        f"S3 não apagou {len(falhas)} objeto(s) sob {prefixo}"
                    )
                total += len(objetos)
            return total

        return self._executar("apagar o prefixo", apagar_tudo)

    def url_temporaria(self, chave: str) -> str | None:
        return self._executar(
            "assinar a URL",
            lambda: self.cliente.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": validar_chave(chave)},
                ExpiresIn=self.expira_s,
            ),
        )
