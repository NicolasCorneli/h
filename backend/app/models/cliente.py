from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdUUID, Timestamps

if TYPE_CHECKING:
    from app.models.agendamento import Agendamento
    from app.models.atendimento import Atendimento
    from app.models.consentimento import Consentimento
    from app.models.imagem import Imagem
    from app.models.simulacao import Simulacao
    from app.models.usuario import Usuario


class Cliente(IdUUID, Timestamps, Base):
    """Cliente da carteira de um profissional.

    O cadastro se sustenta na execução do contrato de serviço (LGPD, art. 7º, V) e é
    independente do consentimento de imagem, que trata apenas das fotografias.
    """

    __tablename__ = "clientes"
    __table_args__ = (Index("ix_clientes_usuario_id_nome", "usuario_id", "nome"),)

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    telefone: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    data_nascimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    observacoes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    usuario: Mapped["Usuario"] = relationship(back_populates="clientes")

    # A foto de perfil é a imagem de tipo `perfil` do cliente — no máximo uma, garantida
    # por índice único parcial em `imagens`. Evita a dependência circular que existiria
    # com uma coluna `foto_imagem_id` apontando para `imagens`.
    foto: Mapped["Imagem | None"] = relationship(
        primaryjoin="and_(Cliente.id == Imagem.cliente_id, Imagem.tipo == 'perfil')",
        viewonly=True,
        uselist=False,
    )

    consentimentos: Mapped[list["Consentimento"]] = relationship(
        back_populates="cliente",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Consentimento.registrado_em.desc()",
    )
    simulacoes: Mapped[list["Simulacao"]] = relationship(
        back_populates="cliente", cascade="all, delete-orphan", passive_deletes=True
    )
    atendimentos: Mapped[list["Atendimento"]] = relationship(
        back_populates="cliente", cascade="all, delete-orphan", passive_deletes=True
    )
    agendamentos: Mapped[list["Agendamento"]] = relationship(
        back_populates="cliente", cascade="all, delete-orphan", passive_deletes=True
    )
