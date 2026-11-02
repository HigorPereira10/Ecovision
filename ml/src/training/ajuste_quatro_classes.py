"""
ml/src/training/ajuste_quatro_classes.py

Acrescenta a classe `deficiencia_nutricional` ao modelo de producao,
partindo do artefato de tres classes gerado por ajuste_dois_dominios.py.

POR QUE ESTA CLASSE E OBRIGATORIA, E NAO UMA MELHORIA
-----------------------------------------------------
Medido em 2026-11-01, no ecovision-pi-01: quatro capturas da mesma
planta, com amarelamento internerval generalizado, sairam como
`pinta_preta` com ate 77,8% de confianca. A planta nao tem pinta preta.

A primeira hipotese foi que o softmax estava inflando a confianca por
normalizacao, e que trocar por sigmoides independentes resolveria. Foi
medido e NAO e isso:

    logit maximo, mediana     classes conhecidas (PlantDoc)   1,89
                              nossa planta (janelas da porta) 1,70
    janelas nossas acima do percentil 5 das conhecidas:        100%

O modelo esta genuinamente confiante. Ele nao esta errado sobre o que
VE, que e tecido foliar danificado; esta errado ao NOMEAR, porque os
unicos nomes que tem sao nomes de doenca. Problema de nome nao se
corrige na camada de saida, so com rotulo novo. Por isso este script
existe, e por isso a troca de ativacao foi descartada.

A porta de familiaridade tambem nao resolve: ela e post-hoc, e o
benchmark de OOD em patologia vegetal (arXiv 2605.08618) mede que
metodos post-hoc desabam em OOD PROXIMO (AUROC 0,482 para softmax,
0,516 para energia post-hoc). Folha de tomate com deficiencia e o OOD
mais proximo que existe.

A ARMADILHA CENTRAL DESTE TREINO, E COMO ELA E DESARMADA
--------------------------------------------------------
A classe nova vem SO do OLID I, enquanto as outras tres vem do
PlantVillage e do PlantDoc. Isso deixa o modelo aprender "imagem com
cara de OLID = deficiencia", que e atalho pela origem, nao
aprendizado do sintoma. O treino fecharia com metrica alta e o modelo
seria inutil em campo.

A defesa: o OLID tem 236 imagens de tomate SAUDAVEL, e elas entram na
classe `saudavel`. Com o OLID presente em DUAS classes, a origem deixa
de separar os rotulos e para de servir de atalho.

Isto nao e opcional. Sem as saudaveis do OLID, nao rode este script.

ORDEM DAS CLASSES: NAO MEXER
----------------------------
A classe nova entra no INDICE 3, depois das tres existentes. A ordem
tem que continuar batendo com _CLASSES_DO_MODELO em
cloud/app/core/inference.py. Trocar a ordem nao quebra nada de forma
visivel: o modelo carrega, a API sobe, e o produtor passa a receber
recomendacao de fungicida para folha sa. Ja aconteceu uma vez neste
projeto (ver o comentario de _CATALOGO_AGRONOMICO).

A CABECA E EXPANDIDA, NAO SUBSTITUIDA
-------------------------------------
A camada densa sai de 3 para 4 unidades, mas as tres colunas ja
treinadas sao COPIADAS para a nova. So a quarta comeca aleatoria.
Jogar a cabeca fora obrigaria a reaprender do zero o que custou o
ajuste de dois dominios.

DADOS (nenhum versionado, ml/data/ inteiro esta no .gitignore)
--------------------------------------------------------------
- Laboratorio: PlantVillage tomate, 3 classes, 1000 treino + 100 teste
  cada. Recorte publico, SEM licenca declarada no espelho usado; citar
  o PlantVillage original no texto do TCC.
- Campo: ml/data/plantdoc_tomate/, 3 classes, 249 treino.
- Deficiencia e saudavel extra: OLID I (Zenodo 8105154), CC BY 4.0,
  rotulado por painel de especialistas, 3024x3024, campo real.
  Tomate: K=36, N=47, N_K=40 (total 123) e healthy=236.

O OLID NAO TEM DIVISAO train/test. Este script faz a divisao com
semente fixa e GRAVA a lista em ml/data/olid_divisao.csv, porque a
divisao e a parte insubstituivel: o conjunto e publico, a nossa
divisao nao.

Como rodar:

    python ml/src/training/ajuste_quatro_classes.py \\
        --laboratorio ml/data/plantvillage_tomate \\
        --olid ml/data/olid_i_tomate

    python ml/src/training/ajuste_quatro_classes.py --listar-olid <pasta>
"""

