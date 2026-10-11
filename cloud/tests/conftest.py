"""
cloud/tests/conftest.py

Configuração compartilhada dos testes automatizados de cloud/app/.

app/config.py exige variáveis de ambiente (URL do Supabase, API Key do
dispositivo, string de conexão do banco) assim que é importado. Para os
testes rodarem sem precisar de um Supabase/Postgres reais, este
conftest define valores de teste ANTES de qualquer teste ser coletado,
incluindo um banco SQLite em arquivo temporário no lugar do Postgres
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

# Desliga o envio de email À FORÇA (os.environ vence o .env na ordem de
# precedência do pydantic-settings). Não é setdefault: precisa
# sobrescrever mesmo quando a variável existe.
#
# Sem isto, a suíte lia o cloud/.env de quem estivesse rodando e tentava
# MANDAR EMAIL DE VERDADE a cada cadastro de teste. Além de deixar os
# testes lentos e dependentes de rede, o resultado passava a variar
# conforme a máquina: quem tivesse SMTP configurado via falhas que
# ninguém mais via. Os testes que precisam de email ligado simulam isso
# por monkeypatch (ver test_email_verificacao.py).
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
    """Cria um produtor de teste no banco (email/senha conhecidos,
    usados por test_auth.py). Usado também por outros testes que
    só precisam de QUALQUER usuário válido para gerar um token."""
    async with _SessionLocal() as sessao:
        usuario = Usuario(
            email="produtor@teste.com",
            senha_hash=gerar_hash_senha("senha-correta"),
            papel="produtor",
            # Criado direto no banco, sem passar pelo cadastro, então
            # precisa nascer verificado: o login recusa conta pendente
            # de confirmação por email.
            email_verificado=True,
        )
        sessao.add(usuario)
        await sessao.commit()
        await sessao.refresh(usuario)
        return usuario


@pytest_asyncio.fixture
async def dispositivo_do_produtor(usuario_produtor: Usuario) -> Dispositivo:
    """Vincula o device_id "pi-teste" (o usado por todos os testes que
    gravam capturas) ao produtor de teste.

    Necessário desde que as rotas passaram a filtrar por dono
    (app/api/escopo.py): sem uma linha em `dispositivos` ligando o
    device_id a um usuário, a captura não tem dono e não aparece para
    ninguém. É a mesma exigência que vale em produção, onde o vínculo é
    criado por scripts/seed_dispositivo_teste.py."""
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
    """Access token JWT válido para um produtor de teste, pronto para
    usar no header Authorization dos endpoints do dashboard.

    Depende de dispositivo_do_produtor de propósito: o caso comum nos
    testes é "o produtor consultando os dados DELE", então o vínculo
    precisa existir. Os testes de isolamento entre produtores
    (test_escopo.py) montam o cenário na mão, sem esta fixture."""
    return criar_access_token(usuario_produtor.id, usuario_produtor.papel)
