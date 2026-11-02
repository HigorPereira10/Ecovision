"""
ml/src/training/ajuste_dominio_proprio.py

Acrescenta ao modelo as classes rotuladas NA PROPRIA ESTUFA.

POR QUE ESTE SCRIPT EXISTE, E NAO O DO OLID
-------------------------------------------
Medido em 2026-11-01, tres caminhos falharam no mesmo ponto, que e a
distancia entre o dado de treino e esta estufa:

  quarta classe do OLID .......... 83,3% dentro do OLID, ZERO janelas
                                   vencidas nas capturas do dispositivo
  porta de familiaridade ......... recusa fundo, nao recusa folha
                                   estranha (e post-hoc)
  geometria da lesao ............. separa entre fontes (AUC 0,849) e
                                   nao dentro (0,627), e muda com a
                                   distancia da camera

O unico dominio com acesso ilimitado e o proprio, e desde 2026-11-01
ele e consistente: foco fixo em 20 cm, LED estavel, janela de 896 px
levando o foliolo ao modelo com 222 px.

AS CLASSES NOVAS SAO DESCRITIVAS
--------------------------------
`amarelecimento_difuso` e `tecido_seco` dizem o que se ve, nao o que se
supoe. Nao da para afirmar "deficiencia de potassio" de uma foto sem
saber a adubacao, e rotulo visual com nome etiologico e o tipo de coisa
que cai numa pergunta de banca.

ASSIMETRIA DE FONTE QUE PRECISA ESTAR DECLARADA
-----------------------------------------------
`septoriose` e `pinta_preta` vem SO do PlantDoc e do PlantVillage;
`amarelecimento_difuso` e `tecido_seco` vem SO da estufa. `saudavel`
vem dos dois, o que atenua, mas o modelo ainda pode usar a origem para
separar fungo do resto.

Nao da para resolver enquanto a planta nao tiver doenca fungica de
verdade para fotografar. Fica declarado aqui e no texto, e e por isso
que avaliar_dominio_proprio.py mede quantas janelas da estufa caem nas
classes fungicas.

Como rodar:

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

# As TRES primeiras nao mudam de posicao, nunca: a ordem tem que bater
# com _CLASSES_DO_MODELO em cloud/app/core/inference.py. Trocar nao
# quebra nada visivelmente, so passa a mandar fungicida para folha sa.
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
    """Le as janelas rotuladas na estufa, guardando a POSICAO de cada
    uma. A posicao e o que impede vazamento: a mesma posicao da grade
    aparece em varias capturas e as imagens sao quase identicas."""
    itens = []
    for pasta in PASTAS_ESTUFA:
        for caminho in sorted(glob.glob(os.path.join(raiz, pasta, "*.png"))):
            # A chave inclui a SESSAO (o enquadramento), nao so a
            # celula da grade: mover o vaso faz a mesma celula mostrar
            # outras folhas. Ver ml/src/dataset/extrair_janelas.py.
            posicao = chave_posicao(os.path.basename(caminho))
            itens.append((caminho, INDICE[pasta], posicao))
    if not itens:
        raise SystemExit(
            f"Nenhuma janela rotulada em {raiz}. Rode "
            "ml/src/dataset/extrair_janelas.py e rotule antes."
        )
    return itens


def separar_por_sessao(itens, sessao_teste: str):
    """Separa um ENQUADRAMENTO inteiro para teste, e nao uma amostra
    aleatoria de janelas.

    POR QUE ASSIM: todas as janelas vem de UMA planta, num vaso, sob a
    mesma luz. Uma divisao aleatoria, ou mesmo por posicao da grade,
    mediria memorizacao da cena, porque o modelo ja teria visto aquele
    fundo, aquele vaso e aquelas folhas de outro angulo.

    Reservando o enquadramento B inteiro, a pergunta do teste passa a
    ser "funciona num enquadramento que nunca viu". Isso ainda NAO
    prova que funciona em outra planta, e o texto tem que dizer isso.
    Prova que o modelo nao decorou o fundo.

    A sessao B foi escolhida por ser a mais desbalanceada das quatro
    (13 saudaveis e quase nenhum estresse), o que torna o teste mais
    duro: se o modelo aprendeu "enquadramento = classe", ele quebra
    aqui.
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
    """Validacao da estufa separada POR POSICAO, nao por imagem.

    Se a posicao x0672_y0224 for para a validacao, TODAS as capturas
    dela vao junto. Separar por imagem colocaria quase-duplicatas dos
    dois lados e a val_loss mediria memorizacao, nao generalizacao.
    """
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
    """Liga uma densa maior ao tensor que JA existe no grafo, copiando
    as colunas treinadas. Nao recriar a entrada: reaproveitar camadas
    num grafo novo as deixa com dois nos e o modelo com duas entradas de
    mesmo nome, e o erro so aparece ao salvar ou ao montar submodelo
    (ver ajuste_quatro_classes.py)."""
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
    # A validacao sai do TREINO, nunca do teste: o teste so e olhado no
    # fim, uma vez. Usar o teste para parar o treino o transformaria em
    # parte do ajuste, e a metrica final ficaria otimista.
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

    # Validacao: so a estufa. O laboratorio tem 3000 imagens e
    # dominaria a val_loss, que foi o erro que travou o treino do OLID
    # na epoca 2 e deixou a classe nova sem influencia nenhuma na
    # decisao de parar. Aqui a validacao mede o que o treino quer mudar.
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
