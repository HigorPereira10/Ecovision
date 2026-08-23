"""
cloud/tests/test_diagnostico.py

O que este arquivo verifica, em português simples:

Este é o teste "de ponta a ponta" do endpoint POST /diagnostico.
Simula exatamente o que a Raspberry Pi manda (edge/src/upload/uploader.py):
uma imagem + device_id + timestamp + leituras de sensores, autenticado
por API Key. Sem precisar de Supabase real nem de rede, confere:

1. Sem a API Key certa (ausente ou errada), a API recusa com 401: não
   dá para mandar fotos falsas se não souber a chave.
2. Com a API Key certa, a requisição funciona de ponta a ponta: a
   imagem "sobe" para o storage (aqui, simulado, já que não existe
   Supabase de verdade rodando no teste), e as 3 tabelas relacionadas
   (registros_imagem, leituras_ambientais, diagnosticos) são gravadas
   corretamente no banco.
3. Quando um sensor falhou na Pi (edge/src/main.py grava `None` nesse
   caso, que pode chegar aqui como campo ausente ou como a string
   "None"), a API não trava: grava a leitura como nula no banco, em
   vez de dar erro.
4. Sem um modelo de IA real disponível (situação atual do projeto), o
   diagnóstico gravado é o placeholder "indisponivel", não um erro.
5. Reenvio da MESMA captura (mesmo idempotency_key), uma situação
   real: a API confirma 200 mas o Pi cai antes de tirar o registro da
   fila local, e no próximo ciclo ele reenvia a mesma foto. A API
   detecta e devolve o diagnóstico já existente, sem duplicar a linha
   no banco.
6. Imagem corrompida ou inválida: a API recusa com 400 (erro claro),
   em vez de travar com um 500 cru.
7. Diagnóstico que não é "saudavel" nem o placeholder "indisponivel"
   gera um alerta automático; o placeholder ("indisponivel", situação
   atual sem modelo de IA) não gera, porque avisar o produtor de uma
   classe que ainda não significa nada seria pior que não avisar.
8. timestamp ou leitura de sensor em formato inválido: recusado com
   422 ANTES de subir a imagem para o storage (evita imagem órfã no
   bucket).
9. Imagem maior que o limite (5MB): recusada com 413, sem processar.
10. Duas requisições com a MESMA idempotency_key "correndo" ao mesmo
    tempo (a checagem inicial ainda não vê a outra): a segunda não
    quebra com erro de chave duplicada, devolve o diagnóstico que já
    tinha sido criado pela primeira.
"""

from datetime import datetime
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.routes.diagnostico as diagnostico_module
from app.core import inference as inference_module
from app.db.models import Alerta, Diagnostico, LeituraAmbiental, RegistroImagem
from app.db.session import engine
from app.main import app


async def _salvar_imagem_falso(device_id: str, timestamp: str, bytes_imagem: bytes) -> str:
    """Substitui app.storage.supabase_storage.salvar_imagem nos testes:
    não existe Supabase real disponível, então nada de rede aqui."""
    return f"{device_id}/{timestamp}.jpg"


