"""
cloud/tests/test_inference.py

O que este arquivo verifica, em português simples:

Desde 2026-10-10 existe um modelo real em ml/models/modelo.tflite (3
classes). Ainda assim, a API precisa continuar de pé quando o modelo
não puder ser carregado (runtime ausente, arquivo faltando, arquivo
corrompido), devolvendo um resultado "placeholder" e avisando no log,
em vez de recusar subir. Uma falha no modelo nunca pode derrubar o
upload da imagem nem a gravação no banco.

Também confere o pré-processamento da imagem, que tem duas
particularidades capazes de corromper TODO diagnóstico sem levantar
erro nenhum, e por isso valem teste próprio:

1. Os pixels precisam sair CRUS, de 0 a 255. O modelo normaliza por
   dentro; dividir por 255 aqui faz tudo virar "saudavel" com ~90% de
   confiança, inclusive folha doente.
2. O redimensionamento precisa ser por vizinho mais próximo, igual ao
   do treino. Com interpolação diferente, 2 das 6 imagens de
   ml/validacao_externa/ trocam de classe.
"""

import io

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
    """Regressão: a versão anterior dividia por 255. Como o modelo
    normaliza por dentro, isso colapsava toda predição para 'saudavel'
    sem erro nenhum."""
    array = inference.preprocessar_imagem(_imagem_de_teste())

    # A imagem de teste é lisa, cor (100, 150, 80). Se alguém voltar a
    # normalizar, esses valores viram 0.39/0.59/0.31 e o teste pega.
    assert array.max() > 1.0, "os pixels foram normalizados; o modelo espera 0-255"
    assert round(float(array[0, 0, 0, 1])) == 150


def test_preprocessar_imagem_usa_vizinho_mais_proximo_no_redimensionamento():
    """Regressão: o padrão do Pillow é bicúbico, e o treino usou vizinho
    mais próximo. Medido nas 6 imagens de validação externa, a troca de
    interpolação muda a classe de 2 delas."""
    # Tabuleiro de 2x2 pixels: com vizinho mais próximo, a ampliação
    # para 224x224 preserva exatamente os dois valores originais. Com
    # bicúbico ou bilinear, aparecem tons intermediários nas bordas.
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
    """A ordem aqui precisa ser a mesma de ml/src/export/convert_tflite.py.
    Se divergir, cada predição sai com o nome e a recomendação de outra
    doença, e nada falha de forma visível."""
    assert inference._CLASSES_DO_MODELO == ["septoriose", "pinta_preta", "saudavel"]

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
    """Regressão: TFLITE_MODEL_PATH é relativo e era resolvido contra o
    diretório de trabalho do processo. Como a API sobe de dentro de
    cloud/, ela procurava em cloud/ml/models/ e subia SEM MODELO, em
    silêncio, devolvendo placeholder como se nada estivesse errado."""
    from pathlib import Path

    from app.config import get_settings

    caminho = Path(get_settings().caminho_do_modelo)

    assert caminho.is_absolute(), "o caminho precisa independer de onde o processo rodou"
    assert caminho.is_file(), (
        f"modelo nao encontrado em {caminho}. O .tflite e versionado no repositorio "
        "(Blueprint Secao 4.4): se sumiu ou foi renomeado, a API sobe sem inferencia."
    )
