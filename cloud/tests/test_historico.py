"""
cloud/tests/test_historico.py

O que este arquivo verifica, em português simples:

Os endpoints de consulta histórica do dashboard (GET /leituras e
GET /diagnosticos):
1. Sem login (sem token JWT), a API recusa com 401.
2. Com login válido, devolvem os dados certos, na ordem certa
   (leituras: mais antiga primeiro, para o gráfico; diagnósticos: mais
   recente primeiro, para o feed de histórico).
3. O filtro `?horas=N` exclui itens mais antigos que o período pedido.
4. GET /diagnosticos inclui a signed URL da imagem (gerar_url_assinada_imagem,
   ver infra/supabase/storage_policies.md), e não quebra a lista
   inteira se a geração da URL falhar para um item específico.
"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Diagnostico, LeituraAmbiental, RegistroImagem
from app.db.session import engine
from app.main import app

AGORA = datetime.now(timezone.utc)


async def _url_assinada_falsa(caminho: str) -> str:
    """Substitui app.storage.supabase_storage.gerar_url_assinada_imagem
    nos testes: não existe Supabase real disponível."""
    return f"https://storage.teste/{caminho}?signed=1"


async def _criar_registro_com_leitura_e_diagnostico(
    sessao: AsyncSession, *, idempotency_key: str, capturado_em: datetime, temperatura_c: float
) -> None:
    registro = RegistroImagem(
        device_id="pi-teste",
        idempotency_key=idempotency_key,
        caminho_arquivo=f"pi-teste/{idempotency_key}.jpg",
        capturado_em=capturado_em,
    )
    sessao.add(registro)
    await sessao.flush()

    # criado_em passado explicitamente (em vez de deixar o default
    # _agora_utc do modelo) para o teste nao depender do relogio real:
    # sem isso, "mais nova"/"mais antiga" ficariam definidas pela ordem
    # de insercao no teste, nao pelo timestamp em si.
    sessao.add(LeituraAmbiental(
        registro_imagem_id=registro.id, temperatura_c=temperatura_c, criado_em=capturado_em
    ))
    sessao.add(Diagnostico(
        registro_imagem_id=registro.id,
        classe_prevista="saudavel",
        confianca=0.95,
        recomendacao=None,
        criado_em=capturado_em,
    ))
    await sessao.commit()


async def test_leituras_sem_token_retorna_401():
    with TestClient(app) as client:
        resposta = client.get("/leituras")
    assert resposta.status_code == 401


async def test_diagnosticos_sem_token_retorna_401():
    with TestClient(app) as client:
        resposta = client.get("/diagnosticos")
    assert resposta.status_code == 401


async def test_leituras_vem_em_ordem_cronologica(token_produtor: str):
    async with AsyncSession(engine) as sessao:
        await _criar_registro_com_leitura_e_diagnostico(
            sessao, idempotency_key="mais-nova", capturado_em=AGORA, temperatura_c=30.0
        )
        await _criar_registro_com_leitura_e_diagnostico(
            sessao,
            idempotency_key="mais-antiga",
            capturado_em=AGORA - timedelta(hours=5),
            temperatura_c=20.0,
        )

    with TestClient(app) as client:
        resposta = client.get("/leituras", headers={"Authorization": f"Bearer {token_produtor}"})

    assert resposta.status_code == 200
    temperaturas = [item["temperatura_c"] for item in resposta.json()]
    assert temperaturas == [20.0, 30.0]  # mais antiga primeiro


async def test_diagnosticos_vem_em_ordem_do_mais_recente(token_produtor: str, monkeypatch):
    monkeypatch.setattr("app.api.routes.historico.gerar_url_assinada_imagem", _url_assinada_falsa)

    async with AsyncSession(engine) as sessao:
        await _criar_registro_com_leitura_e_diagnostico(
            sessao,
            idempotency_key="antiga",
            capturado_em=AGORA - timedelta(hours=5),
            temperatura_c=20.0,
        )
        await _criar_registro_com_leitura_e_diagnostico(
            sessao, idempotency_key="nova", capturado_em=AGORA, temperatura_c=30.0
        )

    with TestClient(app) as client:
        resposta = client.get("/diagnosticos", headers={"Authorization": f"Bearer {token_produtor}"})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo) == 2
    assert corpo[0]["caminho_arquivo"] == "pi-teste/nova.jpg"  # mais recente primeiro
    assert corpo[1]["caminho_arquivo"] == "pi-teste/antiga.jpg"
    assert corpo[0]["url_imagem"] == "https://storage.teste/pi-teste/nova.jpg?signed=1"


async def test_diagnosticos_nao_quebra_se_signed_url_falhar(token_produtor: str, monkeypatch):
    async def _sempre_falha(caminho: str) -> None:
        return None

    monkeypatch.setattr("app.api.routes.historico.gerar_url_assinada_imagem", _sempre_falha)

    async with AsyncSession(engine) as sessao:
        await _criar_registro_com_leitura_e_diagnostico(
            sessao, idempotency_key="sem-url", capturado_em=AGORA, temperatura_c=25.0
        )

    with TestClient(app) as client:
        resposta = client.get("/diagnosticos", headers={"Authorization": f"Bearer {token_produtor}"})

    assert resposta.status_code == 200
    assert resposta.json()[0]["url_imagem"] is None


async def test_filtro_horas_exclui_itens_antigos(token_produtor: str):
    async with AsyncSession(engine) as sessao:
        await _criar_registro_com_leitura_e_diagnostico(
            sessao, idempotency_key="dentro-do-filtro", capturado_em=AGORA, temperatura_c=25.0
        )
        await _criar_registro_com_leitura_e_diagnostico(
            sessao,
            idempotency_key="fora-do-filtro",
            capturado_em=AGORA - timedelta(hours=48),
            temperatura_c=18.0,
        )

    with TestClient(app) as client:
        resposta = client.get(
            "/leituras", params={"horas": 24}, headers={"Authorization": f"Bearer {token_produtor}"}
        )

    assert resposta.status_code == 200
    temperaturas = [item["temperatura_c"] for item in resposta.json()]
    assert temperaturas == [25.0]
