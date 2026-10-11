"""
cloud/tests/test_health.py

O que este arquivo verifica, em português simples:

`GET /health` é o endpoint que o UptimeRobot vai pingar periodicamente
para manter o Supabase (que pausa sozinho após 7 dias sem uso) e o
Railway ativos. Ver infra/monitoring/uptimerobot.md.

Confere três coisas:
1. Responde 200 e realmente consegue falar com o banco (não é só "o
   processo está de pé", é "o processo está de pé E consegue consultar
   o banco").
2. Devolve 503, não 200, quando o banco falha.
3. Informa se o modelo de IA está carregado. Sem isso, uma API rodando
   sem modelo classifica toda captura como "indisponivel" e nada
   denuncia de fora; já aconteceu uma vez.
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
    # Nos testes o .tflite real existe no repositório, então tem que
    # estar carregado. Se este assert falhar, o caminho do modelo
    # quebrou (ver caminho_do_modelo em app/config.py).
    assert corpo["modelo"] == "carregado"


def test_health_denuncia_modelo_ausente():
    """A checagem que torna visível uma falha que já passou despercebida
    em produção: a API subiu sem o .tflite, devolveu placeholder em toda
    captura, e o único sintoma era diagnóstico vazio no app,
    indistinguível de dispositivo que não capturou."""
    with TestClient(app) as client:
        anterior = app.state.modelo_tflite
        app.state.modelo_tflite = None
        try:
            resposta = client.get("/health")
        finally:
            app.state.modelo_tflite = anterior

    # Continua 200: sem modelo o serviço está DEGRADADO, não fora do ar,
    # e alarmar o UptimeRobot por isso ensinaria o grupo a ignorar alarme.
    assert resposta.status_code == 200
    assert resposta.json()["modelo"] == "ausente"


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
    corpo = resposta.json()
    assert corpo["status"] == "erro"
    assert corpo["banco"] == "indisponivel"
