"""
Testes de GET /health: 200 com o banco acessível, 503 quando o banco
falha, e indicação de modelo carregado.
"""

from fastapi.testclient import TestClient

from app.db.session import get_session
from app.main import app


def test_health_responde_ok():
    with TestClient(app) as client:
        resposta = client.get("/health")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "ok"
    assert corpo["banco"] == "ok"
    # O .tflite está no repositório, então deve estar carregado.
    assert corpo["modelo"] == "carregado"


def test_health_denuncia_modelo_ausente():
    """Sem modelo, o campo `modelo` indica a ausência."""
    with TestClient(app) as client:
        anterior = app.state.modelo_tflite
        app.state.modelo_tflite = None
        try:
            resposta = client.get("/health")
        finally:
            app.state.modelo_tflite = anterior

    # Continua 200: sem modelo o serviço está degradado, não fora do ar.
    assert resposta.status_code == 200
    assert resposta.json()["modelo"] == "ausente"


def test_health_nao_exige_api_key():
    """/health é acessível sem autenticação, para monitoramento externo."""
    with TestClient(app) as client:
        resposta = client.get("/health")
    assert resposta.status_code != 401


def test_health_retorna_503_quando_banco_falha():
    """Falha do banco responde 503, para que monitores externos detectem."""

    async def sessao_quebrada():
        class _SessaoFalsa:
            async def execute(self, *args, **kwargs):
                raise ConnectionError("simulação de Supabase fora do ar")

        yield _SessaoFalsa()

    app.dependency_overrides[get_session] = sessao_quebrada
    try:
        with TestClient(app) as client:
            resposta = client.get("/health")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resposta.status_code == 503
    corpo = resposta.json()
    assert corpo["status"] == "erro"
    assert corpo["banco"] == "indisponivel"
