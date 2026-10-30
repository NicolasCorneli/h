"""Confere se o banco está na mesma versão do código (migrations aplicadas).

Quando o código é atualizado e `alembic upgrade head` não roda, o servidor sobe, mas
qualquer consulta a uma tabela ou coluna nova falha com erro 500 genérico. Esta
verificação transforma isso num aviso claro no terminal e no `/api/v1/saude`.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine

RAIZ = Path(__file__).resolve().parents[2]


@lru_cache
def versao_do_codigo() -> str | None:
    """A migration mais recente do código. Não muda com o processo no ar: lida uma vez,
    em vez de a cada sonda de prontidão."""
    configuracao = Config(str(RAIZ / "alembic.ini"))
    configuracao.set_main_option("script_location", str(RAIZ / "migrations"))
    return ScriptDirectory.from_config(configuracao).get_current_head()


def versoes(engine: Engine) -> tuple[str | None, str | None]:
    """Devolve (versão aplicada no banco, versão mais recente do código)."""
    with engine.connect() as conexao:
        aplicada = MigrationContext.configure(conexao).get_current_revision()
    return aplicada, versao_do_codigo()


def banco_atualizado(engine: Engine) -> bool:
    aplicada, mais_recente = versoes(engine)
    return aplicada == mais_recente
