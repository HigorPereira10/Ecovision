"""
Ajuste fino do modelo base com imagens de laboratório (PlantVillage) e de
campo (PlantDoc) ao mesmo tempo, gerando o modelo de três classes
(ml/models/modelo.tflite).

O modelo base, treinado só com laboratório, acertava 57,0% em campo.
Ajustar só com campo trocava um domínio pelo outro (laboratório caía de
90,7% para 78,2%). Com os dois domínios juntos, a validação cruzada de 5
dobras (3.577 imagens, comparação pareada) deu:

    domínio       modelo base       este ajuste
    laboratório   90,7% ± 0,2       95,3% ± 0,8
    campo         57,0% ± 4,7       74,0% ± 2,3

Decisões do ajuste:
1. Só as 30 últimas camadas da base são descongeladas, exceto as de
   BatchNormalization, cujas estatísticas seriam ruidosas com lotes de 16.
2. Taxa de aprendizado de 1e-5, para evitar esquecimento catastrófico.
3. Peso por classe e por domínio: 3.000 imagens de laboratório contra 249
   de campo. Como o Keras aceita apenas peso por classe, o peso de domínio
   entra na contagem efetiva de cada classe (aproximação).

Dados (não versionados; publicados no Zenodo ou de origem pública):
- campo: ml/data/plantdoc_tomate/, na divisão de plantdoc_tomate_divisao.csv;
- laboratório: PlantVillage, tomate, 3 classes com 1.100 imagens cada.

O modelo normaliza internamente (pixels de 0 a 255), a ordem das classes
é septoriose, pinta_preta, saudavel (igual a _CLASSES_DO_MODELO) e a
exportação é sem quantização. Requer TensorFlow, em ambiente separado:

    python ml/src/training/ajuste_dois_dominios.py --laboratorio <caminho>
"""

import argparse
import glob
import os

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import numpy as np
import tensorflow as tf
from tensorflow import keras

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASELINE = os.path.join(RAIZ, "training", "baseline_pinta_preta.keras")
PLANTDOC = os.path.join(RAIZ, "data", "plantdoc_tomate")

CLASSES = ["septoriose", "pinta_preta", "saudavel"]
# Nome da pasta -> indice da classe. O indice tem que bater com
# _CLASSES_DO_MODELO do backend, nao com a ordem alfabetica da pasta.
PASTA_CAMPO = {"distrator_septoria": 0, "pinta_preta": 1, "saudavel": 2}
PASTA_LAB = {"mancha_septoria": 0, "pinta_preta": 1, "folhas_saudaveis": 2}
TAMANHO = (224, 224)
SEMENTE = 42
EPOCAS = 10
LOTE = 16
TAXA_APRENDIZADO = 1e-5
CAMADAS_DESCONGELADAS = 30


def coletar(raiz, splits, mapa):
    itens = []
    for split in splits:
        for pasta, indice in mapa.items():
            for caminho in glob.glob(os.path.join(raiz, split, pasta, "*")):
                if os.path.isfile(caminho):
                    itens.append((caminho, indice))
    return itens


def montar_ds(itens, embaralhar):
    caminhos = [c for c, _ in itens]
    rotulos = [r for _, r in itens]

    def ler(caminho, rotulo):
        img = tf.image.decode_image(
            tf.io.read_file(caminho), channels=3, expand_animations=False
        )
        img = tf.image.resize(img, TAMANHO, method="bilinear")
        return tf.cast(img, tf.float32), rotulo  # pixels CRUS 0-255

    ds = tf.data.Dataset.from_tensor_slices((caminhos, rotulos))
    if embaralhar:
        ds = ds.shuffle(min(len(caminhos), 4096), seed=SEMENTE)
    return ds.map(ler, num_parallel_calls=tf.data.AUTOTUNE).batch(LOTE).prefetch(
        tf.data.AUTOTUNE
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--laboratorio", required=True,
        help="pasta do PlantVillage, com subpastas train/ e test/",
    )
    parser.add_argument("--saida", default=os.path.join(RAIZ, "models", "modelo.tflite"))
    args = parser.parse_args()

    tf.random.set_seed(SEMENTE)
    rng = np.random.default_rng(SEMENTE)

    lab = coletar(args.laboratorio, ("train",), PASTA_LAB)
    campo = coletar(PLANTDOC, ("train",), PASTA_CAMPO)
    if not lab or not campo:
        raise SystemExit("Nao encontrei imagens. Confira os caminhos e os nomes das pastas.")
    print(f"laboratorio={len(lab)}  campo={len(campo)}")

    treino = lab + campo
    rng.shuffle(treino)
    corte = int(len(treino) * 0.12)
    val, treino = treino[:corte], treino[corte:]

    peso_dominio = len(lab) / len(campo)
    efetiva = np.zeros(len(CLASSES))
    for _, r in lab:
        efetiva[r] += 1.0
    for _, r in campo:
        efetiva[r] += peso_dominio
    peso = {i: float(efetiva.sum() / (len(CLASSES) * efetiva[i])) for i in range(len(CLASSES))}
    print(f"peso de dominio={peso_dominio:.1f}  class_weight=" +
          ", ".join(f"{CLASSES[i]}={peso[i]:.2f}" for i in peso))

    modelo = keras.models.load_model(BASELINE)
    base = next(c for c in modelo.layers if "mobilenet" in c.name)
    base.trainable = True
    limite = len(base.layers) - CAMADAS_DESCONGELADAS
    for i, camada in enumerate(base.layers):
        if i < limite or isinstance(camada, keras.layers.BatchNormalization):
            camada.trainable = False
    print(f"descongeladas {sum(1 for c in base.layers if c.trainable)} de {len(base.layers)}")

    modelo.compile(
        optimizer=keras.optimizers.Adam(learning_rate=TAXA_APRENDIZADO),
        loss=keras.losses.SparseCategoricalCrossentropy(),
        metrics=["accuracy"],
    )
    modelo.fit(
        montar_ds(treino, True),
        validation_data=montar_ds(val, False),
        epochs=EPOCAS,
        class_weight=peso,
        callbacks=[keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=3, restore_best_weights=True)],
        verbose=2,
    )

    keras_destino = os.path.join(RAIZ, "training", "modelo_hibrido_lab_campo.keras")
    modelo.save(keras_destino)
    print(f"keras salvo: {keras_destino}")

    # SEM quantizacao: no baseline, a versao quantizada inverteu 2 de 7
    # predicoes para economizar 6 MB. Diagnostico nao se troca por disco.
    conversor = tf.lite.TFLiteConverter.from_keras_model(modelo)
    tflite = conversor.convert()
    with open(args.saida, "wb") as arquivo:
        arquivo.write(tflite)
    print(f"tflite salvo: {args.saida}  ({len(tflite)/1024/1024:.2f} MB)")


if __name__ == "__main__":
    main()
