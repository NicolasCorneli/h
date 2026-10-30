"""gênero do corte na simulação

A etapa "Estilo e cor" ganhou a opção "Gênero" (feminino, masculino ou não especificar),
enviada ao `change-haircut` no campo `gender`. A geração roda em segundo plano e remonta o
pedido a partir da linha gravada, então o valor precisa ficar na simulação:

- `simulacoes.genero` (nova): o valor exato do campo do modelo, "none", "male" ou
  "female", conferido por restrição.

Os registros existentes ficam com "none", que é o padrão do próprio modelo e é como eles
foram gerados: até aqui o campo não era enviado. Nada é inventado.

A volta apaga a coluna.

Revision ID: d2f6a8c31e94
Revises: c6a2f9d41b87
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "d2f6a8c31e94"
down_revision: str | None = "c6a2f9d41b87"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "simulacoes",
        sa.Column("genero", sa.String(10), nullable=False, server_default="none"),
    )
    op.create_check_constraint(
        op.f("ck_simulacoes_genero_valido"), "simulacoes", "genero IN ('none', 'male', 'female')"
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_simulacoes_genero_valido"), "simulacoes", type_="check")
    op.drop_column("simulacoes", "genero")
