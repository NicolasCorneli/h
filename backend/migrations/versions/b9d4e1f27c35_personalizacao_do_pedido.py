"""personalização do pedido: corte e cor descritos, referência, instrução e envio único

A etapa "Estilo e cor" deixou de ser uma escolha entre seis cortes e seis cores. Agora:

- `simulacoes.estilo` e `simulacoes.cor` guardam a descrição pedida (até 300 caracteres,
  o mesmo limite da API), ou "Corte atual" / "Cor atual" quando nada muda;
- `simulacoes.usou_referencia` (nova): a geração usou uma foto de referência do corte. A
  foto em si não é guardada;
- `simulacoes.instrucao_ia` (nova, opcional): o que foi pedido ao modelo (as opções ou a
  instrução em texto), sem imagens. Serve para conferir e avaliar cada resultado;
- `simulacoes.chave_envio` (nova, opcional): identificador do envio gerado pelo aplicativo.
  O índice único por conta faz o mesmo envio repetido (toque duplo, rede que cai depois de
  o servidor receber) devolver a simulação já criada em vez de pagar outra geração.

Os registros existentes não mudam: rótulos antigos continuam válidos.

A volta reduz as colunas a 60 caracteres e apaga as três novas. Se houver descrição com
mais de 60 caracteres, ela se recusa em vez de cortar o texto pela metade.

Revision ID: b9d4e1f27c35
Revises: a3e7b5c90d14
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "b9d4e1f27c35"
down_revision: str | None = "a3e7b5c90d14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("simulacoes", "estilo", existing_type=sa.String(60), type_=sa.String(300))
    op.alter_column("simulacoes", "cor", existing_type=sa.String(60), type_=sa.String(300))
    op.add_column(
        "simulacoes",
        sa.Column("usou_referencia", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("simulacoes", sa.Column("instrucao_ia", sa.Text(), nullable=True))
    op.add_column("simulacoes", sa.Column("chave_envio", sa.Uuid(), nullable=True))
    op.create_index(
        "uq_simulacoes_chave_envio_por_usuario",
        "simulacoes",
        ["usuario_id", "chave_envio"],
        unique=True,
        postgresql_where=sa.text("chave_envio IS NOT NULL"),
    )


def downgrade() -> None:
    longas = op.get_bind().scalar(
        sa.text(
            "SELECT count(*) FROM simulacoes WHERE char_length(estilo) > 60 OR char_length(cor) > 60"
        )
    )
    if longas:
        raise RuntimeError(
            f"{longas} simulação(ões) com descrição de corte ou cor acima de 60 caracteres. "
            "A volta exigiria cortar o texto; trate esses registros antes de desfazer esta migration."
        )
    op.drop_index(
        "uq_simulacoes_chave_envio_por_usuario",
        table_name="simulacoes",
        postgresql_where=sa.text("chave_envio IS NOT NULL"),
    )
    op.drop_column("simulacoes", "chave_envio")
    op.drop_column("simulacoes", "instrucao_ia")
    op.drop_column("simulacoes", "usou_referencia")
    op.alter_column("simulacoes", "cor", existing_type=sa.String(300), type_=sa.String(60))
    op.alter_column("simulacoes", "estilo", existing_type=sa.String(300), type_=sa.String(60))
