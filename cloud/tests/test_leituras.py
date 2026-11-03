"""
cloud/tests/test_leituras.py

O que este arquivo verifica, em português simples:

POST /leituras, o ciclo de sensor SEM foto que o Pi manda a cada 15
minutos (ver app/api/routes/leituras.py e edge/src/sensores.py):

1. Sem credencial de dispositivo, a API recusa com 401, igual a
   POST /diagnostico.
2. Uma leitura aceita é gravada sem registro de imagem, e aparece em
   GET /leituras para o dono do dispositivo.
3. O JOIN que foi removido de GET /leituras: se ele voltar, a leitura
   sem foto desaparece da resposta sem nenhum erro aparente. É a
   regressão mais perigosa deste conjunto, porque o sintoma seria
   apenas "o gráfico voltou a ter poucos pontos".
4. Reenvio com a mesma idempotency_key não cria linha duplicada.
5. Leitura fora de faixa gera alerta ambiental pelo MESMO caminho de
   POST /diagnostico, porque os dois usam
   app/api/alertas_de_leitura.py.
6. Requisição com as três medições nulas é aceita: "o ciclo rodou e
   nenhum sensor respondeu" é informação diferente de "não houve
   ciclo", e é o que impede a tela de mostrar a leitura de duas horas
   atrás como se fosse a atual.
"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alerta, LeituraAmbiental
from app.db.session import engine
from app.main import app

CREDENCIAL = {"Authorization": "chave-de-teste-dispositivo"}


def _corpo(**overrides) -> dict:
    dados = {
        "device_id": "pi-teste",
        "idempotency_key": "leitura-de-teste-001",
        "temperatura_c": 26.4,
        "umidade_ar_pct": 68.0,
        "umidade_solo_pct": 52.0,
    }
    dados.update(overrides)
    return dados


async def test_sem_credencial_retorna_401():
    with TestClient(app) as client:
        resposta = client.post("/leituras", json=_corpo())
    assert resposta.status_code == 401


async def test_leitura_e_gravada_sem_registro_de_imagem():
    with TestClient(app) as client:
        resposta = client.post("/leituras", json=_corpo(), headers=CREDENCIAL)

    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["device_id"] == "pi-teste"
    assert corpo["temperatura_c"] == 26.4
    assert corpo["tem_foto"] is False, (
        "leitura de ciclo sem foto tem que se identificar como tal, senao a "
        "tela nao tem como explicar por que ha mais pontos de ambiente do "
        "que diagnosticos"
    )

    async with AsyncSession(engine) as sessao:
        leituras = (await sessao.execute(select(LeituraAmbiental))).scalars().all()

    assert len(leituras) == 1
    assert leituras[0].registro_imagem_id is None
    assert leituras[0].device_id == "pi-teste"


async def test_leitura_sem_foto_aparece_em_get_leituras(token_produtor: str):
    """A regressao mais perigosa deste arquivo.

    GET /leituras usava INNER JOIN com registros_imagem, porque era a
    unica forma de saber o dispositivo da leitura antes de `device_id`
    virar coluna propria. Com o JOIN de volta, TODA leitura sem foto
    sai da resposta e nada falha: o sintoma e so o grafico da tela
    inicial voltar a ter um ponto a cada 2 horas, que e exatamente o
    que o desacoplamento foi feito para resolver.
    """
    with TestClient(app) as client:
        envio = client.post("/leituras", json=_corpo(), headers=CREDENCIAL)
        assert envio.status_code == 201

        resposta = client.get(
            "/leituras", headers={"Authorization": f"Bearer {token_produtor}"}
        )

    assert resposta.status_code == 200
    itens = resposta.json()
    assert len(itens) == 1, (
        "a leitura sem foto sumiu de GET /leituras: provavelmente o JOIN com "
        "registros_imagem voltou para a consulta"
    )
    assert itens[0]["temperatura_c"] == 26.4
    assert itens[0]["tem_foto"] is False


async def test_reenvio_com_mesma_chave_nao_duplica():
    with TestClient(app) as client:
        primeira = client.post("/leituras", json=_corpo(), headers=CREDENCIAL)
        segunda = client.post("/leituras", json=_corpo(), headers=CREDENCIAL)

    assert primeira.status_code == 201
    # O reenvio devolve a MESMA linha, nao uma nova.
    assert segunda.json()["id"] == primeira.json()["id"]

    async with AsyncSession(engine) as sessao:
        leituras = (await sessao.execute(select(LeituraAmbiental))).scalars().all()
    assert len(leituras) == 1, "reenvio criou linha duplicada"


async def test_leitura_fora_de_faixa_gera_alerta_ambiental():
    """Mesmo comportamento de POST /diagnostico, pelo mesmo codigo.

    Se este teste falhar e o equivalente em test_diagnostico.py passar,
    os dois caminhos divergiram, que e justamente o que
    app/api/alertas_de_leitura.py existe para impedir.
    """
    with TestClient(app) as client:
        resposta = client.post(
            "/leituras",
            json=_corpo(temperatura_c=38.0),  # acima de TEMPERATURA_MAX_C
            headers=CREDENCIAL,
        )

    assert resposta.status_code == 201
    async with AsyncSession(engine) as sessao:
        alertas = (await sessao.execute(select(Alerta))).scalars().all()

    assert len(alertas) == 1
    assert alertas[0].leitura_id is not None
    assert alertas[0].diagnostico_id is None, (
        "leitura sem foto nao pode gerar alerta de diagnostico: nao houve "
        "diagnostico nenhum"
    )
    assert "temperatura" in alertas[0].descricao.lower()


async def test_ciclo_em_que_nenhum_sensor_respondeu_e_aceito():
    """Tres medicoes nulas e um registro valido, nao um erro.

    "O ciclo rodou as 14:15 e nenhum sensor respondeu" e informacao
    diferente de "nao houve ciclo". Sem ela, a tela nao distingue sensor
    quebrado de Pi desligado, e continuaria exibindo a ultima leitura
    boa como se fosse a atual.
    """
    with TestClient(app) as client:
        resposta = client.post(
            "/leituras",
            json=_corpo(temperatura_c=None, umidade_ar_pct=None, umidade_solo_pct=None),
            headers=CREDENCIAL,
        )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["temperatura_c"] is None
    assert corpo["umidade_ar_pct"] is None
    assert corpo["umidade_solo_pct"] is None

    async with AsyncSession(engine) as sessao:
        alertas = (await sessao.execute(select(Alerta))).scalars().all()
    assert alertas == [], (
        "medicao ausente nao e medicao fora de faixa: alertar aqui encheria o "
        "painel toda vez que o DHT22 falhasse"
    )


async def test_leitura_recebe_horario_de_chegada():
    """criado_em e preenchido pelo default do modelo, nao pelo Pi.

    Diferente de POST /diagnostico, que recebe `timestamp` do
    dispositivo porque a foto pode ficar horas na fila offline antes de
    subir. Leitura de sensor nao passa pela fila (ver o cabecalho de
    app/api/routes/leituras.py), entao a hora de chegada e a hora da
    medicao, e confiar no relogio do Pi seria introduzir uma fonte de
    erro sem ganho nenhum.
    """
    antes = datetime.now(timezone.utc)
    with TestClient(app) as client:
        resposta = client.post("/leituras", json=_corpo(), headers=CREDENCIAL)
    assert resposta.status_code == 201

    criado_em = datetime.fromisoformat(resposta.json()["criado_em"])
    if criado_em.tzinfo is None:
        criado_em = criado_em.replace(tzinfo=timezone.utc)
    assert criado_em >= antes.replace(microsecond=0)
