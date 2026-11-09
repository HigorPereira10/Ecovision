"""
Gera a referência da verificação de familiaridade: os vetores de atributos
(1280 dimensões, saída do GlobalAveragePooling) das imagens de treino.

Uma janela nova é comparada a esses vetores por similaridade de cosseno
com o vizinho mais próximo; valores baixos indicam conteúdo diferente de
tudo o que o modelo viu (fundo, parede, vaso). Na extração de janelas para
rotulagem, a referência descarta recortes sem folha. O limiar padrão é o
percentil 5 da familiaridade no conjunto de teste do PlantDoc (0,604).

O preprocess_input da MobileNetV2 faz parte do grafo salvo, mas não
aparece em model.layers; ao montar o submodelo manualmente, ele precisa
ser aplicado de forma explícita.

Uso:
    python -m ml.src.porta.referencia

Grava ml/models/referencia_familiaridade.npz.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parents[3]
DADOS = RAIZ / "ml" / "data" / "plantdoc_tomate"
MODELO_KERAS = RAIZ / "ml" / "training" / "modelo_hibrido_lab_campo.keras"
SAIDA = RAIZ / "ml" / "models" / "referencia_familiaridade.npz"

# A ordem é a mesma que o treino usou, porque
# image_dataset_from_directory ordena os diretórios alfabeticamente.
CLASSES_PASTA = ["distrator_septoria", "pinta_preta", "saudavel"]
CLASSES_MODELO = ["septoriose", "pinta_preta", "saudavel"]

TAMANHO = (224, 224)
LOTE = 8  # lotes pequenos: a máquina de desenvolvimento tem pouca RAM livre


def _carregar_modelo():
    import keras

    modelo = keras.models.load_model(MODELO_KERAS)
    return (
        modelo,
        modelo.get_layer("mobilenetv2_1.00_224"),
        modelo.get_layer("global_average_pooling2d"),
    )


def extrator(mobilenet, pooling):
    """Devolve uma função que mapeia um lote de imagens (pixels de 0 a 255)
    para os vetores de 1280 dimensões, aplicando o preprocess_input."""
    import keras
    import tensorflow as tf

    preparar = keras.applications.mobilenet_v2.preprocess_input

    def calcular(imagens: list[np.ndarray]) -> np.ndarray:
        saida = []
        for inicio in range(0, len(imagens), LOTE):
            bloco = np.asarray(imagens[inicio : inicio + LOTE], np.float32)
            tensor = preparar(tf.convert_to_tensor(bloco))
            saida.append(pooling(mobilenet(tensor, training=False)).numpy())
        return np.vstack(saida)

    return calcular


def normalizar(vetores: np.ndarray) -> np.ndarray:
    """Normaliza para norma 1, o que transforma produto escalar em
    similaridade de cosseno."""
    return vetores / np.linalg.norm(vetores, axis=1, keepdims=True)


def _ler_particao(particao: str) -> tuple[list[np.ndarray], list[int]]:
    imagens, rotulos = [], []
    for indice, pasta in enumerate(CLASSES_PASTA):
        diretorio = DADOS / particao / pasta
        for arquivo in sorted(os.listdir(diretorio)):
            imagem = Image.open(diretorio / arquivo).convert("RGB")
            imagens.append(
                np.asarray(imagem.resize(TAMANHO, Image.BILINEAR), np.float32)
            )
            rotulos.append(indice)
    return imagens, rotulos


def main() -> int:
    if not MODELO_KERAS.exists():
        print(f"Modelo Keras não encontrado em {MODELO_KERAS}", file=sys.stderr)
        return 1

    _, mobilenet, pooling = _carregar_modelo()
    calcular = extrator(mobilenet, pooling)

    print("Calculando vetores de referência a partir do conjunto de treino...")
    treino, rotulos = _ler_particao("train")
    referencia = normalizar(calcular(treino))

    print("Calibrando o limiar com o conjunto de teste...")
    teste, _ = _ler_particao("test")
    familiaridade_teste = (normalizar(calcular(teste)) @ referencia.T).max(axis=1)
    limiar = float(np.percentile(familiaridade_teste, 5))

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        SAIDA,
        referencia=referencia.astype(np.float32),
        rotulos=np.asarray(rotulos, np.int16),
        limiar=np.asarray(limiar, np.float32),
        familiaridade_teste=familiaridade_teste.astype(np.float32),
        classes=np.asarray(CLASSES_MODELO),
    )
    tamanho_mb = SAIDA.stat().st_size / 1e6
    print(
        f"Gravado {SAIDA.relative_to(RAIZ)}: {referencia.shape[0]} vetores de "
        f"{referencia.shape[1]} dimensões, {tamanho_mb:.2f} MB"
    )
    print(
        f"Limiar (percentil 5 do teste): {limiar:.3f}   "
        f"mediana do teste: {np.median(familiaridade_teste):.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
