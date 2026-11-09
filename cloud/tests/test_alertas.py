"""
Testes de GET /alertas e PATCH /alertas/{id}/lido:

1. sem login: 401;
2. lista os alertas gravados, do mais recente ao mais antigo;
3. dispositivo inativo gera um item sintético no topo, sem gravar nada;
4. dispositivo sem nenhuma captura também gera o item sintético;
5. PATCH marca alerta gravado como lido; id inexistente (inclusive do
   item sintético) responde 404.
"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alerta, Diagnostico, LeituraAmbiental, RegistroImagem
from app.db.session import engine
from app.main import app

AGORA = datetime.now(timezone.utc)


async def _criar_alerta(sessao: AsyncSession, *, titulo: str, criado_em: datetime) -> int:
    registro = RegistroImagem(
        device_id="pi-teste",
        idempotency_key=f"chave-{titulo}",
        caminho_arquivo="pi-teste/foto.jpg",
        capturado_em=criado_em,
    )
    sessao.add(registro)
    await sessao.flush()

    diagnostico = Diagnostico(
        registro_imagem_id=registro.id, classe_prevista="requeima", confianca=0.9, recomendacao=None
    )
    sessao.add(diagnostico)
    await sessao.flush()

    alerta = Alerta(
        diagnostico_id=diagnostico.id,
        titulo=titulo,
        descricao="descricao de teste",
        severidade="alta",
        criado_em=criado_em,
    )
    sessao.add(alerta)
    await sessao.commit()
    await sessao.refresh(alerta)
    return alerta.id


async def _registrar_captura_recente(sessao: AsyncSession, capturado_em: datetime) -> None:
    sessao.add(RegistroImagem(
        device_id="pi-teste",
        idempotency_key="captura-recente",
        caminho_arquivo="pi-teste/recente.jpg",
        capturado_em=capturado_em,
        criado_em=capturado_em,
    ))
    await sessao.commit()


async def test_alertas_sem_token_retorna_401():
    with TestClient(app) as client:
        resposta = client.get("/alertas")
    assert resposta.status_code == 401


async def test_patch_lido_sem_token_retorna_401():
    with TestClient(app) as client:
        resposta = client.patch("/alertas/1/lido")
    assert resposta.status_code == 401


async def test_lista_alertas_reais_do_mais_recente(token_produtor: str):
    async with AsyncSession(engine) as sessao:
        await _criar_alerta(sessao, titulo="Alerta antigo", criado_em=AGORA - timedelta(hours=2))
        await _criar_alerta(sessao, titulo="Alerta novo", criado_em=AGORA)
        # captura recente: nao deve gerar o item sintetico de inatividade
        await _registrar_captura_recente(sessao, AGORA)

    with TestClient(app) as client:
        resposta = client.get("/alertas", headers={"Authorization": f"Bearer {token_produtor}"})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo) == 2
    assert corpo[0]["titulo"] == "Alerta novo"
    assert corpo[1]["titulo"] == "Alerta antigo"
    assert all(item["sintetico"] is False for item in corpo)


async def test_dispositivo_inativo_aparece_como_item_sintetico(token_produtor: str):
    async with AsyncSession(engine) as sessao:
        await _registrar_captura_recente(sessao, AGORA - timedelta(hours=10))  # bem atrasado

    with TestClient(app) as client:
        resposta = client.get("/alertas", headers={"Authorization": f"Bearer {token_produtor}"})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo) == 1
    assert corpo[0]["sintetico"] is True
    assert corpo[0]["id"] is None
    assert corpo[0]["severidade"] == "alta"


async def test_sem_nenhuma_captura_tambem_gera_sintetico(token_produtor: str):
    with TestClient(app) as client:
        resposta = client.get("/alertas", headers={"Authorization": f"Bearer {token_produtor}"})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo) == 1
    assert corpo[0]["sintetico"] is True


async def test_marcar_alerta_como_lido(token_produtor: str):
    async with AsyncSession(engine) as sessao:
        alerta_id = await _criar_alerta(sessao, titulo="Alerta X", criado_em=AGORA)

    with TestClient(app) as client:
        resposta = client.patch(
            f"/alertas/{alerta_id}/lido", headers={"Authorization": f"Bearer {token_produtor}"}
        )

    assert resposta.status_code == 200
    assert resposta.json()["lido"] is True


async def test_marcar_alerta_inexistente_retorna_404(token_produtor: str):
    with TestClient(app) as client:
        resposta = client.patch(
            "/alertas/99999/lido", headers={"Authorization": f"Bearer {token_produtor}"}
        )
    assert resposta.status_code == 404
