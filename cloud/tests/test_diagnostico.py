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
4. O diagnóstico gravado vem do modelo real (ml/models/modelo.tflite,
   versionado no repositório). Se por algum motivo ele não carregar, a
   API ainda responde 200 com o placeholder "indisponivel", em vez de
   derrubar o envio da captura.
5. Reenvio da MESMA captura (mesmo idempotency_key), uma situação
   real: a API confirma 200 mas o Pi cai antes de tirar o registro da
   fila local, e no próximo ciclo ele reenvia a mesma foto. A API
   detecta e devolve o diagnóstico já existente, sem duplicar a linha
   no banco.
6. Imagem corrompida ou inválida: a API recusa com 400 (erro claro),
   em vez de travar com um 500 cru.
7. Diagnóstico que não é "saudavel" nem o placeholder "indisponivel"
   gera um alerta automático; o placeholder não gera, porque avisar o
   produtor de uma classe que não significa nada seria pior que não
   avisar.
8. timestamp ou leitura de sensor em formato inválido: recusado com
   422 ANTES de subir a imagem para o storage (evita imagem órfã no
   bucket).
9. Imagem maior que o limite (5MB): recusada com 413, sem processar.
10. Duas requisições com a MESMA idempotency_key "correndo" ao mesmo
    tempo (a checagem inicial ainda não vê a outra): a segunda não
    quebra com erro de chave duplicada, devolve o diagnóstico que já
    tinha sido criado pela primeira.
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
    """Um JPEG pequeno, mas de verdade, e com TEXTURA.

    Era um quadrado de cor única até 2026-10-17. Isso deixou de servir
    quando a guarda de qualidade entrou em app/core/inference.py: uma
    imagem lisa é exatamente o que ela reprova (lente tampada, parede,
    fora de foco total), então todo teste de envio bem-sucedido passou a
    receber "imagem_inadequada" em vez do diagnóstico esperado.

    A falha foi útil: provou que a guarda pega o caso para o qual foi
    escrita. O padrão quadriculado abaixo tem brilho e desvio padrão
    acima dos limiares, imitando uma foto com conteúdo.

    EM 2026-11-02 A FIXTURE PRECISOU EVOLUIR DE NOVO, pelo mesmo motivo.
    O diagnóstico por janela (app/core/janelas.py) exige, além de brilho
    e textura, COBERTURA DE VERDE: janela sem folha não vale
    diagnóstico. O xadrez cinza passava na guarda antiga e era recusado
    por "sem folha", devolvendo imagem_inadequada em oito testes.

    De novo a falha foi útil, e pela mesma razão: provou que a guarda
    por janela recusa o que não é folha. A correção é tornar o xadrez
    VERDE e grande o bastante para render janelas, não afrouxar a
    guarda.

    O tamanho importa: janelas.recortar decodifica em metade (ESCALA=2)
    e recorta blocos de 448, então uma imagem de 64 px não rende janela
    nenhuma."""
    import numpy as np

    # Xadrez VERDE de 16x16 com ruído leve. Verde porque a guarda por
    # janela mede cobertura de folha.
    #
    # O TAMANHO TEM QUE RENDER PELO MENOS JANELAS_MINIMAS JANELAS. Com
    # 1024x1024 saía UMA só: recortar() decodifica em metade, sobram
    # 512 px, e uma janela de 448 com passo 224 só cabe uma vez. Em
    # 2026-11-03, quando o mínimo de janelas entrou, isso derrubou três
    # testes com "imagem_inadequada".
    #
    # 2688x1512 (16:9, como a câmera) vira 1344x756 e rende 5 por 2,
    # ou seja 10 janelas: margem confortável sobre o mínimo de 6.
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
    """Faz a rota devolver `resultado`, seja qual for o caminho de
    inferencia.

    Desde 2026-11-02 a rota tem DOIS caminhos: o quadro inteiro
    (inference.rodar_inferencia) e a janela deslizante
    (janelas.diagnosticar_por_janelas), escolhidos por
    DIAGNOSTICO_POR_JANELA. Um teste que so trocava o primeiro passou a
    nao ter efeito nenhum quando a chave ligou, e o sintoma era
    confuso: o teste de alerta falhava como se o alerta estivesse
    quebrado.

    Estes testes sao sobre ALERTA e RESSALVA, nao sobre qual caminho de
    inferencia roda, entao eles fixam a saida dos dois.
    """
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
    # Antes este teste fixava "indisponivel", porque o modelo nao
    # carregava. Nao era o comportamento desejado: era um bug de caminho
    # relativo (ver test_inference.py). Agora o modelo real roda, entao a
    # assercao e sobre o CONTRATO, nao sobre uma classe especifica: assim
    # o teste continua valendo quando o modelo for retreinado.
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
    """O titulo do alerta e texto GRAVADO, nao classe que a tela traduz.

    O titulo era montado interpolando a chave crua da classe, e o
    alerta do ciclo de 2026-11-03 chegou ao aplicativo escrito
    "Possivel estresse_foliar detectado", com o sublinhado a vista. O
    app tem a sua propria tabela de rotulos, mas ela nao alcanca este
    caso: o que esta em alertas.titulo e o que o produtor le.

    A classe escolhida aqui e justamente a de nome composto, que e a
    unica em que o defeito aparecia.
    """
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


async def test_foto_reprovada_guarda_a_imagem_mas_nao_afirma_diagnostico(monkeypatch):
    """O comportamento decidido pelo grupo em 2026-10-17.

    A captura com foto ruim NÃO é descartada: a imagem é guardada e as
    leituras também, porque é olhando a própria foto que o produtor
    descobre o que aconteceu (LED apagado, lente suja, captura à noite)
    e confere se o aviso estava certo.

    O que NÃO acontece é afirmar um diagnóstico. Sem esta guarda, uma
    foto preta recebia "saudavel" com 0,93 de confiança, que é a
    afirmação mais perigosa que este sistema pode fazer: diz ao produtor
    que a planta está bem, com alta confiança, sobre uma imagem onde não
    se vê nada."""
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
        # E nenhum alerta de doenca: o sistema nao acusa doenca nenhuma
        # a partir de uma foto que ele mesmo recusou analisar. O alerta
        # de doenca tem o formato "Sinal de <classe> na planta", e e
        # esse prefixo que o distingue.
        #
        # A assercao era sobre a palavra "detectado", do titulo antigo.
        # Depois que o titulo mudou ela continuava passando, mas sem
        # provar nada: nenhum titulo tem mais essa palavra.
        assert "sinal de" not in alertas[0].titulo.lower()


# --- 11. ressalva de plausibilidade ambiental ---------------------------
#
# O modelo de imagem nao duvida de si mesmo: medido em 2026-11-01, os
# logits de uma planta com amarelamento nutricional ficam no mesmo
# patamar dos das classes conhecidas (mediana 1,70 contra 1,89), entao
# ele acusa doenca com confianca alta e nada na visao o contradiz. Quem
# contradiz e o historico da estufa, via app/core/pressao_infecciosa.py.
#
# O que os testes abaixo fixam: a ressalva so aparece quando ha medicao
# suficiente E o ambiente de fato nao sustentou infeccao, e ela nunca
# substitui a recomendacao agronomica, so se soma a ela.


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
