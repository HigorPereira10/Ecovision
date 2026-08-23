"""
cloud/app/db/session.py

Configuração da conexão assíncrona com o banco (Supabase Postgres em
produção, via asyncpg; SQLite em memória nos testes, ver
cloud/tests/conftest.py), via SQLAlchemy async.

Relação com o resto do sistema:
- Usado por todos os routers que leem/escrevem dados de negócio, via a
  dependency get_session().
- As migrations correspondentes a este engine ficam em cloud/alembic/.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL)

_SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency FastAPI: fornece uma sessão async por requisição."""
    async with _SessionLocal() as sessao:
        yield sessao
