"""entrar com Google: identidades externas e conta sem senha

Acrescenta a tabela `identidades_externas`, que liga uma conta do aplicativo a uma conta
de um provedor de identidade (hoje, só o Google), pelo identificador estável do provedor
(`sub`). Duas restrições únicas garantem, no banco, que uma conta Google não entra em duas
contas daqui e que uma conta daqui tem no máximo uma conta Google.

`usuarios.senha_hash` passa a aceitar vazio: quem se cadastra pelo Google não cria senha.
Nenhum registro existente muda; todas as contas atuais continuam com a senha que têm.

A volta (downgrade) remove a tabela e torna a senha obrigatória de novo. Se já houver
conta sem senha, a volta se recusa em vez de apagar contas ou inventar senhas: essas
contas precisam ser tratadas antes, de forma consciente.

Revision ID: e5a9c3f17b20
Revises: d7b2e9c41a03
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "e5a9c3f17b20"
down_revision: str | None = "d7b2e9c41a03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "identidades_externas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("provedor", sa.String(length=20), nullable=False),
        sa.Column("sujeito", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuarios.id"],
            name=op.f("fk_identidades_externas_usuario_id"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_identidades_externas")),
        sa.UniqueConstraint(
            "provedor", "sujeito", name=op.f("uq_identidades_externas_provedor_sujeito")
        ),
        sa.UniqueConstraint(
            "usuario_id", "provedor", name=op.f("uq_identidades_externas_usuario_id_provedor")
        ),
    )
    op.create_index(
        op.f("ix_identidades_externas_usuario_id"),
        "identidades_externas",
        ["usuario_id"],
        unique=False,
    )
    op.alter_column("usuarios", "senha_hash", existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    sem_senha = op.get_bind().scalar(sa.text("SELECT count(*) FROM usuarios WHERE senha_hash IS NULL"))
    if sem_senha:
        raise RuntimeError(
            f"{sem_senha} conta(s) sem senha, criadas pelo Google. A volta exigiria apagá-las "
            "ou inventar senhas; trate essas contas antes de desfazer esta migration."
        )
    op.alter_column("usuarios", "senha_hash", existing_type=sa.String(length=255), nullable=False)
    op.drop_index(op.f("ix_identidades_externas_usuario_id"), table_name="identidades_externas")
    op.drop_table("identidades_externas")
