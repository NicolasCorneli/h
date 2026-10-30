"""versão da sessão: encerrar sessões no servidor

Os tokens de acesso e de renovação levam a versão da sessão da conta (`sv`). Trocar a
senha ou pedir "sair de todos os aparelhos" incrementa a versão, e todo token emitido
antes passa a ser recusado. Até aqui não havia como invalidar um token de renovação
copiado antes de ele expirar (30 dias).

- `usuarios.versao_sessao` (nova): inteiro, começa em 0.

Os registros existentes ficam com 0, que é também a versão assumida para tokens emitidos
antes desta mudança (sem `sv`): ninguém é desconectado pela atualização.

A volta apaga a coluna. Tokens emitidos depois da mudança continuam aceitos pelo código
anterior, que ignora o campo `sv`.

Revision ID: e1b4c7d29a50
Revises: d2f6a8c31e94
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "e1b4c7d29a50"
down_revision: str | None = "d2f6a8c31e94"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("versao_sessao", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "versao_sessao")
