from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from app.models.enums import DecisaoConsentimento, FaixaEtaria, FormaObtencao
from app.schemas.base import ModeloBase


class ResponsavelLegal(ModeloBase):
    nome: str = Field(min_length=2, max_length=120)
    parentesco: str = Field(min_length=2, max_length=60)


class NovaDecisao(ModeloBase):
    """Registro de uma decisão do cliente.

    A versão do termo **não** é aceita do aplicativo: quem define é o servidor, a partir
    da versão vigente. Isso impede que um aplicativo desatualizado registre um aceite
    sobre um texto que não é mais o apresentado (achado A6 do diagnóstico).
    """

    decisao: DecisaoConsentimento
    forma_obtencao: FormaObtencao
    confirmado_por: str = Field(min_length=2, max_length=120)
    responsavel: ResponsavelLegal | None = None
    observacao: str = Field(default="", max_length=2000)


class ConsentimentoOut(ModeloBase):
    id: uuid.UUID
    cliente_id: uuid.UUID
    usuario_id: uuid.UUID
    decisao: DecisaoConsentimento
    versao_termo: str
    registrado_em: datetime
    forma_obtencao: FormaObtencao
    confirmado_por: str
    responsavel: ResponsavelLegal | None
    faixa_etaria: FaixaEtaria
    observacao: str


class BloqueioOut(ModeloBase):
    motivo: Literal["pendente", "revalidar", "recusado", "revogado"]
    titulo: str
    descricao: str


class ResumoConsentimentoOut(ModeloBase):
    """O que a interface precisa para desenhar o selo e decidir o próximo passo."""

    status: Literal["pendente", "aceito", "recusado", "revogado"]
    rotulo: str
    revalidar: bool
    registro: ConsentimentoOut | None
    #: Versão vigente do termo no servidor — a única válida para uma nova decisão.
    versao_vigente: str
    exige_responsavel: bool
    #: Ausente quando a captura está liberada.
    bloqueio: BloqueioOut | None = None
