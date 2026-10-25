"""
ml/src/training/ajuste_dois_dominios.py

Gera o modelo que esta em producao (ml/models/modelo.tflite), por ajuste
fino do baseline com DOIS dominios de imagem ao mesmo tempo.

POR QUE ESTE AJUSTE EXISTE
--------------------------
O baseline (ml/training/baseline_pinta_preta.keras) foi treinado so com
imagem de laboratorio: folha arrancada, fundo uniforme, luz de estudio.
Medido em 2026-10-22 sobre 277 fotos DE CAMPO (PlantDoc), ele acertava
57,0%, com o acaso em 33,3%. Ou seja: ia bem no dominio em que aprendeu
e mal no dominio em que o sistema de fato opera, que e foto de planta na
estufa.

Ajustar so com foto de campo resolvia metade do problema e criava outra:
subia campo para 69,3% e DERRUBAVA laboratorio de 90,7% para 78,2%, e o
modelo passava a chamar 495 das 1100 pinta pretas de laboratorio de
septoriose, porque herdava o desequilibrio do PlantDoc (138 septoriose
de 277). Era troca, nao melhora.

Treinar com os dois dominios juntos eliminou a troca.

RESULTADO (validacao cruzada de 5 dobras, 3577 imagens, cada uma testada
uma vez, comparacao pareada contra o baseline nas MESMAS imagens):

    dominio       baseline          este ajuste
    laboratorio   90,7% +- 0,2      95,3% +- 0,8    (+4,5 p.p.)
    campo         57,0% +- 4,7      74,0% +- 2,3   (+17,0 p.p.)

Venceu nas 5 dobras dos dois dominios: 10 comparacoes pareadas, 10
vitorias. Em campo tambem ficou mais estavel, com metade do desvio.

TRES DECISOES QUE FAZEM ESTE AJUSTE FUNCIONAR
---------------------------------------------
1. SO O TOPO DA BASE E DESCONGELADO (as 30 ultimas camadas, menos as de
   BatchNormalization). As camadas iniciais detectam borda e textura, que
   valem para qualquer imagem; descongelar tudo com poucas fotos de campo
   destruiria o que a rede aprendeu no ImageNet. As de BatchNormalization
   ficam congeladas porque, com lote de 16, as estatisticas de lote sao
   ruidosas demais e desestabilizam o ajuste.

2. TAXA DE APRENDIZADO BAIXA (1e-5, contra 1e-3 do treino original).
   Ajuste fino precisa de passos pequenos, senao o modelo esquece o que
   ja sabia. E o chamado esquecimento catastrofico, e foi exatamente o
   que aconteceu na versao que treinou so com campo.

3. PESO POR CLASSE E POR DOMINIO. Sao 3000 fotos de laboratorio contra
   249 de campo. Sem compensar, o campo vira ruido estatistico e o ajuste
   nao muda nada. Cada foto de campo entra valendo por cerca de 12 de
   laboratorio no calculo do class_weight.

   ATENCAO, APROXIMACAO ASSUMIDA: o Keras so aceita peso por CLASSE, nao
   por amostra. O peso de dominio entra embutido na contagem efetiva por
   classe, o que nao e equivalente a pesar cada imagem individualmente.
   Funcionou na medicao, mas nao e a formulacao exata do problema.

DADOS
-----
- Campo: ml/data/plantdoc_tomate/ (PlantDoc, recorte de tomate em 3
  classes). ATENCAO: NAO esta versionado. O .gitignore ignora ml/data/
  inteiro por peso, entao este conjunto vive apenas na maquina de quem
  treina. Vale tanto para as imagens quanto para a DIVISAO entre train/
  e test/, que e a parte insubstituivel: o PlantDoc e publico, a nossa
  divisao nao. Enquanto o deposito no Zenodo nao sair, perder o disco
  significa nao conseguir reproduzir nenhuma metrica de campo.
- Laboratorio: PlantVillage tomate, 3 classes, 1100 imagens cada. NAO
  esta versionado aqui por tamanho (cerca de 400 MB). Foi obtido do
  recorte publico em
  github.com/batestin1/coding_the_future_reconhecimento_de_pragas_com_redes_neurais
  (pasta dataset/, imagens 256x256 com os nomes originais do
  PlantVillage). Qualquer copia do PlantVillage tomate serve, desde que
  as pastas sejam mapeadas para as mesmas 3 classes.

ARMADILHAS QUE CONTINUAM VALENDO (ver ADR 0011)
-----------------------------------------------
- O modelo normaliza POR DENTRO: quem chama passa pixels CRUS de 0 a 255.
- A ordem das classes e septoriose, pinta_preta, saudavel, e tem que
  bater com _CLASSES_DO_MODELO em cloud/app/core/inference.py.
- Exportar SEM quantizacao.
- O vies do escuro NAO foi resolvido por este ajuste: foto subexposta
  continua saindo como "saudavel" com confianca alta. A guarda de
  qualidade de imagem em cloud/app/core/inference.py segue obrigatoria.

Como rodar (precisa de TensorFlow, que nao entra em cloud/requirements.txt
por causa do limite de RAM do Railway; usar um venv separado):

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
