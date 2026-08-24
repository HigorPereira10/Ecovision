"""
cloud/alembic/env.py

Gerado por `alembic init`, adaptado para:
- Usar a MetaData real dos modelos (app/db/models.py), o que habilita
  `alembic revision --autogenerate` a partir daqui em diante.
- Ler a URL do banco de app/config.py (settings.DATABASE_URL) em vez de
  alembic.ini, para não duplicar/desalinhar configuração.
- Rodar as migrations com um engine assíncrono (asyncpg), já que o
  projeto inteiro usa SQLAlchemy async (app/db/session.py). Ver
  https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Garante que "app" (cloud/app/) é importável independente de onde o
# comando `alembic` é chamado (mesmo padrão de ancoragem usado em
# edge/src/config.py).
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.db.models import Base  # noqa: E402

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _rodar_migrations_sincrono(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_rodar_migrations_sincrono)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
