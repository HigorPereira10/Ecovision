"""
Teste de CORS: o cabeçalho Access-Control-Allow-Origin é enviado, para que
a versão web do aplicativo, em outra origem, consiga chamar a API.
"""

from fastapi.testclient import TestClient

from app.main import app


def test_resposta_inclui_cabecalho_cors():
    with TestClient(app) as client:
        resposta = client.get("/health", headers={"Origin": "http://localhost:8081"})

    assert resposta.headers.get("access-control-allow-origin") == "*"
