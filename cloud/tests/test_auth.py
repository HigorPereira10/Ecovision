"""
Testes de POST /auth/login e POST /auth/refresh:

1. login correto devolve os dois tokens;
2. senha errada e e-mail inexistente devolvem o mesmo 401;
3. token de renovação válido gera novo token de acesso;
4. token de acesso no lugar do de renovação, ou token inválido, é recusado.
"""

from fastapi.testclient import TestClient

from app.core.security import criar_access_token
from app.db.models import Usuario
from app.main import app


async def test_login_com_credenciais_corretas_retorna_tokens(usuario_produtor: Usuario):
    with TestClient(app) as client:
        resposta = client.post(
            "/auth/login", json={"email": "produtor@teste.com", "senha": "senha-correta"}
        )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["access_token"]
    assert corpo["refresh_token"]
    assert corpo["token_type"] == "bearer"


async def test_login_com_senha_errada_retorna_401(usuario_produtor: Usuario):
    with TestClient(app) as client:
        resposta = client.post(
            "/auth/login", json={"email": "produtor@teste.com", "senha": "senha-errada"}
        )
    assert resposta.status_code == 401


async def test_login_com_email_inexistente_retorna_mesmo_401():
    with TestClient(app) as client:
        resposta = client.post(
            "/auth/login", json={"email": "nao-existe@teste.com", "senha": "qualquer"}
        )
    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "Email ou senha inválidos."


async def test_refresh_com_token_valido_gera_novo_access_token(usuario_produtor: Usuario):
    with TestClient(app) as client:
        login = client.post(
            "/auth/login", json={"email": "produtor@teste.com", "senha": "senha-correta"}
        )
        refresh_token = login.json()["refresh_token"]

        resposta = client.post("/auth/refresh", json={"refresh_token": refresh_token})

    assert resposta.status_code == 200
    assert resposta.json()["access_token"]
    assert resposta.json()["refresh_token"] is None  # nao emite um novo refresh token


async def test_refresh_com_access_token_no_lugar_do_refresh_falha(usuario_produtor: Usuario):
    access_token = criar_access_token(usuario_produtor.id, usuario_produtor.papel)

    with TestClient(app) as client:
        resposta = client.post("/auth/refresh", json={"refresh_token": access_token})

    assert resposta.status_code == 401


async def test_refresh_com_token_invalido_falha():
    with TestClient(app) as client:
        resposta = client.post("/auth/refresh", json={"refresh_token": "isso-nao-e-um-jwt"})
    assert resposta.status_code == 401
