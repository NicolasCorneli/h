from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.core.security import MAX_BYTES_SENHA
from app.schemas.base import ModeloBase

MIN_SENHA = 8


def _cabe_no_bcrypt(valor: str) -> str:
    if len(valor.encode()) > MAX_BYTES_SENHA:
        raise ValueError(
            f"a senha não pode passar de {MAX_BYTES_SENHA} bytes "
            "(limite do algoritmo de hash)"
        )
    return valor


class _ComSenha(ModeloBase):
    senha: str = Field(min_length=MIN_SENHA, max_length=128)

    @field_validator("senha")
    @classmethod
    def _senha_cabe_no_bcrypt(cls, valor: str) -> str:
        return _cabe_no_bcrypt(valor)


class Registro(_ComSenha):
    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    atuacao: str = Field(default="autônomo", min_length=2, max_length=60)


class Login(ModeloBase):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=128)


class Renovacao(ModeloBase):
    refresh_token: str


class ExclusaoDeConta(ModeloBase):
    """A operação é irreversível, por isso pede a senha de novo.

    Contas criadas pelo Google não têm senha: confirmam com um token novo do Google.
    """

    senha: str | None = Field(default=None, min_length=1, max_length=128)
    id_token_google: str | None = Field(default=None, min_length=20, max_length=4096)


class TokenGoogle(ModeloBase):
    """O ID token que o aplicativo recebeu do Google, e o `nonce` usado no pedido."""

    id_token: str = Field(min_length=20, max_length=4096)
    nonce: str | None = Field(default=None, max_length=200)


class ProvedoresOut(ModeloBase):
    """Formas de entrar disponíveis neste servidor, para o aplicativo não mostrar botão
    que não funciona."""

    google: bool


class TokensOut(ModeloBase):
    access_token: str
    refresh_token: str
    tipo: str = "bearer"
    #: Segundos de validade do token de acesso, para o aplicativo renovar antes de expirar.
    expira_em: int


class UsuarioOut(ModeloBase):
    id: uuid.UUID
    nome: str
    email: EmailStr
    atuacao: str
    criado_em: datetime
    #: Contas criadas pelo Google não têm senha; a exclusão pede o Google no lugar dela.
    tem_senha: bool
    google_vinculado: bool
    #: URL assinada e temporária da foto do profissional; vazia sem foto.
    foto_uri: str | None = None


class SessaoOut(ModeloBase):
    """Resposta de login e de cadastro: tokens + usuário, em uma só ida ao servidor."""

    tokens: TokensOut
    usuario: UsuarioOut


class CienciaOut(ModeloBase):
    """Mesma forma de `CienciaProfissional` no aplicativo."""

    aceita: bool
    versao: str | None
    registrada_em: datetime | None


class TrocaDeSenha(ModeloBase):
    """A senha atual confirma que é a dona da conta, e não alguém com um token copiado."""

    senha_atual: str = Field(min_length=1, max_length=128)
    nova_senha: str = Field(min_length=MIN_SENHA, max_length=128)

    @field_validator("nova_senha")
    @classmethod
    def _nova_cabe_no_bcrypt(cls, valor: str) -> str:
        return _cabe_no_bcrypt(valor)


class AtualizacaoDePerfil(ModeloBase):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    atuacao: str | None = Field(default=None, min_length=2, max_length=60)
