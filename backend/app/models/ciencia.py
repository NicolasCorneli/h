from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdUUID

if TYPE_CHECKING:
    from app.models.termo import Termo
    from app.models.usuario import Usuario


class Ciencia(IdUUID, Base):
    """Ciência das responsabilidades do profissional.

    Não é consentimento de imagem: é o reconhecimento de que cabe ao profissional
    informar o cliente — inclusive sobre o envio da foto a uma empresa terceira — antes
    de registrar qualquer decisão. Também é append-only.
    """

    __tablename__ = "ciencias"
    __table_args__ = (Index("ix_ciencias_usuario_id_registrada_em", "usuario_id", "registrada_em"),)

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    termo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("termos.id", ondelete="RESTRICT"), nullable=False
    )
    versao: Mapped[str] = mapped_column(String(10), nullable=False)
    registrada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    usuario: Mapped["Usuario"] = relationship(back_populates="ciencias")
    termo: Mapped["Termo"] = relationship(back_populates="ciencias")
