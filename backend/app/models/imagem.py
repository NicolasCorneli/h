from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CriadoEm, IdUUID
from app.models.enums import TipoImagem
from app.models.tipos_sql import enum_pg

if TYPE_CHECKING:
    from app.models.usuario import Usuario


class Imagem(IdUUID, CriadoEm, Base):
    """Metadados de um objeto guardado no storage.

    O binário **não** fica no PostgreSQL (seção 19 da especificação): o banco guarda a
    chave do objeto, e o acesso é sempre por URL assinada de curta duração.
    """

    __tablename__ = "imagens"
    __table_args__ = (
        CheckConstraint("largura > 0 AND altura > 0", name="dimensoes_positivas"),
        CheckConstraint("bytes > 0", name="bytes_positivo"),
        # No máximo uma foto de perfil por cliente.
        Index(
            "uq_imagens_perfil_por_cliente",
            "cliente_id",
            unique=True,
            postgresql_where=text("tipo = 'perfil'"),
        ),
        Index("ix_imagens_cliente_id_tipo", "cliente_id", "tipo"),
        Index("ix_imagens_usuario_id", "usuario_id"),
        # No máximo uma foto do próprio profissional (perfil sem cliente).
        Index(
            "uq_imagens_perfil_do_usuario",
            "usuario_id",
            unique=True,
            postgresql_where=text("tipo = 'perfil' AND cliente_id IS NULL"),
        ),
    )

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=True
    )
    tipo: Mapped[TipoImagem] = mapped_column(enum_pg(TipoImagem, "tipo_imagem"), nullable=False)
    chave_objeto: Mapped[str] = mapped_column(String(400), nullable=False, unique=True)
    mime: Mapped[str] = mapped_column(String(40), nullable=False)
    bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    largura: Mapped[int] = mapped_column(Integer, nullable=False)
    altura: Mapped[int] = mapped_column(Integer, nullable=False)

    usuario: Mapped["Usuario"] = relationship(back_populates="imagens")
