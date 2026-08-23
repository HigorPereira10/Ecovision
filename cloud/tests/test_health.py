"""
cloud/tests/test_health.py

O que este arquivo verifica, em português simples:

`GET /health` é o endpoint que o UptimeRobot vai pingar periodicamente
para manter o Supabase (que pausa sozinho após 7 dias sem uso) e o
Railway ativos. Ver infra/monitoring/uptimerobot.md. Este teste só
confere que ele responde 200 e realmente consegue falar com o banco
(não é só "o processo está de pé", é "o processo está de pé E consegue
consultar o banco").
"""

from fastapi.testclient import TestClient

from app.db.session import get_session
from app.main import app


def test_health_responde_ok():
    with TestClient(app) as client:
        resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "banco": "ok"}


def test_health_nao_exige_api_key():
    """Diferente de /diagnostico, /health precisa ser acessível sem
    autenticação: é o UptimeRobot batendo nele de fora, sem chave."""
    with TestClient(app) as client:
        resposta = client.get("/health")
    assert resposta.status_code != 401


def test_health_retorna_503_quando_banco_falha():
    """ATENÇÃO, BUG JÁ CORRIGIDO: a primeira versão devolvia HTTP 200
    mesmo quando a consulta ao banco falhava. Um monitor externo
    (UptimeRobot) que só olha o status code nunca detectaria a falha
    daquele jeito. Agora precisa ser 503; este teste existe para nunca
    deixar essa regressão voltar."""

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
    assert resposta.json() == {"status": "erro", "banco": "indisponivel"}
