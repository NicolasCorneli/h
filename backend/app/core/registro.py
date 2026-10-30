"""Configuração dos logs e identificador da requisição.

Cada requisição recebe um identificador (o `X-Request-ID` que veio do proxy, se for
aceitável, ou um novo). Ele vai no cabeçalho da resposta e em toda linha de log escrita
durante a requisição, inclusive nas tarefas em segundo plano que ela dispara: é o que
liga a reclamação "deu erro às 14h" à linha certa do log.

O registro de acesso é deste módulo, e não o do uvicorn: o do uvicorn escreve a URL com a
query, e a query das imagens leva a assinatura que dá acesso à foto de uma pessoa.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime

_id_requisicao: ContextVar[str] = ContextVar("id_requisicao", default="-")

#: Identificador vindo de fora: só caracteres seguros e tamanho limitado, para ninguém
#: injetar quebras de linha ou texto enorme no log.
_ID_ACEITAVEL = re.compile(r"[A-Za-z0-9._-]{8,64}")


def novo_id_requisicao(recebido: str | None) -> str:
    if recebido and _ID_ACEITAVEL.fullmatch(recebido):
        return recebido
    return uuid.uuid4().hex


def definir_id_requisicao(valor: str) -> None:
    _id_requisicao.set(valor)


def id_requisicao() -> str:
    return _id_requisicao.get()


class _ComIdDaRequisicao(logging.Filter):
    def filter(self, registro: logging.LogRecord) -> bool:
        registro.id_requisicao = _id_requisicao.get()
        return True


class _FormatoJson(logging.Formatter):
    """Uma linha JSON por evento, com os campos que coletores de log esperam."""

    def format(self, registro: logging.LogRecord) -> str:
        evento = {
            "momento": datetime.fromtimestamp(registro.created, UTC).isoformat(),
            "nivel": registro.levelname,
            "origem": registro.name,
            "mensagem": registro.getMessage(),
            "requisicao": getattr(registro, "id_requisicao", "-"),
        }
        if registro.exc_info:
            evento["excecao"] = self.formatException(registro.exc_info)
        return json.dumps(evento, ensure_ascii=False)


def configurar_logs(formato: str = "texto", nivel: str = "INFO") -> None:
    """Configura o log raiz uma vez. Chamar de novo troca o formato (útil nos testes)."""
    manipulador = logging.StreamHandler()
    manipulador.addFilter(_ComIdDaRequisicao())
    if formato == "json":
        manipulador.setFormatter(_FormatoJson())
    else:
        manipulador.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] [%(id_requisicao)s] %(message)s")
        )
    raiz = logging.getLogger()
    for anterior in list(raiz.handlers):
        raiz.removeHandler(anterior)
    raiz.addHandler(manipulador)
    raiz.setLevel(nivel)
    # A API só usa o Alembic para conferir a versão do banco, a cada sonda de prontidão,
    # e ele anuncia "Context impl PostgresqlImpl." em toda conferência.
    logging.getLogger("alembic.runtime.migration").setLevel(logging.WARNING)
