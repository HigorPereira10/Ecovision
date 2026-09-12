"""
cloud/tests/test_cors.py

O que este arquivo verifica, em português simples:

Sem CORS configurado, o navegador bloquearia a versão web do app/
(Expo web) de chamar esta API, porque ela roda em outra origem
(localhost com outra porta em dev, outro domínio em produção). Este
teste confere que o cabeçalho Access-Control-Allow-Origin vem
preenchido numa resposta normal.
"""

from fastapi.testclient import TestClient

from app.main import app


def test_resposta_inclui_cabecalho_cors():
    with TestClient(app) as client:
        resposta = client.get("/health", headers={"Origin": "http://localhost:8081"})

    assert resposta.headers.get("access-control-allow-origin") == "*"
