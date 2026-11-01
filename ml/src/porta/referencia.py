"""
ml/src/porta/referencia.py

Gera o artefato de referência da PORTA DE FAMILIARIDADE: os vetores de
atributos (1280 dimensões, saída do GlobalAveragePooling) de todas as
imagens de treino. É contra eles que uma captura nova é comparada para
decidir se o modelo já viu algo parecido.

POR QUE ISTO EXISTE
-------------------
O classificador tem três saídas e um softmax. Toda entrada é
distribuída entre septoriose, pinta_preta e saudável, inclusive
entrada que não é folha. Medido em 2026-10-31 sobre uma captura real
do dispositivo: de 158 janelas que não continham folha nenhuma
(cobertura de verde abaixo de 2%), 45% foram classificadas como
doença. Parede, chão e vaso viram diagnóstico.

A porta resolve isso sem rótulo novo e sem retreinar: em vez de
perguntar "qual das três classes é esta?", pergunta antes "isto se
parece com algo que o modelo aprendeu?".

COMO A FAMILIARIDADE É DEFINIDA
-------------------------------
Similaridade de cosseno entre o vetor da entrada e o vetor mais
próximo do conjunto de treino. Valor alto significa que existe pelo
menos uma imagem de treino parecida; valor baixo significa que a
entrada é estranha ao que o modelo conhece.

VALORES MEDIDOS EM 2026-10-31
-----------------------------
Referência: 249 imagens de treino do PlantDoc.

    PlantDoc teste (dentro da distribuição) .... mediana 0,664
    Folha danificada, bem enquadrada .......... 0,711
    Folha limpa, bem enquadrada ............... 0,643
    Janelas do dispositivo, em geral .......... mediana 0,571
    Fundo sem folha (controle negativo) ....... mediana 0,391

O limiar padrão é o percentil 5 da familiaridade do conjunto de teste,
que deu 0,604. Com ele, 100% das janelas de fundo são recusadas e os
dois recortes de folha verificáveis a olho passam.

ATENÇÃO AO PRÉ-PROCESSAMENTO
----------------------------
O `preprocess_input` da MobileNetV2 está dentro do grafo do modelo
salvo, mas NÃO aparece em `model.layers`. Ao montar um sub-modelo por
travessia manual, como é feito aqui, ele precisa ser aplicado
explicitamente. Sem isso as predições colapsam para "saudavel" com
cerca de 90% em qualquer imagem (ver ml/models/README.md, quarta
regra).

USO
---
    python -m ml.src.porta.referencia

Grava ml/models/referencia_familiaridade.npz, de cerca de 1,3 MB.
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
    """Devolve uma função que mapeia um lote de imagens cruas de 0 a 255
    para os vetores de 1280 dimensões, aplicando o preprocess_input que
    o grafo espera mas que a travessia manual não traz junto."""
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
