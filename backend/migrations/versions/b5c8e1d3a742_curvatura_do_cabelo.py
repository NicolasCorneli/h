"""curvatura natural do cabelo na simulação

A etapa "Estilo e cor" ganhou a pergunta opcional "Como é o cabelo natural?" (liso,
ondulado, cacheado ou crespo, com o tipo detalhado de 1A a 4C, ou "Não sei informar"). A
resposta não é parâmetro de nenhum modelo: vira uma frase da instrução do Nano Banana, para
ajudar a preservar a curvatura, que os testes com usuários mostraram ser aberta pela
simulação. A geração roda em segundo plano e remonta o pedido a partir da linha gravada,
então o valor precisa ficar na simulação, como o gênero do corte:

- `simulacoes.curvatura` (nova, opcional): a categoria ou o tipo, conferido por restrição.

Os registros existentes ficam nulos ("Não sei informar"), que é como foram gerados. Nada é
inventado. A curvatura não é gravada no cadastro do cliente: só acompanha o pedido em que
foi informada.

A volta apaga a coluna.

Revision ID: b5c8e1d3a742
Revises: a9e4c2b7d158
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "b5c8e1d3a742"
down_revision: str | None = "a9e4c2b7d158"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VALORES = (
    "liso", "ondulado", "cacheado", "crespo",
    "1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C", "4A", "4B", "4C",
)


def upgrade() -> None:
    op.add_column("simulacoes", sa.Column("curvatura", sa.String(10), nullable=True))
    lista = ", ".join(f"'{valor}'" for valor in VALORES)
    op.create_check_constraint(
        op.f("ck_simulacoes_curvatura_valida"),
        "simulacoes",
        f"curvatura IS NULL OR curvatura IN ({lista})",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_simulacoes_curvatura_valida"), "simulacoes", type_="check")
    op.drop_column("simulacoes", "curvatura")
