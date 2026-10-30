from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CriadoEm, IdUUID

if TYPE_CHECKING:
    from app.models.agendamento import Agendamento
    from app.models.cliente import Cliente
    from app.models.simulacao import Simulacao
    from app.models.usuario import Usuario


class Atendimento(IdUUID, CriadoEm, Base):
    """Histórico de serviços prestados (RF03) — `historico_servicos` no aplicativo.

    O vínculo com a simulação é opcional e usa `ON DELETE SET NULL`: excluir as imagens de
    um cliente **não** apaga o atendimento, apenas desfaz a referência. Essa é a regra do
    projeto, aqui garantida pelo banco e não por código de aplicação.
    """

    __tablename__ = "atendimentos"
    __table_args__ = (
        Index("ix_atendimentos_cliente_id_data_servico", "cliente_id", "data_servico"),
        # Histórico da conta inteira, carregado ao abrir o aplicativo.
        Index("ix_atendimentos_usuario_id_data_servico", "usuario_id", "data_servico"),
        # Conferido pelo banco ao apagar uma simulação (SET NULL).
        Index("ix_atendimentos_simulacao_id", "simulacao_id"),
        CheckConstraint("duracao_min BETWEEN 15 AND 480", name="duracao_plausivel"),
        # Um agendamento gera no máximo um atendimento: a defesa contra conclusão duplicada
        # está no banco, e não depende de a aplicação se comportar bem.
        Index(
            "uq_atendimentos_agendamento_id",
            "agendamento_id",
            unique=True,
            postgresql_where=text("agendamento_id IS NOT NULL"),
        ),
    )

    cliente_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    simulacao_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("simulacoes.id", ondelete="SET NULL"), nullable=True
    )
    #: O compromisso de origem, quando o atendimento nasceu da agenda. Vazio nos avulsos
    #: e nos antigos. `SET NULL`: apagar o agendamento não apaga o serviço prestado.
    agendamento_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("agendamentos.id", ondelete="SET NULL"), nullable=True
    )
    descricao: Mapped[str] = mapped_column(String(160), nullable=False)
    #: O dia em que o serviço aconteceu, no fuso do salão.
    data_servico: Mapped[date] = mapped_column(Date, nullable=False)
    #: O instante real da conclusão. Distinto do horário marcado no agendamento, que não
    #: é sobrescrito. Vazio nos registros anteriores a este campo.
    realizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Quanto o atendimento durou, quando informado.
    duracao_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    observacoes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    cliente: Mapped["Cliente"] = relationship(back_populates="atendimentos")
    usuario: Mapped["Usuario"] = relationship(back_populates="atendimentos")
    simulacao: Mapped["Simulacao | None"] = relationship()
    agendamento: Mapped["Agendamento | None"] = relationship(back_populates="atendimento")
