"""
Testes de ponta a ponta de POST /diagnostico, simulando o envio do
dispositivo (edge/src/upload/uploader.py), com o Storage simulado:

1. credencial ausente ou errada: 401;
2. envio válido: imagem enviada ao Storage e registro, leitura e
   diagnóstico gravados;
3. sensor com falha (campo ausente ou "None"): leitura gravada como nula;
4. modelo ausente: 200 com o resultado "indisponivel";
5. reenvio com a mesma idempotency_key: devolve o diagnóstico existente,
   sem duplicar;
6. imagem inválida: 400;
7. alertas de diagnóstico, exceto para "saudavel" e "indisponivel";
8. timestamp ou leitura inválidos: 422 antes do upload;
9. imagem acima de 5 MB: 413;
10. requisições simultâneas com a mesma chave: a segunda devolve o
    diagnóstico da primeira;
11. imagem inadequada e ressalva de plausibilidade ambiental.
"""

from datetime import datetime, timedelta
from functools import lru_cache
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


@lru_cache(maxsize=1)
def _imagem_falsa() -> bytes:
    """JPEG com textura e cobertura verde, grande o suficiente para render
    janelas aproveitáveis; uma imagem lisa seria reprovada pela
    verificação de qualidade."""
    import numpy as np

    # Xadrez verde de 16x16 com ruído leve. Em 2688x1512 (16:9), a
    # decodificação em metade da resolução rende 10 janelas, acima do
    # mínimo de 6.
    largura, altura = 2688, 1512
    base = np.indices((altura, largura)).sum(axis=0) // 8 % 2
    rng = np.random.default_rng(42)
    ruido = rng.integers(-15, 16, (altura, largura))
    canais = []
    for claro, escuro in ((70, 30), (190, 90), (80, 40)):  # R, G, B: verde domina
        canal = np.where(base == 0, escuro, claro).astype(np.int16) + ruido
        canais.append(np.clip(canal, 0, 255).astype(np.uint8))
    rgb = np.stack(canais, axis=-1)

    buffer = BytesIO()
    Image.fromarray(rgb).save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()


