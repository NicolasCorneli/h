from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdUUID
from app.models.enums import DecisaoConsentimento, FaixaEtaria, FormaObtencao
from app.models.tipos_sql import enum_pg

if TYPE_CHECKING:
    from app.models.cliente import Cliente
    from app.models.termo import Termo
    from app.models.usuario import Usuario


class Consentimento(IdUUID, Base):
    """Decisão do cliente sobre o uso da própria imagem — registro imutável.

    O estado `pendente` não é persistido: ausência de registro é ausência de decisão.
    Uma revogação cria uma **nova** linha; o histórico anterior permanece (LGPD, art. 37).
    O gatilho `consentimentos_imutaveis` recusa `UPDATE` e só admite `DELETE` quando o
    cliente já não existe, isto é, em cascata do direito de eliminação (art. 18, VI).
    """

    __tablename__ = "consentimentos"
    __table_args__ = (
        Index("ix_consentimentos_cliente_id_registrado_em", "cliente_id", "registrado_em"),
        CheckConstraint(
            "(responsavel_nome IS NULL) = (responsavel_parentesco IS NULL)",
            name="responsavel_completo",
        ),
        CheckConstraint("length(confirmado_por) > 0", name="confirmado_por_preenchido"),
    )

    cliente_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False
    )
    #: Profissional que apresentou o termo e registrou a decisão. Em cascata com a conta:
    #: excluir a conta elimina também os registros, conforme a estratégia documentada.
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    decisao: Mapped[DecisaoConsentimento] = mapped_column(
        enum_pg(DecisaoConsentimento, "decisao_consentimento"), nullable=False
    )
    termo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("termos.id", ondelete="RESTRICT"), nullable=False
    )
    #: Cópia da versão apresentada, para leitura histórica sem junção.
    versao_termo: Mapped[str] = mapped_column(String(10), nullable=False)
    registrado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    forma_obtencao: Mapped[FormaObtencao] = mapped_column(
        enum_pg(FormaObtencao, "forma_obtencao"), nullable=False
    )
    #: Quem confirmou: o próprio cliente ou o responsável legal.
    confirmado_por: Mapped[str] = mapped_column(String(120), nullable=False)
    responsavel_nome: Mapped[str | None] = mapped_column(String(120), nullable=True)
    responsavel_parentesco: Mapped[str | None] = mapped_column(String(60), nullable=True)
    #: Faixa etária apurada no momento do registro (LGPD, art. 14).
    faixa_etaria: Mapped[FaixaEtaria] = mapped_column(
        enum_pg(FaixaEtaria, "faixa_etaria"), nullable=False, default=FaixaEtaria.desconhecida
    )
    observacao: Mapped[str] = mapped_column(Text, nullable=False, default="")

    cliente: Mapped["Cliente"] = relationship(back_populates="consentimentos")
    usuario: Mapped["Usuario"] = relationship()
    termo: Mapped["Termo"] = relationship(back_populates="consentimentos")