def _imagem_falsa() -> bytes:
    """Um JPEG minúsculo, mas de verdade: a etapa de pré-processamento
    (app/core/inference.py) precisa conseguir abrir a imagem."""
    buffer = BytesIO()
    Image.new("RGB", (10, 10), color=(80, 140, 60)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _payload_valido(**overrides):
    dados = {
        "device_id": "pi-teste",
        "timestamp": "2026-08-22T10:00:00+00:00",
        "idempotency_key": "captura-de-teste-001",
        "temperatura_c": "24.5",
        "umidade_ar_pct": "60.0",
        "umidade_solo_pct": "45.0",
    }
    dados.update(overrides)
    return dados


async def test_sem_api_key_retorna_401():
    with TestClient(app) as client:
        resposta = client.post(
            "/diagnostico",
            data=_payload_valido(),
            files={"imagem": ("foto.jpg", BytesIO(_imagem_falsa()), "image/jpeg")},
        )
    assert resposta.status_code == 401


async def test_api_key_errada_retorna_401():
    with TestClient(app) as client:
        resposta = client.post(
            "/diagnostico",
            data=_payload_valido(),
            files={"imagem": ("foto.jpg", BytesIO(_imagem_falsa()), "image/jpeg")},
            headers={"Authorization": "chave-errada"},
        )
    assert resposta.status_code == 401


async def test_envio_com_sucesso_grava_as_tres_tabelas(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.diagnostico.salvar_imagem", _salvar_imagem_falso
    )

    with TestClient(app) as client:
        resposta = client.post(
            "/diagnostico",
            data=_payload_valido(),
            files={"imagem": ("foto.jpg", BytesIO(_imagem_falsa()), "image/jpeg")},
            headers={"Authorization": "chave-de-teste-dispositivo"},
        )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["classe_prevista"] == "indisponivel"  # sem modelo real disponivel no teste
    assert corpo["confianca"] == 0.0

    async with AsyncSession(engine) as sessao:
        registros = (await sessao.execute(select(RegistroImagem))).scalars().all()
        leituras = (await sessao.execute(select(LeituraAmbiental))).scalars().all()
        diagnosticos = (await sessao.execute(select(Diagnostico))).scalars().all()

    assert len(registros) == 1
    assert registros[0].device_id == "pi-teste"
    assert registros[0].caminho_arquivo == "pi-teste/2026-08-22T10:00:00+00:00.jpg"
    assert len(leituras) == 1
    assert leituras[0].temperatura_c == 24.5
    assert len(diagnosticos) == 1


async def test_leitura_de_sensor_ausente_e_gravada_como_nula(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.diagnostico.salvar_imagem", _salvar_imagem_falso
    )

    payload = _payload_valido(temperatura_c="None")  # o que uploader.py manda quando o sensor falha
    del payload["umidade_ar_pct"]  # e o caso de o campo nem ser enviado

    with TestClient(app) as client:
        resposta = client.post(
            "/diagnostico",
            data=payload,
            files={"imagem": ("foto.jpg", BytesIO(_imagem_falsa()), "image/jpeg")},
            headers={"Authorization": "chave-de-teste-dispositivo"},
        )

    assert resposta.status_code == 200

    async with AsyncSession(engine) as sessao:
        leitura = (await sessao.execute(select(LeituraAmbiental))).scalar_one()

    assert leitura.temperatura_c is None
    assert leitura.umidade_ar_pct is None
    assert leitura.umidade_solo_pct == 45.0


async def test_reenvio_com_mesma_idempotency_key_nao_duplica(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.diagnostico.salvar_imagem", _salvar_imagem_falso
    )
    payload = _payload_valido()

    with TestClient(app) as client:
        primeira = client.post(
            "/diagnostico",
            data=payload,
            files={"imagem": ("foto.jpg", BytesIO(_imagem_falsa()), "image/jpeg")},
            headers={"Authorization": "chave-de-teste-dispositivo"},
        )
        segunda = client.post(
            "/diagnostico",
            data=payload,  # mesma idempotency_key: simula o reenvio
            files={"imagem": ("foto.jpg", BytesIO(_imagem_falsa()), "image/jpeg")},
            headers={"Authorization": "chave-de-teste-dispositivo"},
        )

    assert primeira.status_code == 200
    assert segunda.status_code == 200
    assert primeira.json()["id"] == segunda.json()["id"]

    async with AsyncSession(engine) as sessao:
        registros = (await sessao.execute(select(RegistroImagem))).scalars().all()

    assert len(registros) == 1, "reenvio com a mesma idempotency_key nao deveria duplicar a linha"


async def test_imagem_corrompida_retorna_400(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.diagnostico.salvar_imagem", _salvar_imagem_falso
    )

    with TestClient(app) as client:
        resposta = client.post(
            "/diagnostico",
            data=_payload_valido(),
            files={"imagem": ("foto.jpg", BytesIO(b"isso nao e um jpeg"), "image/jpeg")},
            headers={"Authorization": "chave-de-teste-dispositivo"},
        )

    assert resposta.status_code == 400

    async with AsyncSession(engine) as sessao:
        registros = (await sessao.execute(select(RegistroImagem))).scalars().all()
    assert registros == [], "nada deveria ter sido gravado quando a imagem e invalida"


async def test_diagnostico_ruim_gera_alerta_mas_indisponivel_nao(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.diagnostico.salvar_imagem", _salvar_imagem_falso
    )

    # sem monkeypatch de rodar_inferencia: modelo indisponivel no teste,
    # resultado "indisponivel" -> nao deve gerar alerta
    with TestClient(app) as client:
        client.post(
            "/diagnostico",
            data=_payload_valido(idempotency_key="sem-alerta"),
            files={"imagem": ("foto.jpg", BytesIO(_imagem_falsa()), "image/jpeg")},
            headers={"Authorization": "chave-de-teste-dispositivo"},
        )

    async with AsyncSession(engine) as sessao:
        alertas = (await sessao.execute(select(Alerta))).scalars().all()
    assert alertas == [], "diagnostico placeholder 'indisponivel' nao deveria gerar alerta"

    # agora simula um modelo de verdade detectando uma doença
    monkeypatch.setattr(
        inference_module,
        "rodar_inferencia",
        lambda interpretador, imagem: {
            "classe": "requeima",
            "confianca": 0.91,
            "recomendacao": "Aplicar fungicida a base de cobre.",
            "severidade": "alta",
        },
    )

    with TestClient(app) as client:
        resposta = client.post(
            "/diagnostico",
            data=_payload_valido(idempotency_key="com-alerta"),
            files={"imagem": ("foto.jpg", BytesIO(_imagem_falsa()), "image/jpeg")},
            headers={"Authorization": "chave-de-teste-dispositivo"},
        )

    assert resposta.status_code == 200
    async with AsyncSession(engine) as sessao:
        alertas = (await sessao.execute(select(Alerta))).scalars().all()
    assert len(alertas) == 1
    assert "requeima" in alertas[0].titulo
    assert alertas[0].severidade == "alta"


async def test_leitura_fora_da_faixa_gera_alerta_ambiental(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.diagnostico.salvar_imagem", _salvar_imagem_falso
    )

    payload = _payload_valido(
        idempotency_key="risco-ambiental",
        temperatura_c="40.0",  # acima do limiar (ver docs/decisions/0005-limiares-ambientais.md)
        umidade_solo_pct="10.0",  # solo seco
    )

    with TestClient(app) as client:
        resposta = client.post(
            "/diagnostico",
            data=payload,
            files={"imagem": ("foto.jpg", BytesIO(_imagem_falsa()), "image/jpeg")},
            headers={"Authorization": "chave-de-teste-dispositivo"},
        )

    assert resposta.status_code == 200
    async with AsyncSession(engine) as sessao:
        alertas = (await sessao.execute(select(Alerta))).scalars().all()

    alertas_por_titulo = {alerta.titulo: alerta for alerta in alertas}
    assert "Temperatura fora da faixa segura" in alertas_por_titulo
    assert "Solo seco" in alertas_por_titulo
    assert alertas_por_titulo["Temperatura fora da faixa segura"].severidade == "alta"
    assert alertas_por_titulo["Solo seco"].severidade == "alta"
    assert all(alerta.leitura_id is not None for alerta in alertas)


async def test_doenca_e_risco_ambiental_juntos_correlaciona_no_texto(monkeypatch):
    """Quando doença e risco ambiental ocorrem no mesmo ciclo, a
    descricao do alerta de doenca deve citar isso (correlacao em texto,
    ver ADR 0006: nao e fusao de modelo, so uma mensagem mais util)."""
    monkeypatch.setattr(
        "app.api.routes.diagnostico.salvar_imagem", _salvar_imagem_falso
    )
    monkeypatch.setattr(
        inference_module,
        "rodar_inferencia",
        lambda interpretador, imagem: {
            "classe": "mofo_de_folha",
            "confianca": 0.8,
            "recomendacao": "Melhore a ventilacao da estufa.",
            "severidade": "media",
        },
    )

    payload = _payload_valido(
        idempotency_key="doenca-com-ambiente",
        umidade_ar_pct="95.0",  # acima do limiar -> alerta ambiental tambem
    )

    with TestClient(app) as client:
        resposta = client.post(
            "/diagnostico",
            data=payload,
            files={"imagem": ("foto.jpg", BytesIO(_imagem_falsa()), "image/jpeg")},
            headers={"Authorization": "chave-de-teste-dispositivo"},
        )

    assert resposta.status_code == 200
    async with AsyncSession(engine) as sessao:
        alertas = (await sessao.execute(select(Alerta))).scalars().all()

    alerta_doenca = next(a for a in alertas if a.diagnostico_id is not None)
    assert "Umidade do ar muito alta" in alerta_doenca.descricao
    assert len(alertas) == 2  # 1 de doenca + 1 ambiental


async def test_timestamp_invalido_retorna_422_e_nao_sobe_imagem(monkeypatch):
    chamadas_storage = []

    async def _salvar_imagem_espiao(device_id, timestamp, bytes_imagem):
        chamadas_storage.append(device_id)
        return "nao-deveria-chegar-aqui.jpg"

    monkeypatch.setattr("app.api.routes.diagnostico.salvar_imagem", _salvar_imagem_espiao)

    payload = _payload_valido(timestamp="isso-nao-e-uma-data")

    with TestClient(app) as client:
        resposta = client.post(
            "/diagnostico",
            data=payload,
            files={"imagem": ("foto.jpg", BytesIO(_imagem_falsa()), "image/jpeg")},
            headers={"Authorization": "chave-de-teste-dispositivo"},
        )

    assert resposta.status_code == 422
    assert chamadas_storage == [], "nao deveria ter tentado subir a imagem com timestamp invalido"

    async with AsyncSession(engine) as sessao:
        registros = (await sessao.execute(select(RegistroImagem))).scalars().all()
    assert registros == []


async def test_imagem_maior_que_limite_retorna_413(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.diagnostico.salvar_imagem", _salvar_imagem_falso
    )
    monkeypatch.setattr("app.api.routes.diagnostico._TAMANHO_MAXIMO_IMAGEM_BYTES", 10)

    with TestClient(app) as client:
        resposta = client.post(
            "/diagnostico",
            data=_payload_valido(),
            files={"imagem": ("foto.jpg", BytesIO(_imagem_falsa()), "image/jpeg")},
            headers={"Authorization": "chave-de-teste-dispositivo"},
        )

    assert resposta.status_code == 413


async def test_corrida_de_idempotency_key_no_commit_nao_quebra(monkeypatch, tmp_path):
    """Simula a corrida: forca a checagem inicial a nao encontrar nada
    (como se as duas requisicoes tivessem chegado juntas), mas ja existe
    de verdade uma linha com a mesma idempotency_key no banco. O commit
    deve bater na constraint UNIQUE e o endpoint deve se recuperar,
    devolvendo o diagnostico ja existente em vez de um 500."""
    monkeypatch.setattr(
        "app.api.routes.diagnostico.salvar_imagem", _salvar_imagem_falso
    )

    chave_disputada = "corrida-idempotencia"

    # cria a linha "vencedora" diretamente, como se outra requisicao
    # tivesse chegado primeiro e ja commitado
    async with AsyncSession(engine, expire_on_commit=False) as sessao_setup:
        registro = RegistroImagem(
            device_id="pi-teste",
            idempotency_key=chave_disputada,
            caminho_arquivo="ja-existente.jpg",
            capturado_em=datetime.fromisoformat("2026-08-22T10:00:00+00:00"),
        )
        sessao_setup.add(registro)
        await sessao_setup.flush()
        diagnostico_vencedor = Diagnostico(
            registro_imagem_id=registro.id,
            classe_prevista="indisponivel",
            confianca=0.0,
            recomendacao=None,
        )
        sessao_setup.add(diagnostico_vencedor)
        await sessao_setup.commit()
        id_vencedor = diagnostico_vencedor.id

    # forca a checagem INICIAL da requisicao "perdedora" a nao ver a
    # linha que acabou de ser commitada, simulando a janela de corrida.
    # Mas a segunda chamada (dentro do except IntegrityError, buscando
    # o vencedor de verdade) precisa continuar funcionando normalmente.
    busca_real = diagnostico_module._buscar_diagnostico_por_idempotency_key
    contador = {"chamadas": 0}

    async def _busca_com_falha_na_primeira_chamada(sessao, chave):
        contador["chamadas"] += 1
        if contador["chamadas"] == 1:
            return None
        return await busca_real(sessao, chave)

    monkeypatch.setattr(
        "app.api.routes.diagnostico._buscar_diagnostico_por_idempotency_key",
        _busca_com_falha_na_primeira_chamada,
    )

    payload = _payload_valido(idempotency_key=chave_disputada)

    with TestClient(app) as client:
        resposta = client.post(
            "/diagnostico",
            data=payload,
            files={"imagem": ("foto.jpg", BytesIO(_imagem_falsa()), "image/jpeg")},
            headers={"Authorization": "chave-de-teste-dispositivo"},
        )

    assert resposta.status_code == 200
    assert resposta.json()["id"] == id_vencedor

    async with AsyncSession(engine) as sessao:
        registros = (
            await sessao.execute(
                select(RegistroImagem).where(RegistroImagem.idempotency_key == chave_disputada)
            )
        ).scalars().all()
    assert len(registros) == 1, "nao deveria ter criado uma segunda linha para a mesma chave"