def _imagem_escura() -> bytes:
    """Foto que a guarda de qualidade REPROVA, para os testes do caminho
    de imagem inadequada."""
    buffer = BytesIO()
    Image.new("RGB", (64, 64), color=(8, 8, 10)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _forcar_diagnostico(monkeypatch, resultado):
    """Faz a rota devolver `resultado` nos dois caminhos de inferência
    (quadro inteiro e janelas), para testar alertas e ressalvas
    independentemente do caminho."""
    def _quadro(_interpretador, _imagem):
        return dict(resultado)

    def _janela(_interpretador, _bytes):
        return dict(resultado)

    monkeypatch.setattr(inference_module, "rodar_inferencia", _quadro)
    monkeypatch.setattr(diagnostico_module.inference, "rodar_inferencia", _quadro)
    monkeypatch.setattr(
        diagnostico_module.janelas, "diagnosticar_por_janelas", _janela
    )



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
    # Com o modelo real carregado, a asserção é sobre o contrato, não sobre
    # uma classe específica.
    assert corpo["classe_prevista"] in inference_module._CLASSES_DO_MODELO, (
        f"classe {corpo['classe_prevista']!r} fora de _CLASSES_DO_MODELO. "
        "Se virou 'indisponivel', o modelo nao carregou."
    )
    assert 0.0 < corpo["confianca"] <= 1.0

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
    _forcar_diagnostico(monkeypatch, {
        "classe": "requeima",
        "confianca": 0.91,
        "recomendacao": "Aplicar fungicida a base de cobre.",
        "severidade": "alta",
    })

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


async def test_titulo_do_alerta_nao_vaza_nome_tecnico_da_classe(monkeypatch):
    """O título do alerta é texto gravado e deve usar o nome legível da
    classe, sem sublinhados."""
    monkeypatch.setattr(
        "app.api.routes.diagnostico.salvar_imagem", _salvar_imagem_falso
    )
    _forcar_diagnostico(monkeypatch, {
        "classe": "estresse_foliar",
        "confianca": 0.77,
        "recomendacao": "Confira a planta de perto.",
        "severidade": "media",
    })

    with TestClient(app) as client:
        resposta = client.post(
            "/diagnostico",
            data=_payload_valido(idempotency_key="titulo-sem-nome-tecnico"),
            files={"imagem": ("foto.jpg", BytesIO(_imagem_falsa()), "image/jpeg")},
            headers={"Authorization": "chave-de-teste-dispositivo"},
        )

    assert resposta.status_code == 200
    async with AsyncSession(engine) as sessao:
        alertas = (await sessao.execute(select(Alerta))).scalars().all()

    titulo = next(a.titulo for a in alertas if "estresse" in a.titulo.lower())
    assert "_" not in titulo, f"nome tecnico vazou no titulo do alerta: {titulo!r}"
    assert "estresse foliar" in titulo.lower()


async def test_leitura_fora_da_faixa_gera_alerta_ambiental(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.diagnostico.salvar_imagem", _salvar_imagem_falso
    )

    payload = _payload_valido(
        idempotency_key="risco-ambiental",
            temperatura_c="40.0",  # acima do limiar de temperatura
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
    """Quando doença e risco ambiental ocorrem no mesmo ciclo, a descrição
    do alerta de doença menciona as condições ambientais."""
    monkeypatch.setattr(
        "app.api.routes.diagnostico.salvar_imagem", _salvar_imagem_falso
    )
    _forcar_diagnostico(monkeypatch, {
        "classe": "mofo_de_folha",
        "confianca": 0.8,
        "recomendacao": "Melhore a ventilacao da estufa.",
        "severidade": "media",
    })

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
    """Simula a corrida: a verificação inicial não encontra a linha, que já
    existe no banco. O commit viola a restrição UNIQUE e a rota devolve o
    diagnóstico existente, sem erro 500."""
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

    # A verificação inicial da requisição "perdedora" não vê a linha; a
    # busca dentro do tratamento de IntegrityError funciona normalmente.
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


async def test_foto_reprovada_guarda_a_imagem_mas_nao_afirma_diagnostico(monkeypatch):
    """Captura com foto inadequada é gravada (imagem e leituras), mas sem
    diagnóstico afirmado."""
    monkeypatch.setattr("app.api.routes.diagnostico.salvar_imagem", _salvar_imagem_falso)

    with TestClient(app) as client:
        resposta = client.post(
            "/diagnostico",
            headers={"Authorization": "chave-de-teste-dispositivo"},
            data=_payload_valido(idempotency_key="foto-escura"),
            files={"imagem": ("foto.jpg", BytesIO(_imagem_escura()), "image/jpeg")},
        )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["classe_prevista"] == "imagem_inadequada"
    assert corpo["confianca"] == 0.0
    assert "escura" in corpo["recomendacao"].lower()

    async with AsyncSession(engine) as sessao:
        registro = await sessao.scalar(
            select(RegistroImagem).where(RegistroImagem.idempotency_key == "foto-escura")
        )
        assert registro is not None, "a foto tem que ser guardada mesmo reprovada"
        assert registro.caminho_arquivo

        alertas = (await sessao.execute(
            select(Alerta).join(Diagnostico, Alerta.diagnostico_id == Diagnostico.id)
            .where(Diagnostico.registro_imagem_id == registro.id)
        )).scalars().all()

        assert len(alertas) == 1
        assert "analisar a foto" in alertas[0].titulo.lower()
        assert alertas[0].severidade == "media", "pede conferir a camera, nao agir no cultivo"
        # Nenhum alerta de doença (prefixo "Sinal de <classe> na planta").
        assert "sinal de" not in alertas[0].titulo.lower()


# --- 11. ressalva de plausibilidade ambiental ---------------------------
# A ressalva só aparece com medição suficiente e quando o ambiente não
# sustentou infecção, e é somada à recomendação, sem substituí-la.


def _inferencia_fungica(_interpretador, _imagem):
    return {
        "classe": "pinta_preta",
        "confianca": 0.9,
        "recomendacao": "Aplique fungicida registrado.",
        "severidade": "media",
    }


async def _semear_historico(device_id: str, dias: int, umidade_pct: float) -> None:
    """Cria `dias` de leituras de hora em hora terminando pouco antes do
    timestamp usado por _payload_valido()."""
    fim = datetime.fromisoformat("2026-08-22T10:00:00+00:00") - timedelta(hours=1)
    async with AsyncSession(engine) as sessao:
        for i in range(dias * 24):
            momento = fim - timedelta(hours=i)
            registro = RegistroImagem(
                device_id=device_id,
                idempotency_key=f"historico-{i}",
                caminho_arquivo=f"{device_id}/historico-{i}.jpg",
                capturado_em=momento,
            )
            sessao.add(registro)
            await sessao.flush()
            sessao.add(LeituraAmbiental(
                device_id=device_id,
                registro_imagem_id=registro.id,
                temperatura_c=27.0,
                umidade_ar_pct=umidade_pct,
                umidade_solo_pct=45.0,
            ))
        await sessao.commit()


async def _recomendacao_do_envio(monkeypatch) -> str:
    monkeypatch.setattr("app.api.routes.diagnostico.salvar_imagem", _salvar_imagem_falso)
    _forcar_diagnostico(monkeypatch, _inferencia_fungica(None, None))
    with TestClient(app) as client:
        resposta = client.post(
            "/diagnostico",
            data=_payload_valido(),
            files={"imagem": ("foto.jpg", BytesIO(_imagem_falsa()), "image/jpeg")},
            headers={"Authorization": "chave-de-teste-dispositivo"},
        )
    assert resposta.status_code == 200
    return resposta.json()["recomendacao"] or ""


async def test_estufa_seca_acrescenta_ressalva_sem_apagar_a_recomendacao(monkeypatch):
    await _semear_historico("pi-teste", dias=10, umidade_pct=65.0)
    recomendacao = await _recomendacao_do_envio(monkeypatch)

    assert "Aplique fungicida registrado." in recomendacao, (
        "a ressalva SOMA-SE a recomendacao agronomica, nunca a substitui"
    )
    assert "conferir" in recomendacao.lower() or "confira" in recomendacao.lower()
    assert "irrigação" in recomendacao.lower(), "o ponto cego tem que estar declarado"


async def test_estufa_umida_nao_acrescenta_ressalva(monkeypatch):
    """Ambiente favoravel mais diagnostico de fungo e concordancia, e
    concordancia nao precisa de ressalva."""
    await _semear_historico("pi-teste", dias=10, umidade_pct=95.0)
    recomendacao = await _recomendacao_do_envio(monkeypatch)
    assert recomendacao == "Aplique fungicida registrado."


async def test_sem_historico_nao_acrescenta_ressalva(monkeypatch):
    """Dispositivo recem-instalado: nao ha medicao para afirmar ausencia
    de molhamento, entao o sistema cala. Ausencia de dado nao e dado."""
    recomendacao = await _recomendacao_do_envio(monkeypatch)
    assert recomendacao == "Aplique fungicida registrado."
