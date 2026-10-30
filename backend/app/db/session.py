"""Engine e sessão do SQLAlchemy."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import obter_config

_config = obter_config()

engine = create_engine(
    _config.database_url,
    pool_pre_ping=True,
    pool_size=_config.banco_pool,
    max_overflow=_config.banco_pool_excedente,
    pool_timeout=_config.banco_pool_espera_s,
    # Conexões antigas são renovadas: firewalls e poolers costumam derrubar as ociosas
    # sem avisar, e a próxima consulta nelas falharia.
    pool_recycle=1800,
    echo=False,
)

FabricaSessao = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def obter_sessao() -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão por requisição, com rollback em erro."""
    sessao = FabricaSessao()
    try:
        yield sessao
    except Exception:
        sessao.rollback()
        raise
    finally:
        sessao.close()