import argparse
import csv
import glob
import os

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import numpy as np
import tensorflow as tf
from tensorflow import keras

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELO_TRES_CLASSES = os.path.join(RAIZ, "training", "modelo_hibrido_lab_campo.keras")
PLANTDOC = os.path.join(RAIZ, "data", "plantdoc_tomate")
DIVISAO_OLID = os.path.join(RAIZ, "data", "olid_divisao.csv")

# Indice 3 e novo. Os tres primeiros NAO podem mudar de posicao.
CLASSES = ["septoriose", "pinta_preta", "saudavel", "deficiencia_nutricional"]
INDICE_SAUDAVEL = 2
INDICE_DEFICIENCIA = 3

PASTA_CAMPO = {"distrator_septoria": 0, "pinta_preta": 1, "saudavel": 2}
PASTA_LAB = {"mancha_septoria": 0, "pinta_preta": 1, "folhas_saudaveis": 2}

# Trechos que identificam a pasta do OLID, em minusculas e sem depender
# do nome exato, que varia entre o zip e a planilha de classes.
MARCAS_DEFICIENCIA = ("deficiency", "__k", "__n", "_n_k", "nutrition")
MARCAS_SAUDAVEL = ("healthy",)

TAMANHO = (224, 224)
SEMENTE = 42
EPOCAS = 25
LOTE = 16
TAXA_APRENDIZADO = 1e-5
CAMADAS_DESCONGELADAS = 30
FRACAO_TESTE_OLID = 0.2

# Imagens por classe na validação. Balanceada de propósito, ver
# separar_validacao. Com a deficiência tendo pouco menos de 100 imagens
# de treino, 15 por classe é o que dá para tirar sem esvaziar a classe.
VALIDACAO_POR_CLASSE = 15

# Paciência maior que a do ajuste de dois domínios (3): a validação
# balanceada é pequena, logo mais ruidosa, e parar no primeiro soluço
# foi exatamente o que estragou a primeira rodada.
PACIENCIA = 6
EXTENSOES = (".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG")


def _imagens_em(pasta: str) -> list[str]:
    achados: list[str] = []
    for extensao in EXTENSOES:
        achados.extend(glob.glob(os.path.join(pasta, "**", "*" + extensao), recursive=True))
    return sorted(set(achados))


def listar_olid(raiz: str) -> None:
    """Imprime a arvore do OLID com contagem, para conferir os nomes das
    pastas antes de treinar."""
    print(f"conteudo de {raiz}:")
    for atual, _subpastas, _arquivos in sorted(os.walk(raiz)):
        n = len([a for a in os.listdir(atual)
                 if a.endswith(EXTENSOES) and os.path.isfile(os.path.join(atual, a))])
        if n:
            print(f"  {os.path.relpath(atual, raiz):<50}{n:>5} imagens")


def coletar(raiz: str, splits, mapa: dict[str, int]) -> list[tuple[str, int]]:
    itens = []
    for split in splits:
        for pasta, indice in mapa.items():
            for caminho in glob.glob(os.path.join(raiz, split, pasta, "*")):
                if os.path.isfile(caminho):
                    itens.append((caminho, indice))
    return itens


