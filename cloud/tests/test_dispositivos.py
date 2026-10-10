"""
cloud/tests/test_dispositivos.py

O que este arquivo verifica, em português simples:

GET /dispositivos, a lista de dispositivos IoT da tela de Perfil:
1. Sem login, recusa com 401.
2. Sem nenhum dispositivo cadastrado, devolve lista vazia (não quebra).
3. Um dispositivo que nunca mandou captura aparece como "inativo".
4. Um dispositivo com captura recente aparece como "ativo".
5. Um dispositivo com captura muito atrasada aparece como "inativo"
   (mesmos limiares do item sintético de alerta, ver ADR 0008).
"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import criar_access_token
from app.db.models import RegistroImagem, Usuario
from app.db.session import engine
from app.main import app

AGORA = datetime.now(timezone.utc)


async def _registrar_captura(sessao: AsyncSession, *, device_id: str, capturado_em: datetime) -> None:
    sessao.add(RegistroImagem(
        device_id=device_id,
        idempotency_key=f"captura-{device_id}-{capturado_em.isoformat()}",
        caminho_arquivo=f"{device_id}/foto.jpg",
        capturado_em=capturado_em,
        criado_em=capturado_em,
    ))
    await sessao.commit()


async def test_dispositivos_sem_token_retorna_401():
    with TestClient(app) as client:
        resposta = client.get("/dispositivos")
    assert resposta.status_code == 401


async def test_sem_dispositivo_cadastrado_devolve_lista_vazia(usuario_produtor: Usuario):
    # Usa usuario_produtor em vez de token_produtor de proposito: a
    # fixture token_produtor ja vincula um dispositivo ao produtor, e
    # aqui o cenario e justamente o de quem ainda nao tem nenhum.
    token = criar_access_token(usuario_produtor.id, usuario_produtor.papel)

    with TestClient(app) as client:
        resposta = client.get("/dispositivos", headers={"Authorization": f"Bearer {token}"})

    assert resposta.status_code == 200
    assert resposta.json() == []


async def test_dispositivo_sem_captura_aparece_inativo(token_produtor: str):
    # O dispositivo "pi-teste" ja vem vinculado ao produtor pela
    # fixture dispositivo_do_produtor (ver conftest.py).
    with TestClient(app) as client:
        resposta = client.get("/dispositivos", headers={"Authorization": f"Bearer {token_produtor}"})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo) == 1
    assert corpo[0]["device_id"] == "pi-teste"
    assert corpo[0]["nome"] == "Estufa 1"
    assert corpo[0]["status"] == "inativo"


async def test_dispositivo_com_captura_recente_aparece_ativo(token_produtor: str):
    async with AsyncSession(engine) as sessao:
        await _registrar_captura(sessao, device_id="pi-teste", capturado_em=AGORA)

    with TestClient(app) as client:
        resposta = client.get("/dispositivos", headers={"Authorization": f"Bearer {token_produtor}"})

    assert resposta.status_code == 200
    assert resposta.json()[0]["status"] == "ativo"


async def test_dispositivo_com_captura_atrasada_aparece_inativo(token_produtor: str):
    async with AsyncSession(engine) as sessao:
        await _registrar_captura(sessao, device_id="pi-teste", capturado_em=AGORA - timedelta(hours=10))

    with TestClient(app) as client:
        resposta = client.get("/dispositivos", headers={"Authorization": f"Bearer {token_produtor}"})

    assert resposta.status_code == 200
    assert resposta.json()[0]["status"] == "inativo"
