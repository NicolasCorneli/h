"""índices de desempenho: consultas por conta e chaves estrangeiras

Consultas frequentes que liam a tabela inteira (o PostgreSQL não cria índice para chave
estrangeira sozinho):

- `simulacoes (usuario_id, criado_em)`: a cota de simulações por hora, conferida a cada
  envio, e a expiração das simulações presas, conferida a cada consulta de estado;
- `atendimentos (usuario_id, data_servico)`: o histórico da conta, carregado ao abrir o
  aplicativo;
- `agendamentos (cliente_id)`, `imagens (usuario_id)`, `simulacoes (img_entrada_id)`,
  `simulacoes (img_saida_id)` e `atendimentos (simulacao_id)`: listas por cliente e as
  conferências que o banco faz ao apagar em cascata (cliente, imagem, simulação).

Só índices: nenhum dado muda. Em tabelas grandes, `CREATE INDEX` segura as gravações da
tabela enquanto roda; no porte deste sistema são segundos. A volta apaga os índices.

Revision ID: f3a8d6e2b571
Revises: e1b4c7d29a50
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "f3a8d6e2b571"
down_revision: str | None = "e1b4c7d29a50"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDICES = (
    ("ix_simulacoes_usuario_id_criado_em", "simulacoes", ["usuario_id", "criado_em"]),
    ("ix_simulacoes_img_entrada_id", "simulacoes", ["img_entrada_id"]),
    ("ix_simulacoes_img_saida_id", "simulacoes", ["img_saida_id"]),
    ("ix_atendimentos_usuario_id_data_servico", "atendimentos", ["usuario_id", "data_servico"]),
    ("ix_atendimentos_simulacao_id", "atendimentos", ["simulacao_id"]),
    ("ix_agendamentos_cliente_id", "agendamentos", ["cliente_id"]),
    ("ix_imagens_usuario_id", "imagens", ["usuario_id"]),
)


def upgrade() -> None:
    for nome, tabela, colunas in INDICES:
        op.create_index(nome, tabela, colunas)


def downgrade() -> None:
    for nome, tabela, _ in reversed(INDICES):
        op.drop_index(nome, table_name=tabela)
