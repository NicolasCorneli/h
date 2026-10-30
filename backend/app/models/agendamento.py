from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdUUID, Timestamps
from app.models.enums import StatusAgendamento
from app.models.tipos_sql import enum_pg

if TYPE_CHECKING:
    from app.models.atendimento import Atendimento
    from app.models.cliente import Cliente
    from app.models.usuario import Usuario


class Agendamento(IdUUID, Timestamps, Base):
    """Compromisso da agenda (RF06)."""

    __tablename__ = "agendamentos"
    __table_args__ = (
        Index("ix_agendamentos_usuario_id_data_hora", "usuario_id", "data_hora"),
        Index("ix_agendamentos_cliente_id", "cliente_id"),
        CheckConstraint("duracao_min BETWEEN 15 AND 480", name="duracao_plausivel"),
        CheckConstraint("length(servico) > 0", name="servico_preenchido"),
    )

    cliente_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    data_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    servico: Mapped[str] = mapped_column(String(80), nullable=False)
    #: Opcional: vazio quando o profissional não informou. Nunca se presume uma duração.
    duracao_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[StatusAgendamento] = mapped_column(
        enum_pg(StatusAgendamento, "status_agendamento"),
        nullable=False,
        default=StatusAgendamento.pendente,
    )
    observacoes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    lembrete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    #: Quando o compromisso foi cancelado. Vazio em cancelamentos antigos, anteriores a
    #: este campo: não se inventa a data de algo que já aconteceu.
    cancelado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_cancelamento: Mapped[str] = mapped_column(
        String(300), nullable=False, default="", server_default=""
    )

    cliente: Mapped["Cliente"] = relationship(back_populates="agendamentos")
    usuario: Mapped["Usuario"] = relationship(back_populates="agendamentos")
    #: O atendimento gerado ao concluir. No máximo um, garantido por índice único.
    atendimento: Mapped["Atendimento | None"] = relationship(
        back_populates="agendamento", uselist=False
    )

    @property
    def atendimento_id(self):
        return self.atendimento.id if self.atendimento is not None else None
