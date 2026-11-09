"""
Testes de app/core/janelas.py:

1. geometria das janelas igual à do treino;
2. verificação de qualidade aplicada a cada janela;
3. agregação por incidência, e não por maioria;
4. ordem de severidade: doença, estresse, saudável;
5. sem janela aproveitável, resultado "imagem_inadequada";
6. mesmo contrato de inference.rodar_inferencia.
"""

import io

import numpy as np
import pytest
from PIL import Image

from app.core import janelas
from app.core.inference import CLASSE_IMAGEM_INADEQUADA


class _InterpretadorFalso:
    """Devolve uma sequência fixa de probabilidades, uma por chamada,
    imitando a API do tflite-runtime (set_tensor/invoke/get_tensor) para
    exercitar o laço real."""

    def __init__(self, respostas):
        self._respostas = list(respostas)
        self._atual = None
        self.chamadas = 0

    def get_input_details(self):
        return [{"index": 0}]

    def get_output_details(self):
        return [{"index": 1}]

    def set_tensor(self, indice, valor):
        pass

    def invoke(self):
        self._atual = self._respostas[min(self.chamadas, len(self._respostas) - 1)]
        self.chamadas += 1

    def get_tensor(self, indice):
        return np.asarray([self._atual], dtype=np.float32)


def _textura(forma, rng, amplitude=70):
    """Textura em blocos de 16 px, que sobrevive à compressão JPEG (ruído
    por pixel seria descartado e a janela reprovaria por textura)."""
    altura, largura = forma
    pequeno = rng.integers(-amplitude, amplitude, (altura // 16 + 1, largura // 16 + 1))
    return np.kron(pequeno, np.ones((16, 16), np.int16))[:altura, :largura]


def _foto(cor=(60, 160, 70), tamanho=(4608, 2592), amplitude=70) -> bytes:
    """Captura sintética no tamanho real da câmera (4608 × 2592), que rende
    as 36 janelas da grade."""
    rng = np.random.default_rng(7)
    base = np.zeros((tamanho[1], tamanho[0], 3), np.int16)
    base[:, :] = cor
    # Mesma textura nos três canais: a verificação mede o cinza, e ruídos
    # independentes por canal se cancelariam.
    ruido = _textura((tamanho[1], tamanho[0]), rng, amplitude)
    for canal in range(3):
        base[..., canal] += ruido
    arquivo = io.BytesIO()
    Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).save(
        arquivo, format="JPEG", quality=92
    )
    return arquivo.getvalue()


def _janela(cor, rng=None, amplitude=70):
    """Uma janela 224x224 já pronta, com a mesma textura em blocos."""
    rng = rng or np.random.default_rng(3)
    recorte = np.zeros((224, 224, 3), np.float32)
    ruido = _textura((224, 224), rng, amplitude)
    for canal in range(3):
        recorte[..., canal] = np.clip(cor[canal] + ruido, 0, 255)
    return recorte


def _classes(monkeypatch, nomes, info=None):
    monkeypatch.setattr(janelas, "_CLASSES_DO_MODELO", nomes)
    monkeypatch.setattr(
        janelas, "_INFO_POR_CLASSE", info or {n: (None, None) for n in nomes}
    )


# --- 1. geometria ---


def test_a_geometria_bate_com_a_do_treino():
    """A geometria deve ser a mesma de ml/src/porta/avaliar.py e
    ml/src/dataset/extrair_janelas.py."""
    assert janelas.JANELA_NATIVA == 896
    assert janelas.PASSO_NATIVO == 448
    assert janelas.ESCALA == 2


def test_recorta_na_grade_esperada():
    recortes, posicoes = janelas.recortar(_foto())
    assert len(recortes) == len(posicoes) == 36
    assert all(r.shape == (224, 224, 3) for r in recortes)
    # passo de 448 nativos vira 224 na imagem decodificada em 1/2
    assert posicoes[1][0] - posicoes[0][0] == 224


def test_imagem_menor_que_a_janela_nao_quebra():
    recortes, _ = janelas.recortar(_foto(tamanho=(300, 300)))
    assert recortes, "deveria ao menos recortar uma janela"


# --- 2. a guarda roda por janela ---


def test_janela_escura_e_recusada():
    escura = np.full((224, 224, 3), 10, np.float32)
    assert janelas._janela_aproveitavel(escura) == "escura"


def test_janela_sem_detalhe_e_recusada():
    """Cor sólida e clara: brilho passa, textura não. É parede, plástico
    da estufa ou lente embaçada."""
    lisa = np.full((224, 224, 3), 200, np.float32)  # sem textura nenhuma
    assert janelas._janela_aproveitavel(lisa) == "sem detalhe"


def test_janela_sem_folha_e_recusada():
    terra = _janela((150, 105, 80))  # marrom texturizado: passa brilho e textura
    assert janelas._janela_aproveitavel(terra) == "sem folha"


def test_janela_de_folha_passa():
    assert janelas._janela_aproveitavel(_janela((60, 160, 70))) is None


# --- 3. agregação por incidência ---


def test_minoria_acima_do_limiar_vence_a_maioria(monkeypatch):
    """Teste central: 30% das janelas com doença resulta em doença, mesmo
    com 70% sadias."""
    _classes(monkeypatch, ["septoriose", "pinta_preta", "saudavel"])
    doente = [0.05, 0.90, 0.05]
    sadia = [0.05, 0.05, 0.90]
    # 11 doentes e 25 sadias de 36: 31%, acima dos 20%
    interp = _InterpretadorFalso([doente] * 11 + [sadia] * 25)

    resultado = janelas.diagnosticar_por_janelas(interp, _foto())

    assert resultado["classe"] == "pinta_preta"
    assert resultado["incidencia"] == pytest.approx(11 / 36, abs=0.02)
    assert resultado["votos"]["saudavel"] == 25, "a maioria continua visível"


def test_abaixo_do_limiar_nao_vira_diagnostico(monkeypatch):
    """Com 7% de falso positivo medido, poucos votos positivos são
    ruído. Duas janelas em 36 (5,6%) não podem condenar a planta."""
    _classes(monkeypatch, ["septoriose", "pinta_preta", "saudavel"])
    interp = _InterpretadorFalso([[0.05, 0.90, 0.05]] * 2 + [[0.05, 0.05, 0.90]] * 34)

    resultado = janelas.diagnosticar_por_janelas(interp, _foto())

    assert resultado["classe"] == "saudavel"


def test_o_limiar_fica_acima_do_falso_positivo_medido():
    """A fração de incidência deve ficar acima da taxa de falso positivo do
    modelo (7%)."""
    assert janelas.FRACAO_MINIMA_INCIDENCIA >= 0.15


# --- 4. ordem de severidade ---


def test_doenca_vence_estresse_quando_as_duas_passam(monkeypatch):
    _classes(monkeypatch, ["septoriose", "pinta_preta", "saudavel", "estresse_foliar"])
    doente = [0.05, 0.85, 0.05, 0.05]
    estresse = [0.05, 0.05, 0.05, 0.85]
    # 9 doentes (25%) e 27 com estresse (75%): as duas passam do limiar
    interp = _InterpretadorFalso([doente] * 9 + [estresse] * 27)

    resultado = janelas.diagnosticar_por_janelas(interp, _foto())

    assert resultado["classe"] == "pinta_preta", "doença precede estresse"


def test_estresse_vence_saudavel_quando_passa(monkeypatch):
    _classes(monkeypatch, ["septoriose", "pinta_preta", "saudavel", "estresse_foliar"])
    estresse = [0.05, 0.05, 0.05, 0.85]
    sadia = [0.05, 0.05, 0.85, 0.05]
    interp = _InterpretadorFalso([estresse] * 10 + [sadia] * 26)

    resultado = janelas.diagnosticar_por_janelas(interp, _foto())

    assert resultado["classe"] == "estresse_foliar"


def test_a_ordem_de_severidade_cobre_todas_as_classes_do_modelo():
    """Classe fora de ORDEM_SEVERIDADE nunca venceria por incidência,
    só por maioria, e isso passaria despercebido."""
    for nome in ("septoriose", "pinta_preta", "estresse_foliar", "saudavel"):
        assert nome in janelas.ORDEM_SEVERIDADE


# --- 5. nenhuma janela aproveitável ---


def test_foto_toda_escura_devolve_imagem_inadequada(monkeypatch):
    _classes(monkeypatch, ["septoriose", "pinta_preta", "saudavel"])
    interp = _InterpretadorFalso([[0.05, 0.05, 0.90]])

    resultado = janelas.diagnosticar_por_janelas(interp, _foto(cor=(6, 6, 6), amplitude=3))

    assert resultado["classe"] == CLASSE_IMAGEM_INADEQUADA
    assert resultado["confianca"] == 0.0
    assert resultado["janelas"] == 0
    assert interp.chamadas == 0, "não roda o modelo sobre janela nenhuma"


# --- 6. o contrato não muda ---


def test_devolve_o_mesmo_contrato_de_rodar_inferencia(monkeypatch):
    _classes(
        monkeypatch,
        ["septoriose", "pinta_preta", "saudavel"],
        {"pinta_preta": ("Texto do catálogo.", "media"), "saudavel": (None, None)},
    )
    interp = _InterpretadorFalso([[0.05, 0.90, 0.05]] * 36)

    resultado = janelas.diagnosticar_por_janelas(interp, _foto())

    for chave in ("classe", "confianca", "recomendacao", "severidade"):
        assert chave in resultado, f"o app espera {chave}"
    assert resultado["severidade"] == "media"
    assert "Texto do catálogo." in resultado["recomendacao"]


def test_a_incidencia_entra_no_texto_que_o_produtor_le(monkeypatch):
    """A incidência é o número acionável: diz quanto da planta está
    afetado. Ela não pode viver só no log."""
    _classes(
        monkeypatch,
        ["septoriose", "pinta_preta", "saudavel"],
        {"pinta_preta": ("Texto do catálogo.", "media")},
    )
    interp = _InterpretadorFalso([[0.05, 0.90, 0.05]] * 36)

    resultado = janelas.diagnosticar_por_janelas(interp, _foto())

    assert "36" in resultado["recomendacao"]
    assert "%" in resultado["recomendacao"]


def test_planta_sadia_nao_ganha_frase_de_incidencia(monkeypatch):
    """Dizer 'sinal observado em 0% da planta' seria ruído na tela."""
    _classes(monkeypatch, ["septoriose", "pinta_preta", "saudavel"])
    interp = _InterpretadorFalso([[0.05, 0.05, 0.90]] * 36)

    resultado = janelas.diagnosticar_por_janelas(interp, _foto())

    assert resultado["classe"] == "saudavel"
    assert resultado["recomendacao"] is None


# --- 7. objeto verde que não é folha ---


def test_superficie_verde_lisa_nao_e_folha(monkeypatch):
    """Um pote plástico verde-azulado rende de 9% a 12% de cobertura verde
    e não pode passar; nas janelas rotuladas, nenhuma folha real fica
    abaixo de 20,5%."""
    _classes(monkeypatch, ["septoriose", "pinta_preta", "saudavel"])

    # A cena real mistura pote, plástico branco, fios e madeira; só 9% a
    # 12% dos pixels são verdes.
    janela = _janela((150, 150, 148))  # cinza texturizado: fundo
    lado = int(224 * (0.11 ** 0.5))  # mancha que cobre ~11% da area
    janela[:lado, :lado] = _janela((60, 140, 120))[:lado, :lado]

    cobertura = janelas._cobertura_verde(janela)
    assert 0.08 < cobertura < 0.18, (
        f"o dubles precisa cair na faixa que passava antes: {cobertura:.3f}"
    )
    assert janelas._janela_aproveitavel(janela) == "sem folha", (
        "11% de verde era o que o pote plastico produzia, e passava no "
        "limiar antigo de 8%"
    )


def test_o_limiar_de_verde_nao_corta_folha_real():
    """O outro lado do mesmo numero: subir demais perderia diagnostico.
    O percentil 5 das janelas rotuladas como folha e 20,5%."""
    assert janelas.COBERTURA_VERDE_MINIMA < 0.20


def test_poucas_janelas_nao_viram_diagnostico(monkeypatch):
    """Com poucas janelas aproveitáveis, um único voto ultrapassaria a
    fração de incidência; abaixo do mínimo, nenhum diagnóstico é afirmado."""
    _classes(monkeypatch, ["septoriose", "pinta_preta", "saudavel"])
    interp = _InterpretadorFalso([[0.05, 0.05, 0.90]] * 36)

    # imagem em que so uma faixa estreita tem folha
    import io

    import numpy as np
    from PIL import Image

    rng = np.random.default_rng(5)
    base = np.zeros((2592, 4608, 3), np.int16)
    base[:, :] = (150, 150, 150)  # cinza: sem folha
    ruido = np.kron(
        rng.integers(-70, 70, (2592 // 16 + 1, 4608 // 16 + 1)),
        np.ones((16, 16), np.int16),
    )[:2592, :4608]
    for canal in range(3):
        base[..., canal] += ruido
    # uma faixa verde estreita, que rende menos de 6 janelas
    base[:300, :900] = np.stack([
        np.clip(60 + ruido[:300, :900], 0, 255),
        np.clip(160 + ruido[:300, :900], 0, 255),
        np.clip(70 + ruido[:300, :900], 0, 255),
    ], axis=-1)
    arquivo = io.BytesIO()
    Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).save(
        arquivo, format="JPEG", quality=92
    )

    resultado = janelas.diagnosticar_por_janelas(interp, arquivo.getvalue())

    assert resultado["classe"] == CLASSE_IMAGEM_INADEQUADA
    assert resultado["janelas"] < janelas.JANELAS_MINIMAS