def coletar_olid(raiz: str) -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
    """Separa o OLID em (deficiencia, saudavel), varrendo as pastas pelo
    nome. Levanta erro se qualquer um dos dois vier vazio: sem as
    saudaveis a origem vira atalho, e e melhor falhar do que treinar um
    modelo que mede bem e nao serve (ver a armadilha central no topo)."""
    deficiencia: list[tuple[str, int]] = []
    saudavel: list[tuple[str, int]] = []

    for atual, _sub, _arqs in os.walk(raiz):
        nome = os.path.basename(atual).lower()
        imagens = [a for a in _imagens_em(atual) if os.path.dirname(a) == atual]
        if not imagens:
            continue
        if any(marca in nome for marca in MARCAS_SAUDAVEL):
            saudavel.extend((caminho, INDICE_SAUDAVEL) for caminho in imagens)
        elif any(marca in nome for marca in MARCAS_DEFICIENCIA):
            deficiencia.extend((caminho, INDICE_DEFICIENCIA) for caminho in imagens)

    if not deficiencia:
        raise SystemExit(
            "Nenhuma imagem de deficiencia encontrada no OLID. Rode com "
            "--listar-olid para ver os nomes das pastas e ajuste "
            "MARCAS_DEFICIENCIA."
        )
    if not saudavel:
        raise SystemExit(
            "Nenhuma imagem SAUDAVEL do OLID encontrada. Treinar assim faria "
            "o modelo aprender a origem da imagem em vez do sintoma (ver a "
            "armadilha central no topo deste arquivo). Abortando de proposito."
        )
    return deficiencia, saudavel


def dividir_olid(itens: list[tuple[str, int]], rng) -> tuple[list, list]:
    """Divide por classe, com semente fixa, e grava a divisao em disco."""
    treino, teste = [], []
    for indice in sorted({r for _, r in itens}):
        da_classe = sorted(c for c, r in itens if r == indice)
        ordem = rng.permutation(len(da_classe))
        corte = max(1, int(len(da_classe) * FRACAO_TESTE_OLID))
        for posicao, i in enumerate(ordem):
            destino = teste if posicao < corte else treino
            destino.append((da_classe[i], indice))

    os.makedirs(os.path.dirname(DIVISAO_OLID), exist_ok=True)
    with open(DIVISAO_OLID, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["caminho", "classe_indice", "classe", "split"])
        for conjunto, rotulo in ((treino, "train"), (teste, "test")):
            for caminho, indice in conjunto:
                escritor.writerow(
                    [os.path.relpath(caminho, RAIZ), indice, CLASSES[indice], rotulo]
                )
    print(f"divisao do OLID gravada em {os.path.relpath(DIVISAO_OLID, RAIZ)}")
    return treino, teste


def _ds_cru(itens, recortar: bool):
    """Um conjunto SEM lote, para poder concatenar grupos com políticas
    de recorte diferentes antes de embaralhar tudo junto.

    POR QUE O RECORTE EXISTE, E SÓ PARA O OLID: as imagens do OLID são
    uma folha ISOLADA preenchendo 3024x3024. A captura do dispositivo,
    depois da janela deslizante, mostra um PEDAÇO de folha junto de
    caule e vizinhança. São apresentações diferentes do mesmo sintoma, e
    medido na primeira rodada deste treino a classe nova não atravessou
    essa diferença: acertou 37,5% dentro do OLID e NUNCA venceu em
    nenhuma das 36 janelas da nossa planta.

    O recorte aleatório faz a classe ver folha parcial, em escalas
    variadas, que é o que ela vai encontrar em operação.
    """
    caminhos = [c for c, _ in itens]
    rotulos = [r for _, r in itens]

    def ler(caminho, rotulo):
        img = tf.image.decode_image(
            tf.io.read_file(caminho), channels=3, expand_animations=False
        )
        if recortar:
            lado = tf.shape(img)[0:2]
            menor = tf.cast(tf.reduce_min(lado), tf.float32)
            fracao = tf.random.uniform([], 0.45, 1.0)
            corte = tf.cast(menor * fracao, tf.int32)
            img = tf.image.random_crop(img, [corte, corte, 3])
        img = tf.image.resize(img, TAMANHO, method="bilinear")
        return tf.cast(img, tf.float32), rotulo  # pixels CRUS 0-255

    return tf.data.Dataset.from_tensor_slices((caminhos, rotulos)).map(
        ler, num_parallel_calls=tf.data.AUTOTUNE
    )


def montar_ds(itens, embaralhar: bool):
    """Monta o conjunto a partir de triplas (caminho, rotulo, recortar),
    separando quem leva recorte aleatório de quem não leva."""
    grupos = (
        ([(c, r) for c, r, corta in itens if not corta], False),
        ([(c, r) for c, r, corta in itens if corta], True),
    )
    partes = [_ds_cru(grupo, recortar) for grupo, recortar in grupos if grupo]
    if not partes:
        raise SystemExit("Nenhum item para montar o conjunto.")
    ds = partes[0]
    for parte in partes[1:]:
        ds = ds.concatenate(parte)
    if embaralhar:
        ds = ds.shuffle(min(len(itens), 4096), seed=SEMENTE)
    return ds.batch(LOTE).prefetch(tf.data.AUTOTUNE)


