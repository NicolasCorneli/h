"""Verificação do token de identidade do Google (OpenID Connect).

O aplicativo faz o login na tela do próprio Google e recebe um *ID token*: um JWT
assinado pelo Google que diz quem é a pessoa. O servidor não confia no aplicativo: confere
o token com a biblioteca oficial (`google-auth`), que

- baixa as chaves públicas do Google e confere a assinatura;
- confere a validade (`exp`) e a emissão (`iat`);
- confere o emissor (`iss`: accounts.google.com);
- confere o público (`aud`): o token precisa ter sido emitido para um dos IDs de cliente
  deste aplicativo. Um token emitido para outro site não serve aqui.

Além disso, exige `email_verified`: o Google confirmou que o e-mail é da pessoa.

Nada do token vai para o log: ele é uma credencial enquanto não expira.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from google.auth import exceptions as erros_google
from google.auth.transport import requests as transporte_google
from google.oauth2 import id_token

from app.core.config import obter_config
from app.core.erros import NaoAutenticado, ServicoIndisponivel

log = logging.getLogger(__name__)

#: Folga para diferença de relógio entre o servidor e o Google.
FOLGA_RELOGIO_S = 10


@dataclass(frozen=True)
class IdentidadeGoogle:
    sujeito: str
    email: str
    nome: str


def google_configurado() -> bool:
    return bool(obter_config().ids_google)


def _requisicao() -> transporte_google.Request:
    return transporte_google.Request()


def _decodificar(token: str, publicos: list[str]) -> dict[str, Any]:
    """Ponto único de contato com a biblioteca do Google. Os testes o substituem só no
    endereço das chaves públicas; a verificação em si é a da biblioteca."""
    return id_token.verify_oauth2_token(
        token, _requisicao(), audience=publicos, clock_skew_in_seconds=FOLGA_RELOGIO_S
    )


def verificar_id_token(token: str, nonce: str | None = None) -> IdentidadeGoogle:
    publicos = obter_config().ids_google
    if not publicos:
        raise ServicoIndisponivel(
            "Entrar com Google não está disponível neste servidor.", codigo="google_nao_configurado"
        )

    try:
        dados = _decodificar(token, publicos)
    except erros_google.TransportError:
        # Não foi possível buscar as chaves do Google: não é culpa de quem tenta entrar.
        log.warning("google: falha ao obter as chaves públicas")
        raise ServicoIndisponivel(
            "Não foi possível falar com o Google agora. Tente de novo em instantes.",
            codigo="google_indisponivel",
        ) from None
    except (ValueError, erros_google.GoogleAuthError) as erro:
        # Assinatura, validade, emissor ou público errados. A razão fica no log (sem o
        # token); a resposta é a mesma para todos os casos.
        log.info("google: token recusado (%s)", type(erro).__name__)
        raise NaoAutenticado(
            "Não foi possível confirmar sua conta Google. Tente de novo.",
            codigo="google_token_invalido",
        ) from None

    if nonce is not None and dados.get("nonce") != nonce:
        raise NaoAutenticado(
            "Não foi possível confirmar sua conta Google. Tente de novo.",
            codigo="google_token_invalido",
        )

    email = str(dados.get("email") or "").strip().lower()
    verificado = dados.get("email_verified") in (True, "true")
    if not email or not verificado:
        raise NaoAutenticado(
            "Sua conta Google não tem um e-mail confirmado. Confirme o e-mail no Google ou "
            "entre com e-mail e senha.",
            codigo="google_email_nao_verificado",
        )

    sujeito = str(dados.get("sub") or "")
    if not sujeito:
        raise NaoAutenticado(
            "Não foi possível confirmar sua conta Google. Tente de novo.",
            codigo="google_token_invalido",
        )

    nome = str(dados.get("name") or "").strip() or email.split("@")[0]
    return IdentidadeGoogle(sujeito=sujeito, email=email, nome=nome[:120])
