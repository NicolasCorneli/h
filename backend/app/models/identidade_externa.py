from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CriadoEm, IdUUID

if TYPE_CHECKING:
    from app.models.usuario import Usuario


class IdentidadeExterna(IdUUID, CriadoEm, Base):
    """Uma forma de entrar fornecida por terceiro (hoje, só o Google) ligada a uma conta.

    A identidade é o `sub` do provedor: identificador estável, que não muda quando a
    pessoa troca de e-mail. O e-mail fica guardado só como referência do que estava na
    conta Google no momento do vínculo; ele nunca é usado para encontrar a conta.
    """

    __tablename__ = "identidades_externas"
    __table_args__ = (
        # A mesma conta Google não entra em duas contas do aplicativo...
        UniqueConstraint("provedor", "sujeito"),
        # ...e uma conta do aplicativo tem no máximo uma conta Google ligada.
        UniqueConstraint("usuario_id", "provedor"),
    )

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provedor: Mapped[str] = mapped_column(String(20), nullable=False)
    sujeito: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)

    usuario: Mapped["Usuario"] = relationship(back_populates="identidades")