def separar_validacao(itens, por_classe: int, rng):
    """Tira do treino um conjunto de validação BALANCEADO, com o mesmo
    número de imagens por classe.

    POR QUE BALANCEADO: na primeira rodada a validação saiu de um
    embaralhamento do conjunto inteiro, e ficou 85% laboratório. A
    parada antecipada passou a seguir a val_loss do laboratório, que já
    estava saturada, e cortou o treino na época 2. A classe nova, que é
    o motivo deste script existir, nunca entrou na decisão de parar.

    Validação balanceada é menor e mais ruidosa, e por isso a paciência
    da parada antecipada sobe junto. É troca consciente: melhor um sinal
    ruidoso do que um sinal preciso sobre a coisa errada.
    """
    validacao, treino = [], []
    for indice in sorted({item[1] for item in itens}):
        da_classe = [item for item in itens if item[1] == indice]
        ordem = rng.permutation(len(da_classe))
        quantos = min(por_classe, max(1, len(da_classe) // 5))
        for posicao, i in enumerate(ordem):
            (validacao if posicao < quantos else treino).append(da_classe[i])
    return validacao, treino


def expandir_cabeca(modelo, n_classes: int):
    """Troca a densa de 3 por uma de `n_classes`, COPIANDO as colunas ja
    treinadas. So a coluna nova comeca aleatoria.

    COMO, E POR QUE ASSIM: a densa nova e ligada ao tensor que JA existe
    no grafo (a saida do dropout), e o modelo resultante usa a MESMA
    entrada do original. Com isso entra exatamente um no novo no grafo.

    A tentativa obvia, criar um keras.Input novo e rechamar
    data_augmentation, mobilenet, pooling e dropout sobre ele, parece
    equivalente e nao e: as camadas passam a ter dois nos de entrada, um
    em cada grafo, e o modelo fica com duas entradas registradas com o
    mesmo nome. O sintoma aparece tarde e longe daqui, ao salvar ou ao
    montar submodelo por travessia, que e o que ml/src/porta/avaliar.py
    faz (`ValueError: The name "input_layer_1" is used 2 times`).

    Como nada upstream e reconstruido, o preprocess_input que mora
    dentro do MobileNet aninhado continua no lugar (ver
    ml/models/README.md, quarta regra)."""
    densa_antiga = modelo.get_layer("dense")
    kernel_antigo, bias_antigo = densa_antiga.get_weights()
    unidades_antigas = kernel_antigo.shape[1]
    if unidades_antigas >= n_classes:
        raise SystemExit(
            f"O modelo ja tem {unidades_antigas} saidas; nada a expandir."
        )

    densa_nova = keras.layers.Dense(n_classes, activation="softmax", name="dense_4c")
    saida = densa_nova(modelo.get_layer("dropout").output)
    novo = keras.Model(modelo.inputs, saida, name="ecovision_quatro_classes")

    kernel, bias = densa_nova.get_weights()
    kernel[:, :unidades_antigas] = kernel_antigo
    bias[:unidades_antigas] = bias_antigo
    densa_nova.set_weights([kernel, bias])
    print(f"cabeca expandida de {unidades_antigas} para {n_classes} "
          f"(as {unidades_antigas} primeiras colunas foram preservadas)")
    return novo


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[2])
    parser.add_argument("--laboratorio", help="PlantVillage, com train/ e test/")
    parser.add_argument("--olid", help="OLID I de tomate, ja descompactado")
    parser.add_argument("--listar-olid", dest="listar", help="so lista a arvore e sai")
    parser.add_argument("--saida", default=os.path.join(RAIZ, "models", "modelo_4c.tflite"))
    argumentos = parser.parse_args()

    if argumentos.listar:
        listar_olid(argumentos.listar)
        return
    if not argumentos.laboratorio or not argumentos.olid:
        raise SystemExit("--laboratorio e --olid sao obrigatorios para treinar.")

    tf.random.set_seed(SEMENTE)
    rng = np.random.default_rng(SEMENTE)

    lab = coletar(argumentos.laboratorio, ("train",), PASTA_LAB)
    campo = coletar(PLANTDOC, ("train",), PASTA_CAMPO)
    deficiencia, saudavel_olid = coletar_olid(argumentos.olid)
    olid_treino, olid_teste = dividir_olid(deficiencia + saudavel_olid, rng)

    if not lab or not campo:
        raise SystemExit("Nao encontrei imagens de laboratorio ou de campo.")

    print(f"laboratorio={len(lab)}  campo={len(campo)}  "
          f"olid_treino={len(olid_treino)}  olid_teste={len(olid_teste)}")
    print(f"  deficiencia (OLID) ....... {len(deficiencia)}")
    print(f"  saudavel extra (OLID) .... {len(saudavel_olid)}  <- quebra o atalho de origem")

    # A tripla carrega se aquela imagem leva recorte aleatório. Só o
    # OLID leva, porque só ele é folha isolada preenchendo o quadro
    # (ver _ds_cru).
    todos = (
        [(caminho, rotulo, False) for caminho, rotulo in lab + campo]
        + [(caminho, rotulo, True) for caminho, rotulo in olid_treino]
    )
    validacao, treino = separar_validacao(todos, VALIDACAO_POR_CLASSE, rng)
    rng.shuffle(treino)

    contagem_val = {CLASSES[i]: sum(1 for _, r, _ in validacao if r == i) for i in range(len(CLASSES))}
    print(f"validacao balanceada ({len(validacao)} imagens): {contagem_val}")

    # Peso por dominio: ha milhares de fotos de laboratorio contra
    # centenas de campo e pouco mais de cem de deficiencia. Sem
    # compensar, a classe nova vira ruido estatistico e o ajuste nao
    # muda nada. Mesma aproximacao de ajuste_dois_dominios.py: o Keras
    # so aceita peso por CLASSE, entao o peso de dominio entra embutido
    # na contagem efetiva.
    peso_campo = len(lab) / max(1, len(campo))
    peso_olid = len(lab) / max(1, len(olid_treino))
    efetiva = np.zeros(len(CLASSES))
    for _, r in lab:
        efetiva[r] += 1.0
    for _, r in campo:
        efetiva[r] += peso_campo
    for _, r in olid_treino:
        efetiva[r] += peso_olid
    peso = {i: float(efetiva.sum() / (len(CLASSES) * efetiva[i])) for i in range(len(CLASSES))}
    print(f"peso campo={peso_campo:.1f}  peso olid={peso_olid:.1f}")
    print("class_weight: " + ", ".join(f"{CLASSES[i]}={peso[i]:.2f}" for i in peso))

    modelo = expandir_cabeca(keras.models.load_model(MODELO_TRES_CLASSES), len(CLASSES))

    base = modelo.get_layer("mobilenetv2_1.00_224")
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
        validation_data=montar_ds(validacao, False),
        epochs=EPOCAS,
        class_weight=peso,
        callbacks=[keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=PACIENCIA, restore_best_weights=True)],
        verbose=2,
    )

    destino_keras = os.path.join(RAIZ, "training", "modelo_quatro_classes.keras")
    modelo.save(destino_keras)
    print(f"keras salvo: {destino_keras}")

    # SEM quantizacao, pelo mesmo motivo de ajuste_dois_dominios.py: no
    # baseline a versao quantizada inverteu 2 de 7 predicoes para
    # economizar 6 MB.
    tflite = tf.lite.TFLiteConverter.from_keras_model(modelo).convert()
    os.makedirs(os.path.dirname(argumentos.saida), exist_ok=True)
    with open(argumentos.saida, "wb") as arquivo:
        arquivo.write(tflite)
    print(f"tflite salvo: {argumentos.saida}  ({len(tflite) / 1024 / 1024:.2f} MB)")
    print("\nLEMBRETE: atualizar _CLASSES_DO_MODELO em "
          "cloud/app/core/inference.py para as 4 classes, na mesma ordem.")


if __name__ == "__main__":
    main()
