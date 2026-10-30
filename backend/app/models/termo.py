from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Date, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CriadoEm, IdUUID
from app.models.enums import TipoTermo
from app.models.tipos_sql import enum_pg

if TYPE_CHECKING:
    from app.models.ciencia import Ciencia
    from app.models.consentimento import Consentimento


class Termo(IdUUID, CriadoEm, Base):
    """Versão publicada de um termo.

    Uma versão publicada não é alterada: se o texto muda, publica-se 1.1 e os
    consentimentos antigos continuam apontando para a versão que foi apresentada.
    O gatilho `termos_imutaveis` (ver migration inicial) garante isso no banco — só a
    marcação de vigência pode mudar.
    """

    __tablename__ = "termos"
    __table_args__ = (
        UniqueConstraint("tipo", "versao", name="uq_termos_tipo_versao"),
        # Exatamente uma versão vigente por tipo.
        Index(
            "uq_termos_vigente_por_tipo",
            "tipo",
            unique=True,
            postgresql_where=text("vigente"),
        ),
    )

    tipo: Mapped[TipoTermo] = mapped_column(enum_pg(TipoTermo, "tipo_termo"), nullable=False)
    versao: Mapped[str] = mapped_column(String(10), nullable=False)
    vigente_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vigente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    resumo: Mapped[str] = mapped_column(Text, nullable=False, default="")
    #: Mesma forma de `Termo.secoes` no aplicativo: [{titulo, texto, destaque}].
    secoes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)

    consentimentos: Mapped[list["Consentimento"]] = relationship(back_populates="termo")
    ciencias: Mapped[list["Ciencia"]] = relationship(back_populates="termo")
