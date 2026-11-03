"""
cloud/tests/test_escopo.py

O que este arquivo verifica, em português simples:

Depois que POST /auth/register abriu o cadastro, qualquer pessoa pode
criar uma conta. Estes testes provam que criar uma conta NÃO dá acesso
aos dados de outro produtor. Montam duas estufas de donos diferentes e
conferem que cada um só enxerga a sua:

1. /leituras só devolve as leituras dos dispositivos do produtor.
2. /diagnosticos idem.
3. /alertas idem, nos dois caminhos possíveis (alerta ligado a um
   diagnóstico e alerta ligado a uma leitura ambiental).
4. /dispositivos só lista as estufas do próprio produtor.
5. PATCH /alertas/{id}/lido em alerta alheio responde 404 e NÃO marca
   o alerta como lido.
6. Quem tem papel 'administrador' continua vendo tudo.

O filtro em si vive em app/api/escopo.py.
"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import criar_access_token, gerar_hash_senha
from app.db.models import (
    Alerta,
    Diagnostico,
    Dispositivo,
    LeituraAmbiental,
    RegistroImagem,
    Usuario,
)
from app.db.session import engine
from app.main import app

AGORA = datetime.now(timezone.utc)


async def _montar_estufa(sessao: AsyncSession, *, email: str, device_id: str) -> dict:
    """Cria um produtor dono de um dispositivo, com uma captura que
    gera uma leitura, um diagnóstico e um alerta de cada tipo."""
    usuario = Usuario(
        email=email,
        senha_hash=gerar_hash_senha("x"),
        papel="produtor",
        email_verificado=True,
    )
    sessao.add(usuario)
    await sessao.flush()

    sessao.add(Dispositivo(device_id=device_id, usuario_id=usuario.id, nome=f"Estufa {email}"))

    registro = RegistroImagem(
        device_id=device_id,
        idempotency_key=f"captura-{device_id}",
        caminho_arquivo=f"{device_id}/foto.jpg",
        capturado_em=AGORA,
        criado_em=AGORA,
    )
    sessao.add(registro)
    await sessao.flush()

    leitura = LeituraAmbiental(
        device_id=device_id,
        registro_imagem_id=registro.id,
        temperatura_c=30.0,
        criado_em=AGORA,
    )
    diagnostico = Diagnostico(
        registro_imagem_id=registro.id,
        classe_prevista="pinta_preta",
        confianca=0.9,
        recomendacao=None,
        criado_em=AGORA,
    )
    sessao.add_all([leitura, diagnostico])
    await sessao.flush()

    alerta_doenca = Alerta(
        diagnostico_id=diagnostico.id,
        titulo=f"Doenca em {device_id}",
        descricao="x",
        severidade="alta",
    )
    alerta_ambiental = Alerta(
        leitura_id=leitura.id,
        titulo=f"Calor em {device_id}",
        descricao="x",
        severidade="media",
    )
    sessao.add_all([alerta_doenca, alerta_ambiental])
    await sessao.flush()

    # Os ids sao lidos ANTES do commit de proposito: depois dele os
    # atributos ficam expirados, e ler qualquer um deles dispararia um
    # carregamento preguicoso fora do contexto async (MissingGreenlet).
    dados = {
        "usuario_id": usuario.id,
        "token": criar_access_token(usuario.id, "produtor"),
        "alerta_doenca_id": alerta_doenca.id,
        "alerta_ambiental_id": alerta_ambiental.id,
    }

    await sessao.commit()
    return dados


async def _duas_estufas() -> tuple[dict, dict]:
    async with AsyncSession(engine) as sessao:
        ana = await _montar_estufa(sessao, email="ana@teste.com", device_id="pi-da-ana")
        bento = await _montar_estufa(sessao, email="bento@teste.com", device_id="pi-do-bento")
    return ana, bento


def _cabecalho(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_leituras_so_mostram_o_dispositivo_do_proprio_produtor():
    ana, bento = await _duas_estufas()

    with TestClient(app) as client:
        da_ana = client.get("/leituras", headers=_cabecalho(ana["token"])).json()
        do_bento = client.get("/leituras", headers=_cabecalho(bento["token"])).json()

    assert [item["device_id"] for item in da_ana] == ["pi-da-ana"]
    assert [item["device_id"] for item in do_bento] == ["pi-do-bento"]


async def test_diagnosticos_so_mostram_o_dispositivo_do_proprio_produtor():
    ana, bento = await _duas_estufas()

    with TestClient(app) as client:
        da_ana = client.get("/diagnosticos", headers=_cabecalho(ana["token"])).json()

    assert len(da_ana) == 1
    assert da_ana[0]["caminho_arquivo"].startswith("pi-da-ana/")


async def test_alertas_so_mostram_os_do_proprio_produtor():
    ana, bento = await _duas_estufas()

    with TestClient(app) as client:
        da_ana = client.get("/alertas", headers=_cabecalho(ana["token"])).json()

    titulos = {item["titulo"] for item in da_ana if not item["sintetico"]}
    # Os dois caminhos de ligacao (via diagnostico e via leitura) devem
    # aparecer para a dona, e nenhum do vizinho.
    assert titulos == {"Doenca em pi-da-ana", "Calor em pi-da-ana"}
    assert not any("bento" in titulo for titulo in titulos)


async def test_dispositivos_so_mostram_os_do_proprio_produtor():
    ana, bento = await _duas_estufas()

    with TestClient(app) as client:
        da_ana = client.get("/dispositivos", headers=_cabecalho(ana["token"])).json()

    assert [item["device_id"] for item in da_ana] == ["pi-da-ana"]


async def test_marcar_alerta_de_outro_produtor_responde_404_e_nao_altera_nada():
    ana, bento = await _duas_estufas()
    alerta_alheio = ana["alerta_doenca_id"]

    with TestClient(app) as client:
        resposta = client.patch(
            f"/alertas/{alerta_alheio}/lido", headers=_cabecalho(bento["token"])
        )

    # 404 (e nao 403) de proposito: 403 confirmaria que o id existe.
    assert resposta.status_code == 404

    async with AsyncSession(engine) as sessao:
        lido = await sessao.scalar(select(Alerta.lido).where(Alerta.id == alerta_alheio))
    assert lido is False, "o alerta do outro produtor nao pode ter sido marcado como lido"


async def test_dono_continua_conseguindo_marcar_o_proprio_alerta_como_lido():
    ana, _ = await _duas_estufas()

    with TestClient(app) as client:
        resposta = client.patch(
            f"/alertas/{ana['alerta_ambiental_id']}/lido", headers=_cabecalho(ana["token"])
        )

    assert resposta.status_code == 200
    assert resposta.json()["lido"] is True


async def test_administrador_enxerga_os_dados_de_todos_os_produtores():
    ana, bento = await _duas_estufas()

    async with AsyncSession(engine) as sessao:
        admin = Usuario(
            email="admin@teste.com",
            senha_hash=gerar_hash_senha("x"),
            papel="administrador",
            email_verificado=True,
        )
        sessao.add(admin)
        await sessao.commit()
        await sessao.refresh(admin)
        token_admin = criar_access_token(admin.id, admin.papel)

    with TestClient(app) as client:
        leituras = client.get("/leituras", headers=_cabecalho(token_admin)).json()
        dispositivos = client.get("/dispositivos", headers=_cabecalho(token_admin)).json()

    assert {item["device_id"] for item in leituras} == {"pi-da-ana", "pi-do-bento"}
    assert {item["device_id"] for item in dispositivos} == {"pi-da-ana", "pi-do-bento"}
