"""
Acrescenta ao modelo a classe de estresse foliar, rotulada nas capturas do
próprio dispositivo, gerando o modelo em produção
(ml/models/modelo_dominio.tflite).

A classe é descritiva: indica alteração visível da folha que não
corresponde às doenças reconhecidas, sem afirmar a causa. Septoriose e
pinta-preta vêm só das bases públicas, e o estresse foliar só da estufa;
avaliar_dominio_proprio.py mede quantas janelas da estufa caem nas
classes fúngicas para acompanhar esse viés de origem.

Uso:

    python ml/src/training/ajuste_dominio_proprio.py \\
        --laboratorio ml/data/plantvillage_tomate \\
        --estufa ml/data/estufa_rotulada
"""

import argparse
import glob
import os
import sys

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import numpy as np
import tensorflow as tf
from tensorflow import keras

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
from ml.src.dataset.extrair_janelas import chave_posicao

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELO_BASE = os.path.join(RAIZ, "training", "modelo_hibrido_lab_campo.keras")
PLANTDOC = os.path.join(RAIZ, "data", "plantdoc_tomate")

# As três primeiras classes mantêm a posição: a ordem precisa coincidir com
# _CLASSES_DO_MODELO em cloud/app/core/inference.py.
CLASSES = [
    "septoriose",
    "pinta_preta",
    "saudavel",
    "estresse_foliar",
]
INDICE = {nome: i for i, nome in enumerate(CLASSES)}
CLASSES_FUNGICAS = {"septoriose", "pinta_preta"}

PASTA_CAMPO = {"distrator_septoria": 0, "pinta_preta": 1, "saudavel": 2}
PASTA_LAB = {"mancha_septoria": 0, "pinta_preta": 1, "folhas_saudaveis": 2}
# Classes da estufa que entram no treino (descartar fica de fora).
PASTAS_ESTUFA = ["saudavel", "estresse_foliar"]

TAMANHO = (224, 224)
SEMENTE = 42
EPOCAS = 25
LOTE = 16
TAXA_APRENDIZADO = 1e-5
CAMADAS_DESCONGELADAS = 30
VALIDACAO_POR_CLASSE = 8
PACIENCIA = 6


def coletar(raiz, splits, mapa):
    itens = []
    for split in splits:
        for pasta, indice in mapa.items():
            for caminho in glob.glob(os.path.join(raiz, split, pasta, "*")):
                if os.path.isfile(caminho):
                    itens.append((caminho, indice))
    return itens


def coletar_estufa(raiz):
    """Lê as janelas rotuladas na estufa com a posição de cada uma, que
    impede vazamento entre treino e teste (a mesma posição aparece em
    várias capturas quase idênticas)."""
    itens = []
    for pasta in PASTAS_ESTUFA:
        for caminho in sorted(glob.glob(os.path.join(raiz, pasta, "*.png"))):
            # A chave inclui o enquadramento, não só a célula da grade
            # (ver ml/src/dataset/extrair_janelas.py).
            posicao = chave_posicao(os.path.basename(caminho))
            itens.append((caminho, INDICE[pasta], posicao))
    if not itens:
        raise SystemExit(
            f"Nenhuma janela rotulada em {raiz}. Rode "
            "ml/src/dataset/extrair_janelas.py e rotule antes."
        )
    return itens


def separar_por_sessao(itens, sessao_teste: str):
    """Separa enquadramentos inteiros para teste, e não uma amostra
    aleatória de janelas.

    Como todas as janelas vêm da mesma planta, uma divisão aleatória
    mediria memorização da cena. Reservar enquadramentos inteiros testa o
    desempenho em um enquadramento nunca visto (não em outra planta).
    """
    sessoes = {x.strip() for x in sessao_teste.split(",") if x.strip()}
    treino, teste = [], []
    for caminho, rotulo, posicao in itens:
        destino = teste if posicao.split(":")[0] in sessoes else treino
        destino.append((caminho, rotulo))
    if not teste:
        raise SystemExit(
            f"Nenhuma janela da sessao {sessao_teste}. Confira o nome do "
            "enquadramento (ver chave_posicao)."
        )
    return treino, teste


