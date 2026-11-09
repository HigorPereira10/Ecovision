"""
Sessão assíncrona do SQLAlchemy: PostgreSQL (asyncpg) em produção e
SQLite em memória nos testes.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL)

_SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependência FastAPI que fornece uma sessão por requisição."""
    async with _SessionLocal() as sessao:
        yield sessao
