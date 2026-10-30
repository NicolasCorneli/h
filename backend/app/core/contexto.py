"""Endereço público da requisição atual.

As URLs assinadas de imagem precisam ser absolutas: o `<Image>` do React Native não
resolve caminho relativo. Em vez de fixar o host em configuração — que quebraria quando o
aplicativo roda em um celular acessando o computador por IP da rede local — a URL é
montada a partir do endereço da própria requisição, guardado aqui por um middleware.
"""

from __future__ import annotations

from contextvars import ContextVar

_base_url: ContextVar[str] = ContextVar("base_url", default="")


def definir_base_url(valor: str) -> None:
    _base_url.set(valor.rstrip("/"))


def base_url() -> str:
    return _base_url.get()