def separar_validacao_estufa(itens, por_classe, rng):
    """Validação da estufa separada por posição, e não por imagem, para
    não colocar quase-duplicatas nos dois lados."""
    por_posicao = {}
    for caminho, rotulo, posicao in itens:
        por_posicao.setdefault(posicao, []).append((caminho, rotulo))

    # classe da posicao = a mais frequente nela
    classe_da_posicao = {
        p: max({r for _, r in v}, key=lambda r: sum(1 for _, x in v if x == r))
        for p, v in por_posicao.items()
    }
    validacao, treino = [], []
    for indice in sorted(set(classe_da_posicao.values())):
        posicoes = sorted(p for p, r in classe_da_posicao.items() if r == indice)
        ordem = rng.permutation(len(posicoes))
        quantos = min(por_classe, max(1, len(posicoes) // 4))
        for lugar, i in enumerate(ordem):
            destino = validacao if lugar < quantos else treino
            destino.extend(por_posicao[posicoes[i]])
    return validacao, treino


def _ds_cru(itens):
    caminhos = [c for c, _ in itens]
    rotulos = [r for _, r in itens]

    def ler(caminho, rotulo):
        img = tf.image.decode_image(
            tf.io.read_file(caminho), channels=3, expand_animations=False
        )
        img = tf.image.resize(img, TAMANHO, method="bilinear")
        return tf.cast(img, tf.float32), rotulo  # pixels CRUS 0-255

    return tf.data.Dataset.from_tensor_slices((caminhos, rotulos)).map(
        ler, num_parallel_calls=tf.data.AUTOTUNE
    )


def montar_ds(itens, embaralhar):
    ds = _ds_cru(itens)
    if embaralhar:
        ds = ds.shuffle(min(len(itens), 4096), seed=SEMENTE)
    return ds.batch(LOTE).prefetch(tf.data.AUTOTUNE)


def expandir_cabeca(modelo, n_classes):
    """Liga uma camada densa maior ao tensor já existente no grafo,
    copiando as colunas treinadas. A entrada não é recriada: reaproveitar
    camadas em um grafo novo duplicaria nós e entradas."""
    densa_antiga = modelo.get_layer("dense")
    kernel_antigo, bias_antigo = densa_antiga.get_weights()
    antigas = kernel_antigo.shape[1]
    if antigas >= n_classes:
        raise SystemExit(f"O modelo ja tem {antigas} saidas.")

    densa = keras.layers.Dense(n_classes, activation="softmax", name="dense_dominio")
    saida = densa(modelo.get_layer("dropout").output)
    novo = keras.Model(modelo.inputs, saida, name="ecovision_dominio_proprio")
    kernel, bias = densa.get_weights()
    kernel[:, :antigas] = kernel_antigo
    bias[:antigas] = bias_antigo
    densa.set_weights([kernel, bias])
    print(f"cabeca expandida de {antigas} para {n_classes}")
    return novo


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[2])
    parser.add_argument("--laboratorio", required=True)
    parser.add_argument("--estufa", required=True)
    parser.add_argument("--sessao-teste", dest="sessao_teste", default="C,E",
                        help="enquadramentos reservados para TESTE, separados por "
                             "virgula. Nao entram no treino nem na validacao, e "
                             "so sao olhados no fim.")
    parser.add_argument("--saida", default=os.path.join(RAIZ, "models", "modelo_dominio.tflite"))
    argumentos = parser.parse_args()

    tf.random.set_seed(SEMENTE)
    rng = np.random.default_rng(SEMENTE)

    lab = coletar(argumentos.laboratorio, ("train",), PASTA_LAB)
    campo = coletar(PLANTDOC, ("train",), PASTA_CAMPO)
    estufa = coletar_estufa(argumentos.estufa)
    treino_estufa, teste_estufa = separar_por_sessao(estufa, argumentos.sessao_teste)
    # A validação sai do treino; o teste só é avaliado uma vez, no fim.
    _teste = {x.strip() for x in argumentos.sessao_teste.split(",") if x.strip()}
    triplas = [(c, r, p) for (c, r), p in
               zip(treino_estufa, [p for _, _, p in estufa
                                   if p.split(":")[0] not in _teste])]
    val_estufa, treino_estufa = separar_validacao_estufa(
        triplas, VALIDACAO_POR_CLASSE, rng)

    posicoes = len({p for _, _, p in estufa})
    print(f"laboratorio={len(lab)}  campo={len(campo)}  estufa={len(estufa)}")
    print(f"  estufa: {posicoes} posicoes distintas "
          f"({len(estufa) / posicoes:.1f} imagens por posicao)")
    for pasta in PASTAS_ESTUFA:
        n = sum(1 for _, r, _ in estufa if r == INDICE[pasta])
        print(f"    {pasta:<24}{n:>4}")
    print(f"  TESTE reservado: sessao {argumentos.sessao_teste}, "
          f"{len(teste_estufa)} janelas (nunca vistas no treino)")
    print(f"  validacao (tirada do treino): {len(val_estufa)} janelas")

    # Validação só com a estufa: o laboratório, muito maior, dominaria a
    # val_loss e a classe nova não influenciaria a parada antecipada.
    treino = lab + campo + list(treino_estufa)
    rng.shuffle(treino)

    peso_campo = len(lab) / max(1, len(campo))
    peso_estufa = len(lab) / max(1, len(treino_estufa))
    efetiva = np.zeros(len(CLASSES))
    for _, r in lab:
        efetiva[r] += 1.0
    for _, r in campo:
        efetiva[r] += peso_campo
    for _, r in treino_estufa:
        efetiva[r] += peso_estufa
    efetiva[efetiva == 0] = 1.0
    peso = {i: float(efetiva.sum() / (len(CLASSES) * efetiva[i])) for i in range(len(CLASSES))}
    print(f"\npeso campo={peso_campo:.1f}  peso estufa={peso_estufa:.1f}")
    print("class_weight: " + ", ".join(f"{CLASSES[i]}={peso[i]:.2f}" for i in peso))

    modelo = expandir_cabeca(keras.models.load_model(MODELO_BASE), len(CLASSES))
    base = modelo.get_layer("mobilenetv2_1.00_224")
    base.trainable = True
    limite = len(base.layers) - CAMADAS_DESCONGELADAS
    for i, camada in enumerate(base.layers):
        if i < limite or isinstance(camada, keras.layers.BatchNormalization):
            camada.trainable = False

    modelo.compile(
        optimizer=keras.optimizers.Adam(learning_rate=TAXA_APRENDIZADO),
        loss=keras.losses.SparseCategoricalCrossentropy(),
        metrics=["accuracy"],
    )
    modelo.fit(
        montar_ds(treino, True),
        validation_data=montar_ds(val_estufa, False),
        epochs=EPOCAS,
        class_weight=peso,
        callbacks=[keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=PACIENCIA, restore_best_weights=True)],
        verbose=2,
    )

    # O teste so agora, uma vez, com o modelo ja congelado.
    print()
    print("=" * 60)
    print(f"TESTE no enquadramento {argumentos.sessao_teste} (nunca visto)")
    print("=" * 60)
    import collections
    acertos = collections.Counter()
    totais = collections.Counter()
    previstos = collections.Counter()
    for caminho, rotulo in teste_estufa:
        img = tf.image.decode_image(tf.io.read_file(caminho), channels=3,
                                    expand_animations=False)
        img = tf.cast(tf.image.resize(img, TAMANHO, method="bilinear"), tf.float32)
        p = int(modelo.predict(img[None], verbose=0).argmax())
        totais[rotulo] += 1
        previstos[p] += 1
        acertos[rotulo] += int(p == rotulo)
    for i, nome in enumerate(CLASSES):
        if totais[i]:
            print(f"  {nome:<20}{acertos[i]:>3}/{totais[i]:<4}"
                  f"{acertos[i] / totais[i] * 100:>7.1f}%")
    n = sum(totais.values())
    print(f"  {'GERAL':<20}{sum(acertos.values()):>3}/{n:<4}"
          f"{sum(acertos.values()) / max(1, n) * 100:>7.1f}%")
    print("  distribuicao prevista: " +
          str({CLASSES[i]: v for i, v in sorted(previstos.items())}))

    destino = os.path.join(RAIZ, "training", "modelo_dominio_proprio.keras")
    modelo.save(destino)
    print(f"keras salvo: {destino}")

    tflite = tf.lite.TFLiteConverter.from_keras_model(modelo).convert()
    os.makedirs(os.path.dirname(argumentos.saida), exist_ok=True)
    with open(argumentos.saida, "wb") as arquivo:
        arquivo.write(tflite)
    print(f"tflite salvo: {argumentos.saida}  ({len(tflite) / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()
