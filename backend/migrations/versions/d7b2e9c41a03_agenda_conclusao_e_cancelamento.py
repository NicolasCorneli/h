"""agenda: conclusão vinculada ao atendimento, e cancelamento registrado

Até aqui, concluir um agendamento só trocava o status: nenhum atendimento era criado e
não havia relação entre os dois no banco. O histórico do cliente dependia de alguém lembrar
de registrar o atendimento à parte, e nada impedia registrá-lo duas vezes.

Esta migration acrescenta, sem tocar nos registros existentes:

- `atendimentos.agendamento_id`: o compromisso de origem, quando houver. Opcional, porque
  atendimentos antigos e avulsos continuam válidos sem ele. `ON DELETE SET NULL`: apagar
  o agendamento não apaga o histórico do serviço prestado;
- índice único parcial sobre `agendamento_id`: um agendamento gera no máximo um
  atendimento. É a garantia contra duplicidade no banco, não só no código;
- `atendimentos.realizado_em`: o instante em que o serviço de fato terminou. Distinto do
  horário marcado, que continua em `agendamentos.data_hora` e não é sobrescrito;
- `agendamentos.cancelado_em` e `motivo_cancelamento`: quando e por que um compromisso foi
  cancelado. O cancelamento preserva o registro, em vez de apagá-lo.

Registros antigos ficam com esses campos vazios. Não se inventa a data de um
cancelamento que já aconteceu nem o horário real de um atendimento antigo.

Revision ID: d7b2e9c41a03
Revises: c3f1a2d45e60
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "d7b2e9c41a03"
down_revision: str | None = "c3f1a2d45e60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "atendimentos",
        sa.Column(
            "agendamento_id",
            sa.Uuid(),
            sa.ForeignKey("agendamentos.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "atendimentos",
        sa.Column("realizado_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "uq_atendimentos_agendamento_id",
        "atendimentos",
        ["agendamento_id"],
        unique=True,
        postgresql_where=sa.text("agendamento_id IS NOT NULL"),
    )

    op.add_column(
        "agendamentos",
        sa.Column("cancelado_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "agendamentos",
        sa.Column(
            "motivo_cancelamento",
            sa.String(300),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("agendamentos", "motivo_cancelamento")
    op.drop_column("agendamentos", "cancelado_em")
    op.drop_index("uq_atendimentos_agendamento_id", table_name="atendimentos")
    op.drop_column("atendimentos", "realizado_em")
    op.drop_column("atendimentos", "agendamento_id")
