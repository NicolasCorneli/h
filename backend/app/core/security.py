"""Senhas, tokens e assinatura das URLs de imagem.

Três mecanismos, propositalmente juntos porque compartilham o mesmo segredo de origem:

1. hash de senha com bcrypt (custo 12) — nunca se guarda a senha em texto puro;
2. JWT HS256 de acesso e de renovação;
3. assinatura HMAC de curta duração para servir imagens sem URL pública permanente.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import obter_config

#: bcrypt ignora bytes além de 72. Em vez de truncar em silêncio, a senha é recusada
#: na validação de entrada (ver schemas.auth).
MAX_BYTES_SENHA = 72

TipoToken = Literal["access", "refresh"]


# --- Senhas ---------------------------------------------------------------


def gerar_hash_senha(senha: str) -> str:
    if len(senha.encode()) > MAX_BYTES_SENHA:
        raise ValueError("senha excede o limite de 72 bytes do bcrypt")
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt(rounds=12)).decode()


def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode()[:MAX_BYTES_SENHA], hash_armazenado.encode())
    except ValueError:
        # Hash malformado no banco: trata como falha de autenticação, sem vazar o motivo.
        return False


# --- JWT ------------------------------------------------------------------


def criar_token(
    usuario_id: uuid.UUID, tipo: TipoToken = "access", versao_sessao: int = 0
) -> str:
    config = obter_config()
    agora = datetime.now(UTC)
    validade = (
        timedelta(minutes=config.jwt_minutos_access)
        if tipo == "access"
        else timedelta(days=config.jwt_dias_refresh)
    )
    payload = {
        "sub": str(usuario_id),
        "tipo": tipo,
        # Versão da sessão da conta: trocar a senha ou sair de todos os aparelhos a
        # incrementa, e o token deixa de valer (ver `usuarios.versao_sessao`).
        "sv": versao_sessao,
        "iat": int(agora.timestamp()),
        "exp": int((agora + validade).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algoritmo)


class TokenInvalido(Exception):
    pass


@dataclass(frozen=True)
class DadosDoToken:
    usuario_id: uuid.UUID
    #: Tokens emitidos antes da versão da sessão não têm `sv`: valem como 0, a versão
    #: inicial de toda conta, para a atualização não desconectar ninguém.
    versao_sessao: int


def ler_dados_do_token(token: str, tipo_esperado: TipoToken = "access") -> DadosDoToken:
    config = obter_config()
    try:
        dados: dict[str, Any] = jwt.decode(
            token,
            config.jwt_secret,
            algorithms=[config.jwt_algoritmo],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as erro:
        raise TokenInvalido(str(erro)) from erro

    if dados.get("tipo") != tipo_esperado:
        raise TokenInvalido("tipo de token inesperado")
    versao = dados.get("sv", 0)
    if not isinstance(versao, int) or isinstance(versao, bool):
        raise TokenInvalido("versão da sessão inválida")
    try:
        return DadosDoToken(usuario_id=uuid.UUID(dados["sub"]), versao_sessao=versao)
    except (KeyError, ValueError, TypeError) as erro:
        raise TokenInvalido("identificador ausente ou inválido") from erro


def ler_token(token: str, tipo_esperado: TipoToken = "access") -> uuid.UUID:
    return ler_dados_do_token(token, tipo_esperado).usuario_id


# --- Assinatura das URLs de imagem ---------------------------------------


def assinar_imagem(imagem_id: uuid.UUID, usuario_id: uuid.UUID) -> str:
    """Token curto que libera **uma** imagem para **um** usuário por alguns minutos.

    O `<Image>` do React Native não envia cabeçalhos de autorização de forma confiável,
    por isso a autorização vai na query — mas nunca como URL pública permanente.
    """
    config = obter_config()
    expira = int((datetime.now(UTC) + timedelta(minutes=config.url_imagem_minutos)).timestamp())
    return assinar_imagem_em(imagem_id, usuario_id, expira)


def verificar_assinatura_imagem(token: str, imagem_id: uuid.UUID, usuario_id: uuid.UUID) -> bool:
    try:
        expira_txt, _ = token.split(".", 1)
        expira = int(expira_txt)
    except (ValueError, AttributeError):
        return False
    if expira < int(datetime.now(UTC).timestamp()):
        return False
    esperado = assinar_imagem_em(imagem_id, usuario_id, expira)
    return hmac.compare_digest(token, esperado)


def assinar_imagem_em(imagem_id: uuid.UUID, usuario_id: uuid.UUID, expira: int) -> str:
    config = obter_config()
    mensagem = f"{imagem_id}:{usuario_id}:{expira}"
    assinatura = hmac.new(config.jwt_secret.encode(), mensagem.encode(), hashlib.sha256).digest()
    return f"{expira}.{base64.urlsafe_b64encode(assinatura).decode().rstrip('=')}"
