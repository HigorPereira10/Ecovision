"""
cloud/tests/test_inference.py

O que este arquivo verifica, em português simples:

O modelo de IA (.tflite) que de fato reconhece doenças na folha ainda
não existe — quem treina isso é a camada ml/, que também está no
início. Em vez de a API travar ou recusar subir por causa disso, ela
deve continuar funcionando e devolver um resultado "placeholder"
(faz-de-conta), avisando no log, para todo o resto do sistema (upload
da imagem, gravação no banco) já poder ser testado e usado antes do
modelo real ficar pronto.

Também confere que o pré-processamento da imagem (redimensionar para
224x224 e normalizar os valores de cor) produz o formato que qualquer
modelo TFLite espera receber.
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
    assert array.min() >= 0.0
    assert array.max() <= 1.0


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
