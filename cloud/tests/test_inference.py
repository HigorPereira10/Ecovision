"""
Testes de app/core/inference.py.

A API deve continuar funcionando quando o modelo não pode ser carregado
(runtime ausente, arquivo faltando ou corrompido), com resultado
provisório. O pré-processamento tem dois pontos que corrompem o
diagnóstico sem gerar erro: os pixels devem ficar entre 0 e 255 (a
normalização faz parte do modelo) e o redimensionamento deve usar o
vizinho mais próximo, como no treino.
"""

import io
from pathlib import Path

import numpy as np
from PIL import Image

from app.core import inference


def _imagem_de_teste() -> bytes:
    imagem = Image.new("RGB", (800, 600), color=(100, 150, 80))
    buffer = io.BytesIO()
    imagem.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_preprocessar_imagem_gera_formato_esperado():
    array = inference.preprocessar_imagem(_imagem_de_teste())

    assert array.shape == (1, 224, 224, 3)
    assert array.dtype == np.float32


def test_preprocessar_imagem_devolve_pixels_crus_e_nao_normalizados():
    """Os pixels não podem ser divididos por 255: o modelo normaliza
    internamente, e a divisão levaria todas as predições a 'saudavel'."""
    array = inference.preprocessar_imagem(_imagem_de_teste())

    # A imagem de teste é lisa, cor (100, 150, 80). Se alguém voltar a
    # normalizar, esses valores viram 0.39/0.59/0.31 e o teste pega.
    assert array.max() > 1.0, "os pixels foram normalizados; o modelo espera 0-255"
    assert round(float(array[0, 0, 0, 1])) == 150


def test_preprocessar_imagem_usa_vizinho_mais_proximo_no_redimensionamento():
    """O redimensionamento deve usar o vizinho mais próximo (o padrão do
    Pillow é bicúbico)."""
    # Tabuleiro de 2x2 pixels: o vizinho mais próximo preserva os dois
    # valores originais; interpolações criam tons intermediários.
    original = Image.new("RGB", (2, 2))
    original.putpixel((0, 0), (0, 0, 0))
    original.putpixel((1, 0), (255, 255, 255))
    original.putpixel((0, 1), (255, 255, 255))
    original.putpixel((1, 1), (0, 0, 0))
    buffer = io.BytesIO()
    original.save(buffer, format="PNG")

    array = inference.preprocessar_imagem(buffer.getvalue())

    valores = set(np.unique(array).tolist())
    assert valores <= {0.0, 255.0}, (
        f"apareceram tons intermediarios {sorted(valores)[:5]}: o redimensionamento "
        "nao esta usando vizinho mais proximo"
    )


def test_classes_do_modelo_batem_com_o_conversor():
    """A ordem deve seguir as saídas do modelo; se divergir, cada predição
    recebe o nome e a recomendação de outra classe."""
    assert inference._CLASSES_DO_MODELO == [
        "septoriose",
        "pinta_preta",
        "saudavel",
        "estresse_foliar",
    ]

    # Toda classe do modelo precisa existir no catálogo agronômico,
    # senão o produtor recebe diagnóstico sem orientação nenhuma.
    for classe in inference._CLASSES_DO_MODELO:
        assert classe in inference._INFO_POR_CLASSE, f"{classe} fora do catalogo"


def test_carregar_modelo_com_arquivo_inexistente_retorna_none_sem_quebrar():
    interpretador = inference.carregar_modelo_tflite("/caminho/que/nao/existe.tflite")
    assert interpretador is None


def test_rodar_inferencia_sem_modelo_devolve_placeholder():
    array = inference.preprocessar_imagem(_imagem_de_teste())
    resultado = inference.rodar_inferencia(None, array)

    assert resultado == {
        "classe": "indisponivel",
        "confianca": 0.0,
        "recomendacao": None,
        "severidade": None,
    }


def test_caminho_do_modelo_resolve_a_partir_da_raiz_do_repo():
    """TFLITE_MODEL_PATH relativo é resolvido a partir da raiz do
    repositório, e não do diretório de trabalho (a API inicia em cloud/)."""
    from pathlib import Path

    from app.config import get_settings

    caminho = Path(get_settings().caminho_do_modelo)

    assert caminho.is_absolute(), "o caminho precisa independer de onde o processo rodou"
    assert caminho.is_file(), (
        f"modelo nao encontrado em {caminho}. O .tflite e versionado no repositorio "
        "(ml/models/): se sumiu ou foi renomeado, a API sobe sem inferencia."
    )


# --------------------------------------------- guarda de qualidade de imagem

def _imagem_jpeg(cor, tamanho=(224, 224)) -> bytes:
    from io import BytesIO
    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", tamanho, cor).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_foto_escura_demais_e_reprovada():
    """Imagem preta é reprovada: o modelo responderia 'saudavel' com alta
    confiança."""
    motivo = inference.avaliar_qualidade_imagem(_imagem_jpeg((10, 10, 12)))

    assert motivo is not None
    assert "escura" in motivo.lower()
    assert "iluminação" in motivo.lower(), "a mensagem tem que dizer o que fazer"


def test_imagem_lisa_e_reprovada_por_falta_de_detalhe():
    """Parede, lente tampada ou fora de foco total: brilho pode estar
    perfeito e não haver folha nenhuma. Textura zero é o sinal."""
    motivo = inference.avaliar_qualidade_imagem(_imagem_jpeg((128, 128, 128)))

    assert motivo is not None
    assert "detalhe" in motivo.lower()
    assert "lente" in motivo.lower()


def test_captura_real_do_dispositivo_passa():
    """A verificação não pode reprovar uma foto válida. Usa uma captura
    noturna do dispositivo, com o LED, a condição mais escura de operação."""
    from pathlib import Path

    caminho = Path(__file__).resolve().parent / "fixtures" / "captura_dispositivo.jpg"
    assert inference.avaliar_qualidade_imagem(caminho.read_bytes()) is None


def test_limiares_mantem_margem_sobre_a_pior_foto_boa():
    """Os limiares mantêm margem sobre a pior foto válida medida (brilho
    74,6 e textura 35,2): limiares próximos disso reprovariam fotos
    legítimas."""
    assert inference.TEXTURA_MINIMA < 35.2, "nao pode alcancar a pior foto boa"
    assert inference.BRILHO_MINIMO < 74.6
    # E não pode aceitar uma foto com 25% de luz (brilho 51,4, textura
    # 17,8), que o modelo classificou com 0,97 de confiança.
    assert inference.TEXTURA_MINIMA > 17.8


def test_modelo_com_numero_de_saidas_diferente_da_lista_nao_carrega(tmp_path, caplog):
    """Um modelo com menos saídas do que nomes em _CLASSES_DO_MODELO não
    pode ser carregado: atribuiria nomes errados com alta confiança."""
    import logging

    caminho = Path(__file__).resolve().parents[2] / "ml" / "models" / "modelo.tflite"
    if not caminho.is_file():
        pytest.skip("modelo de 3 classes nao esta no disco")

    original = inference._CLASSES_DO_MODELO
    inference._CLASSES_DO_MODELO = ["a", "b", "c", "d"]  # 4 nomes, modelo tem 3
    try:
        with caplog.at_level(logging.ERROR):
            interpretador = inference.carregar_modelo_tflite(str(caminho))
    finally:
        inference._CLASSES_DO_MODELO = original

    assert interpretador is None, "carregar com nomes a mais devolve None"
    assert "saídas" in caplog.text, "o log tem que dizer o que esta errado"
