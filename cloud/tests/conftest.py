"""
Configuração compartilhada dos testes de cloud/app.

Define as variáveis de ambiente exigidas por app/config.py antes da
coleta, incluindo um banco SQLite temporário no lugar do PostgreSQL (as
tabelas são criadas a partir de app.db.models, sem Alembic).
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

# Desliga o envio de e-mail sobrescrevendo as variáveis (os.environ tem
# precedência sobre o .env), para a suíte nunca enviar e-mails reais. Os
# testes que precisam de envio usam monkeypatch.
for _chave in (
    "BREVO_API_KEY",
    "SMTP_HOST",
    "SMTP_USUARIO",
    "SMTP_SENHA",
    "EMAIL_REMETENTE",
):
    os.environ[_chave] = ""

import pytest_asyncio  # noqa: E402

from app.core.security import criar_access_token, gerar_hash_senha  # noqa: E402
from app.db.models import Base, Dispositivo, Usuario  # noqa: E402
from app.db.session import _SessionLocal, engine  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def _banco_limpo():
    """Cria as tabelas antes de cada teste e apaga tudo depois. Assim,
    cada teste começa com um banco vazio, sem interferir nos outros."""
    async with engine.begin() as conexao:
        await conexao.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conexao:
        await conexao.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def usuario_produtor() -> Usuario:
    """Produtor de teste com e-mail e senha conhecidos."""
    async with _SessionLocal() as sessao:
        usuario = Usuario(
            email="produtor@teste.com",
            senha_hash=gerar_hash_senha("senha-correta"),
            papel="produtor",
            # Criado direto no banco, já verificado (o login recusa conta
            # pendente).
            email_verificado=True,
        )
        sessao.add(usuario)
        await sessao.commit()
        await sessao.refresh(usuario)
        return usuario


@pytest_asyncio.fixture
async def dispositivo_do_produtor(usuario_produtor: Usuario) -> Dispositivo:
    """Vincula o device_id "pi-teste", usado nos testes de captura, ao
    produtor de teste; sem o vínculo, as capturas não têm dono."""
    async with _SessionLocal() as sessao:
        dispositivo = Dispositivo(
            device_id="pi-teste", usuario_id=usuario_produtor.id, nome="Estufa 1"
        )
        sessao.add(dispositivo)
        await sessao.commit()
        await sessao.refresh(dispositivo)
        return dispositivo


@pytest_asyncio.fixture
async def token_produtor(usuario_produtor: Usuario, dispositivo_do_produtor: Dispositivo) -> str:
    """Token de acesso válido do produtor de teste, com o dispositivo já
    vinculado. Os testes de isolamento entre produtores (test_escopo.py)
    montam o cenário sem esta fixture."""
    return criar_access_token(usuario_produtor.id, usuario_produtor.papel)
