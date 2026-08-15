"""
cloud/app/db/session.py

Configuração da conexão assíncrona com o Supabase Postgres, via
SQLAlchemy async + asyncpg (Blueprint v3.0, Sumário Executivo).

Responsabilidades quando implementado:
- Criar o engine assíncrono a partir de settings.DATABASE_URL
  (app/config.py).
- Expor uma dependency `get_session()` para injeção nos endpoints
  FastAPI (app/api/routes/*.py).

Relação com o resto do sistema:
- Usado por todos os routers que leem/escrevem dados de negócio.
- As migrations correspondentes a este engine ficam em cloud/alembic/.
"""

# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# from app.config import settings

# engine = create_async_engine(settings.DATABASE_URL)

# async def get_session() -> "AsyncSession":
#     """Dependency FastAPI: fornece uma sessão async por requisição."""
#     raise NotImplementedError
