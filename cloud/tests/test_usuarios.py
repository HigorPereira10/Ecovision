"""
Testes de GET /usuarios/me: sem login, 401; com login, dados do dono do
token; `nome` não preenchido volta como null.
"""

from fastapi.testclient import TestClient

from app.core.security import criar_access_token, gerar_hash_senha
from app.db.models import Usuario
from app.db.session import _SessionLocal
from app.main import app


async def test_perfil_sem_token_retorna_401():
    with TestClient(app) as client:
        resposta = client.get("/usuarios/me")
    assert resposta.status_code == 401


async def test_perfil_retorna_nome_e_email_do_dono_do_token():
    async with _SessionLocal() as sessao:
        usuario = Usuario(
            nome="Maria Teste",
            email="maria@teste.com",
            senha_hash=gerar_hash_senha("senha"),
            papel="produtor",
            email_verificado=True,
        )
        sessao.add(usuario)
        await sessao.commit()
        await sessao.refresh(usuario)

    token = criar_access_token(usuario.id, usuario.papel)

    with TestClient(app) as client:
        resposta = client.get("/usuarios/me", headers={"Authorization": f"Bearer {token}"})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["nome"] == "Maria Teste"
    assert corpo["email"] == "maria@teste.com"


async def test_perfil_sem_nome_preenchido_devolve_null(usuario_produtor: Usuario):
    token = criar_access_token(usuario_produtor.id, usuario_produtor.papel)

    with TestClient(app) as client:
        resposta = client.get("/usuarios/me", headers={"Authorization": f"Bearer {token}"})

    assert resposta.status_code == 200
    assert resposta.json()["nome"] is None


async def test_perfil_devolve_o_papel_do_usuario(token_produtor: str, usuario_produtor):
    """O app usa o papel para decidir o que mostrar (hoje, o botão de
    notificação de demonstração na tela de Alertas)."""
    with TestClient(app) as client:
        resposta = client.get("/usuarios/me", headers={"Authorization": f"Bearer {token_produtor}"})

    assert resposta.status_code == 200
    assert resposta.json()["papel"] == "produtor"
