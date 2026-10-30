"""remove a foto de referência da simulação

A foto de referência do corte saiu do sistema (decisão de escopo e custo para o protótipo
do TCC): o aplicativo não envia mais referência, e o servidor não usa mais o modelo de duas
imagens. A coluna `simulacoes.usou_referencia`, criada na migration anterior, deixa de ter
quem a escreva.

A volta recria a coluna e a preenche a partir do que ficou gravado: a instrução enviada ao
modelo de duas imagens sempre começava dizendo que a segunda imagem era só referência
(`instrucao_ia`). Nada é inventado.

Revision ID: c6a2f9d41b87
Revises: b9d4e1f27c35
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "c6a2f9d41b87"
down_revision: str | None = "b9d4e1f27c35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Trecho fixo da instrução do modelo de duas imagens (ver o histórico de `instrucoes.py`).
MARCA_DA_REFERENCIA = "%The second image is only a hairstyle reference%"


def upgrade() -> None:
    op.drop_column("simulacoes", "usou_referencia")


def downgrade() -> None:
    op.add_column(
        "simulacoes",
        sa.Column("usou_referencia", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.get_bind().execute(
        sa.text("UPDATE simulacoes SET usou_referencia = true WHERE instrucao_ia LIKE :marca"),
        {"marca": MARCA_DA_REFERENCIA},
    )
