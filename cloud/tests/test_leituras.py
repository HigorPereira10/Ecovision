"""
Testes de POST /leituras, o ciclo de leitura sem foto:

1. sem credencial de dispositivo: 401;
2. a leitura é gravada sem registro de imagem e aparece em GET /leituras;
3. GET /leituras inclui as leituras sem foto;
4. reenvio com a mesma idempotency_key não duplica;
5. leitura fora da faixa gera alerta ambiental pelo mesmo código de
   POST /diagnostico;
6. requisição com as três medições nulas é aceita.
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
    """GET /leituras não pode depender do registro de imagem: um JOIN com
    registros_imagem excluiria todas as leituras sem foto."""
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
    """Os alertas ambientais de POST /leituras seguem a mesma regra de
    POST /diagnostico."""
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
    """Três medições nulas geram um registro válido, que indica ciclo sem
    resposta dos sensores."""
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
    """criado_em é definido pelo servidor: as leituras não passam pela
    fila local, então o momento de chegada é o momento da medição."""
    antes = datetime.now(timezone.utc)
    with TestClient(app) as client:
        resposta = client.post("/leituras", json=_corpo(), headers=CREDENCIAL)
    assert resposta.status_code == 201

    criado_em = datetime.fromisoformat(resposta.json()["criado_em"])
    if criado_em.tzinfo is None:
        criado_em = criado_em.replace(tzinfo=timezone.utc)
    assert criado_em >= antes.replace(microsecond=0)
