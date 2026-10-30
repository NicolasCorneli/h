from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from app.core.config import obter_config
from app.db.base import Base
from app.models import *  # noqa: F401,F403  (popula Base.metadata)

config = context.config
if config.config_file_name is not None:
    # `disable_existing_loggers` vem True por padrão e desligaria todos os loggers já
    # criados — inclusive os da aplicação. Quando as migrations rodam no mesmo processo
    # (como na suíte de testes), isso apaga o log do sistema inteiro em silêncio.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

config.set_main_option("sqlalchemy.url", obter_config().database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


#: Chave do advisory lock das migrations (um número qualquer, fixo para este sistema).
TRAVA_DAS_MIGRATIONS = 7_342_195_001


def run_migrations_online() -> None:
    conectavel = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with conectavel.connect() as conexao:
        # Duas instâncias subindo juntas rodariam as mesmas migrations ao mesmo tempo, e a
        # segunda falharia no meio (tabela que já existe) ou aplicaria duas vezes. Com a
        # trava, a segunda espera a primeira terminar e então encontra o banco em dia.
        # A trava é da sessão e sai com a conexão, mesmo se a migration falhar.
        conexao.execute(text("SELECT pg_advisory_lock(:chave)"), {"chave": TRAVA_DAS_MIGRATIONS})
        conexao.commit()
        try:
            context.configure(
                connection=conexao, target_metadata=target_metadata, compare_type=True
            )
            with context.begin_transaction():
                context.run_migrations()
        finally:
            conexao.execute(
                text("SELECT pg_advisory_unlock(:chave)"), {"chave": TRAVA_DAS_MIGRATIONS}
            )
            conexao.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
