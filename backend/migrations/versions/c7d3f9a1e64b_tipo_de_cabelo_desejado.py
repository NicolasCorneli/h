"""tipo de cabelo desejado na simulação

A pergunta da etapa "Estilo e cor" mudou de sentido. Antes era "Como é o cabelo natural?",
só um apoio para o modelo ler a foto. Agora é "Qual tipo de cabelo você deseja na
simulação?": o tipo escolhido (liso, ondulado, cacheado ou crespo, ou um tipo de 1A a 4C)
é aplicado na imagem gerada, e "Manter meu tipo de cabelo atual" é a instrução de preservar
a textura da foto.

Como o significado é outro, o valor novo tem coluna própria, e a antiga não é reaproveitada:

- `simulacoes.textura` (nova, opcional): o tipo desejado, conferido por restrição. Nula é
  "Manter meu tipo de cabelo atual".
- `simulacoes.curvatura` fica como está, com os valores já gravados (o cabelo natural
  informado naqueles pedidos), e deixa de ser preenchida.

Os registros existentes ficam com `textura` nula, que é como foram gerados: nenhum deles
pediu troca de textura. Nada é inventado nem copiado de uma coluna para a outra.

A volta apaga só a coluna nova.

Revision ID: c7d3f9a1e64b
Revises: c8f2a6d4e913
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "c7d3f9a1e64b"
down_revision: str | None = "c8f2a6d4e913"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VALORES = (
    "liso", "ondulado", "cacheado", "crespo",
    "1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C", "4A", "4B", "4C",
)


def upgrade() -> None:
    op.add_column("simulacoes", sa.Column("textura", sa.String(10), nullable=True))
    lista = ", ".join(f"'{valor}'" for valor in VALORES)
    op.create_check_constraint(
        op.f("ck_simulacoes_textura_valida"),
        "simulacoes",
        f"textura IS NULL OR textura IN ({lista})",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_simulacoes_textura_valida"), "simulacoes", type_="check")
    op.drop_column("simulacoes", "textura")
