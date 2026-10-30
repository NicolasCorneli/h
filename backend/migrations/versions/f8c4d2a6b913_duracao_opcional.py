"""duração opcional no agendamento, e duração do atendimento

A duração prevista deixa de ser obrigatória: o profissional pode criar um agendamento sem
informá-la. Antes, quem não escolhia ficava com 60 minutos sem ter dito isso.

- `agendamentos.duracao_min` passa a aceitar vazio. Os registros existentes não mudam:
  quem já tinha 60 continua com 60 (não há como saber quais 60 foram escolhidos de fato,
  então nada é apagado);
- `atendimentos.duracao_min` (nova, opcional): quanto o atendimento durou, informado na
  conclusão ou no registro direto pelo perfil do cliente. Mesma faixa do agendamento.

A volta torna a duração do agendamento obrigatória de novo. Se houver agendamento sem
duração, ela se recusa em vez de preencher um valor inventado.

Revision ID: f8c4d2a6b913
Revises: e5a9c3f17b20
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "f8c4d2a6b913"
down_revision: str | None = "e5a9c3f17b20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("agendamentos", "duracao_min", existing_type=sa.Integer(), nullable=True)
    op.add_column("atendimentos", sa.Column("duracao_min", sa.Integer(), nullable=True))
    op.create_check_constraint(
        op.f("ck_atendimentos_duracao_plausivel"),
        "atendimentos",
        "duracao_min BETWEEN 15 AND 480",
    )


def downgrade() -> None:
    sem_duracao = op.get_bind().scalar(
        sa.text("SELECT count(*) FROM agendamentos WHERE duracao_min IS NULL")
    )
    if sem_duracao:
        raise RuntimeError(
            f"{sem_duracao} agendamento(s) sem duração prevista. A volta exigiria inventar "
            "uma duração para eles; trate esses registros antes de desfazer esta migration."
        )
    op.drop_constraint(op.f("ck_atendimentos_duracao_plausivel"), "atendimentos", type_="check")
    op.drop_column("atendimentos", "duracao_min")
    op.alter_column("agendamentos", "duracao_min", existing_type=sa.Integer(), nullable=False)
