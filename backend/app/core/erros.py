"""Erros de negócio e formato único de resposta.

Toda falha prevista sai com o mesmo corpo:

    {"erro": {"codigo": "consentimento_invalido", "mensagem": "...", "detalhes": [...]}}

O `codigo` é estável e é o que o aplicativo usa para escolher a tela; a `mensagem` é o
texto que o profissional lê. Detalhe técnico fica no log, nunca na resposta.
"""

from __future__ import annotations

from typing import Any


class ErroDeNegocio(Exception):
    status = 400
    codigo = "erro"

    def __init__(
        self,
        mensagem: str,
        *,
        codigo: str | None = None,
        status: int | None = None,
        detalhes: list[Any] | None = None,
    ) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        if codigo:
            self.codigo = codigo
        if status:
            self.status = status
        self.detalhes = detalhes or []

    def como_json(self) -> dict[str, Any]:
        corpo: dict[str, Any] = {"codigo": self.codigo, "mensagem": self.mensagem}
        if self.detalhes:
            corpo["detalhes"] = self.detalhes
        return {"erro": corpo}


class NaoAutenticado(ErroDeNegocio):
    status = 401
    codigo = "nao_autenticado"


class SemPermissao(ErroDeNegocio):
    status = 403
    codigo = "sem_permissao"


class NaoEncontrado(ErroDeNegocio):
    status = 404
    codigo = "nao_encontrado"


class Conflito(ErroDeNegocio):
    status = 409
    codigo = "conflito"


class ValidacaoFalhou(ErroDeNegocio):
    status = 422
    codigo = "validacao"


class ConsentimentoInvalido(ErroDeNegocio):
    """403 — ausência ou invalidade da autorização do titular da imagem."""

    status = 403
    codigo = "consentimento_invalido"

    def __init__(self, mensagem: str, *, motivo: str, titulo: str) -> None:
        super().__init__(mensagem, detalhes=[{"motivo": motivo, "titulo": titulo}])
        self.motivo = motivo
        self.titulo = titulo


class FotoRecusada(ErroDeNegocio):
    """422 — a imagem não atende às condições mínimas; nada é enviado ao provedor."""

    status = 422
    codigo = "foto_recusada"


class ProvedorIndisponivel(ErroDeNegocio):
    status = 502
    codigo = "provedor_indisponivel"


class ServicoIndisponivel(ErroDeNegocio):
    status = 503
    codigo = "servico_indisponivel"


class ArmazenamentoIndisponivel(ErroDeNegocio):
    status = 503
    codigo = "armazenamento_indisponivel"
