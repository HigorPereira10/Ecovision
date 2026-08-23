"""
cloud/tests/conftest.py

Configuração compartilhada dos testes automatizados de cloud/app/.

app/config.py exige variáveis de ambiente (URL do Supabase, API Key do
dispositivo, string de conexão do banco) assim que é importado. Para os
testes rodarem sem precisar de um Supabase/Postgres reais, este
conftest define valores de teste ANTES de qualquer teste ser coletado
— incluindo um banco SQLite em arquivo temporário no lugar do Postgres
real (mesmas tabelas, criadas via app.db.models.Base.metadata, sem
precisar do Alembic nos testes).

Como rodar:
    cd cloud
    pip install -r tests/requirements-test.txt
    pytest tests -v
"""

import os
import sys
import tempfile
from pathlib import Path

_CLOUD_DIR = Path(__file__).resolve().parents[1]
if str(_CLOUD_DIR) not in sys.path:
    sys.path.insert(0, str(_CLOUD_DIR))

_DB_PATH = Path(tempfile.gettempdir()) / "ecovision_cloud_teste.db"

os.environ.setdefault("SUPABASE_URL", "https://teste.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "chave-de-teste")
os.environ.setdefault("SUPABASE_STORAGE_BUCKET", "ecovision-imagens-teste")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_DB_PATH.as_posix()}")
os.environ.setdefault("DEVICE_API_KEY", "chave-de-teste-dispositivo")

import pytest_asyncio  # noqa: E402

from app.db.models import Base  # noqa: E402
from app.db.session import engine  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def _banco_limpo():
    """Cria as tabelas antes de cada teste e apaga tudo depois — cada
    teste começa com um banco vazio, sem interferir nos outros."""
    async with engine.begin() as conexao:
        await conexao.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conexao:
        await conexao.run_sync(Base.metadata.drop_all)
