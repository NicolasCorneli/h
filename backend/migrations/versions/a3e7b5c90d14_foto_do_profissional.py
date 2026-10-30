"""foto do profissional: no máximo uma por conta

A foto do próprio profissional é uma imagem de tipo `perfil` sem cliente. O índice único
parcial garante, no banco, que cada conta tenha no máximo uma. Nenhum registro muda.

Revision ID: a3e7b5c90d14
Revises: f8c4d2a6b913
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "a3e7b5c90d14"
down_revision: str | None = "f8c4d2a6b913"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_imagens_perfil_do_usuario",
        "imagens",
        ["usuario_id"],
        unique=True,
        postgresql_where=sa.text("tipo = 'perfil' AND cliente_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_imagens_perfil_do_usuario",
        table_name="imagens",
        postgresql_where=sa.text("tipo = 'perfil' AND cliente_id IS NULL"),
    )
