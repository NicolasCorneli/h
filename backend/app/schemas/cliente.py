from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import Field, field_validator

from app.schemas.base import ModeloBase
from app.schemas.consentimento import ResumoConsentimentoOut


def _nascimento_plausivel(valor: date | None) -> date | None:
    """A mesma regra no cadastro e na edição: antes ela só valia no cadastro, e um PATCH
    gravava nascimento em 2099, o que torna a faixa etária (e a exigência de responsável
    legal no consentimento) sem sentido."""
    if valor is None:
        return None
    if valor > date.today():
        raise ValueError("a data de nascimento não pode estar no futuro")
    if valor.year < 1900:
        raise ValueError("data de nascimento implausível")
    return valor


class ClienteEntrada(ModeloBase):
    nome: str = Field(min_length=2, max_length=120)
    telefone: str = Field(default="", max_length=32)
    observacoes: str = Field(default="", max_length=4000)
    data_nascimento: date | None = None

    @field_validator("data_nascimento")
    @classmethod
    def _data_plausivel(cls, valor: date | None) -> date | None:
        return _nascimento_plausivel(valor)


class ClienteAtualizacao(ModeloBase):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    telefone: str | None = Field(default=None, max_length=32)
    observacoes: str | None = Field(default=None, max_length=4000)
    data_nascimento: date | None = None
    #: `true` apaga a data já cadastrada (sem isso não há como distinguir de "não mudou").
    limpar_data_nascimento: bool = False

    @field_validator("data_nascimento")
    @classmethod
    def _data_plausivel(cls, valor: date | None) -> date | None:
        return _nascimento_plausivel(valor)


class ClienteOut(ModeloBase):
    id: uuid.UUID
    usuario_id: uuid.UUID
    nome: str
    telefone: str
    observacoes: str
    data_nascimento: date | None
    #: URL assinada de curta duração, ou `null`. Mesmo nome de campo do aplicativo.
    foto_uri: str | None
    criado_em: datetime
    #: Vem junto para a lista de clientes desenhar o selo sem uma requisição por linha.
    consentimento: ResumoConsentimentoOut
