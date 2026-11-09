"""
Testes de GET /leituras e GET /diagnosticos:

1. sem login: 401;
2. ordem correta (leituras em ordem cronológica, diagnósticos do mais
   recente ao mais antigo);
3. o filtro ?horas=N exclui itens mais antigos;
4. os diagnósticos trazem a URL assinada, sem quebrar a lista quando a
   geração falha;
5. cada diagnóstico informa o dispositivo de origem.
"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Diagnostico, Dispositivo, LeituraAmbiental, RegistroImagem
from app.db.session import engine
from app.main import app

AGORA = datetime.now(timezone.utc)


async def _urls_assinadas_falsas(caminhos: list[str]) -> dict[str, str]:
    """Substitui a geração de URLs assinadas (feita em lote) por um dublê
    que devolve o mapa caminho -> URL."""
    return {caminho: f"https://storage.teste/{caminho}?signed=1" for caminho in caminhos}


async def _criar_registro_com_leitura_e_diagnostico(
    sessao: AsyncSession,
    *,
    idempotency_key: str,
    capturado_em: datetime,
    temperatura_c: float,
    device_id: str = "pi-teste",
) -> None:
    registro = RegistroImagem(
        device_id=device_id,
        idempotency_key=idempotency_key,
        caminho_arquivo=f"{device_id}/{idempotency_key}.jpg",
        capturado_em=capturado_em,
    )
    sessao.add(registro)
    await sessao.flush()

    # criado_em explícito, para a ordem não depender do relógio real.
    sessao.add(LeituraAmbiental(
        device_id=device_id,
        registro_imagem_id=registro.id,
        temperatura_c=temperatura_c,
        criado_em=capturado_em,
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
    monkeypatch.setattr(
        "app.api.routes.historico.gerar_urls_assinadas_imagens", _urls_assinadas_falsas
    )

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
    async def _sempre_falha(caminhos: list[str]) -> dict[str, None]:
        return {caminho: None for caminho in caminhos}

    monkeypatch.setattr(
        "app.api.routes.historico.gerar_urls_assinadas_imagens", _sempre_falha
    )

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


async def test_diagnosticos_informam_o_dispositivo_de_origem(
    token_produtor: str, usuario_produtor, monkeypatch
):
    """Dois dispositivos do mesmo usuário aparecem na lista, cada um com
    seu device_id."""
    monkeypatch.setattr(
        "app.api.routes.historico.gerar_urls_assinadas_imagens", _urls_assinadas_falsas
    )

    async with AsyncSession(engine) as sessao:
        sessao.add(
            Dispositivo(device_id="pi-estufa-02", usuario_id=usuario_produtor.id, nome="Estufa 2")
        )
        await sessao.commit()

        await _criar_registro_com_leitura_e_diagnostico(
            sessao, idempotency_key="da-um", capturado_em=AGORA, temperatura_c=25.0
        )
        await _criar_registro_com_leitura_e_diagnostico(
            sessao,
            idempotency_key="da-dois",
            capturado_em=AGORA - timedelta(hours=1),
            temperatura_c=26.0,
            device_id="pi-estufa-02",
        )

    with TestClient(app) as client:
        resposta = client.get("/diagnosticos", headers={"Authorization": f"Bearer {token_produtor}"})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo) == 2
    assert [item["device_id"] for item in corpo] == ["pi-teste", "pi-estufa-02"]


async def test_limite_controla_quantos_diagnosticos_voltam(token_produtor: str, monkeypatch):
    """`limite` restringe a consulta e o lote de URLs assinadas."""
    assinados: list[str] = []

    async def _contando(caminhos: list[str]) -> dict[str, str]:
        assinados.extend(caminhos)
        return {caminho: f"https://storage.teste/{caminho}?signed=1" for caminho in caminhos}

    monkeypatch.setattr(
        "app.api.routes.historico.gerar_urls_assinadas_imagens", _contando
    )

    async with AsyncSession(engine) as sessao:
        for n in range(5):
            await _criar_registro_com_leitura_e_diagnostico(
                sessao,
                idempotency_key=f"item-{n}",
                capturado_em=AGORA - timedelta(hours=n),
                temperatura_c=25.0,
            )

    with TestClient(app) as client:
        resposta = client.get(
            "/diagnosticos",
            params={"limite": 2},
            headers={"Authorization": f"Bearer {token_produtor}"},
        )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo) == 2
    # Os DOIS MAIS RECENTES, não dois quaisquer.
    assert [item["caminho_arquivo"] for item in corpo] == [
        "pi-teste/item-0.jpg",
        "pi-teste/item-1.jpg",
    ]
    # E só esses dois foram mandados para assinar, que é o ponto.
    assert len(assinados) == 2


async def test_limite_acima_do_maximo_e_recusado(token_produtor: str):
    """Sem o teto, `?limite=999999` desfaria a proteção que o próprio
    parâmetro existe para dar."""
    with TestClient(app) as client:
        resposta = client.get(
            "/diagnosticos",
            params={"limite": 999_999},
            headers={"Authorization": f"Bearer {token_produtor}"},
        )

    assert resposta.status_code == 422
