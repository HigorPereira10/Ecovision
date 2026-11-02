"""
ml/src/porta/avaliar.py

Avalia uma captura do dispositivo com a PORTA DE FAMILIARIDADE e uma
janela deslizante, em vez de reduzir o quadro inteiro para 224x224.

O PROBLEMA QUE ISTO RESOLVE
---------------------------
A câmera entrega 4608x2592 e o pipeline de produção reduz o quadro
inteiro para 224x224. É uma redução linear de 11,6 vezes no lado menor
e 20,6 no maior, mais o esmagamento de 16:9 para 1:1. As imagens de
treino do PlantDoc reduzem 2,6 vezes na mediana.

Medido em 2026-10-29 sobre 249 imagens rotuladas, simulando distância
de captura (acaso com três classes é 33,3%):

    folha com 224 px na entrada .... 80,7% de acurácia
    folha com 156 px ............... 74,3%
    folha com 112 px ............... 62,7%
    folha com  56 px ............... 47,4%
    folha com  33 px ............... 49,4%

Nas capturas reais do dispositivo o folíolo chega ao modelo com 12 a
31 px, ou seja, dentro da faixa de acaso. Por isso o veredito do
quadro inteiro não é confiável, e por isso ele muda conforme o filtro
de redimensionamento: cinco de doze capturas trocam de diagnóstico só
por trocar NEAREST por BILINEAR, enquanto no PlantDoc a troca é
estatisticamente irrelevante (McNemar p = 1,00 em 249 imagens).

O QUE ESTE MÓDULO FAZ
---------------------
1. Divide a captura em janelas de JANELA_NATIVA pixels nativos.
2. Reduz cada janela para 224x224, o que dá uma redução de cerca de
   4 vezes, próxima do regime de treino.
3. Mede a familiaridade de cada janela (ver referencia.py) e descarta
   as que o modelo não reconhece.
4. Classifica apenas as aprovadas e devolve o mapa.

O RESULTADO NÃO É UM RÓTULO ÚNICO, E ISSO É DE PROPÓSITO
--------------------------------------------------------
Medido na captura de 2026-10-31: o quadro inteiro devolve
"pinta_preta 81,7%" para a planta toda. Com a porta, as 28 janelas
aprovadas se dividem em 12 pinta_preta, 13 saudável e 3 septoriose, e
a separação é espacialmente correta: o saudável cai sobre as folhas
limpas da direita e o restante sobre as folhas secas da esquerda.

A planta é mista. Um rótulo único para a planta inteira é a pergunta
errada, e o sistema atual responde essa pergunta errada com confiança
alta. O mapa é a informação acionável.

LIMITAÇÃO CONHECIDA
-------------------
A porta recusa 100% das janelas de fundo, mas não recusa caule, flor
nem fruto, porque esses são material vegetal parecido com o do treino.
Resolver isso depende de uma classe "outro" no modelo, que por sua vez
depende de dado rotulado que ainda não existe (ver ADR 0011).

USO
---
    python -m ml.src.porta.avaliar <imagem ou pasta> [--mapa saida.png]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import numpy as np
from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parents[3]
REFERENCIA = RAIZ / "ml" / "models" / "referencia_familiaridade.npz"
MODELO_KERAS = RAIZ / "ml" / "training" / "modelo_hibrido_lab_campo.keras"

# Janela de 896 px nativos reduzida para 224 dá redução de 4x, dentro
# do regime em que a acurácia medida fica acima de 70%. Janelas muito
# menores mostram um pedaço de limbo em vez de uma folha e são
# recusadas pela porta: das janelas de 224 px nativos, só 27% passam.
JANELA_NATIVA = 896
PASSO_NATIVO = 448  # sobreposição de metade, para não cortar folha ao meio

# Escala de decodificação do JPEG. Decodificar em metade economiza
# memória sem mudar o resultado, porque a janela é reduzida de
# qualquer forma.
ESCALA = 2

CORES = {
    "septoriose": (255, 170, 0),
    "pinta_preta": (230, 40, 40),
    "saudavel": (40, 190, 90),
}


def carregar_referencia():
    if not REFERENCIA.exists():
        raise SystemExit(
            f"Referência não encontrada em {REFERENCIA}.\n"
            "Gere com: python -m ml.src.porta.referencia"
        )
    dados = np.load(REFERENCIA, allow_pickle=False)
    return (
        dados["referencia"],
        float(dados["limiar"]),
        [str(c) for c in dados["classes"]],
    )


def _ultima_densa(modelo):
    """Acha a camada de classificação pelo TIPO, não pelo nome.

    O nome importa menos do que parece e muda sozinho: ao acrescentar a
    quarta classe, ml/src/training/ajuste_quatro_classes.py liga uma
    densa nova ao grafo, e ela não pode se chamar "dense" porque a
    antiga continua registrada ali. Procurar pelo tipo faz este módulo
    servir aos dois modelos sem edição."""
    import keras

    densas = [c for c in modelo.layers if isinstance(c, keras.layers.Dense)]
    if not densas:
        raise SystemExit(f"Nenhuma camada Dense em {MODELO_KERAS}.")
    return densas[-1]


def carregar_modelo():
    import keras

    modelo = keras.models.load_model(MODELO_KERAS)
    return (
        modelo.get_layer("mobilenetv2_1.00_224"),
        modelo.get_layer("global_average_pooling2d"),
        modelo.get_layer("dropout"),
        _ultima_densa(modelo),
    )


def montar_passo(mobilenet, pooling, dropout, denso):
    """Um passo só devolve vetor e probabilidades juntos, para não
    rodar a rede duas vezes por janela."""
    import keras
    import tensorflow as tf

    preparar = keras.applications.mobilenet_v2.preprocess_input

    def calcular(imagens: list[np.ndarray], lote: int = 8):
        vetores, probabilidades = [], []
        for inicio in range(0, len(imagens), lote):
            bloco = np.asarray(imagens[inicio : inicio + lote], np.float32)
            tensor = preparar(tf.convert_to_tensor(bloco))
            atributos = pooling(mobilenet(tensor, training=False))
            vetores.append(atributos.numpy())
            probabilidades.append(denso(dropout(atributos, training=False)).numpy())
        return np.vstack(vetores), np.vstack(probabilidades)

    return calcular


def janelas_da_captura(caminho: Path):
    """Devolve as janelas já reduzidas para 224 e a posição de cada uma
    em coordenadas da imagem decodificada."""
    imagem = Image.open(caminho)
    imagem.draft("RGB", (imagem.size[0] // ESCALA, imagem.size[1] // ESCALA))
    imagem = imagem.convert("RGB")

    lado = JANELA_NATIVA // ESCALA
    passo = PASSO_NATIVO // ESCALA
    largura, altura = imagem.size
    if lado > min(largura, altura):
        lado = min(largura, altura)
        passo = max(1, lado // 2)

    recortes, posicoes = [], []
    for topo in range(0, altura - lado + 1, passo):
        for esquerda in range(0, largura - lado + 1, passo):
            pedaco = imagem.crop((esquerda, topo, esquerda + lado, topo + lado))
            recortes.append(
                np.asarray(pedaco.resize((224, 224), Image.BILINEAR), np.float32)
            )
            posicoes.append((esquerda, topo, lado))
    return imagem, recortes, posicoes


def avaliar(caminho: Path, calcular, referencia, limiar, classes):
    imagem, recortes, posicoes = janelas_da_captura(caminho)
    if not recortes:
        return None

    vetores, probabilidades = calcular(recortes)
    normalizados = vetores / np.linalg.norm(vetores, axis=1, keepdims=True)
    familiaridade = (normalizados @ referencia.T).max(axis=1)
    vencedoras = probabilidades.argmax(axis=1)
    confiancas = probabilidades.max(axis=1)
    aprovadas = familiaridade >= limiar

    resultado = {
        "arquivo": caminho.name,
        "janelas": len(recortes),
        "aprovadas": int(aprovadas.sum()),
        "limiar": limiar,
        "familiaridade_media_aprovadas": (
            float(familiaridade[aprovadas].mean()) if aprovadas.any() else None
        ),
        "votos": {
            classes[i]: int((vencedoras[aprovadas] == i).sum()) for i in range(3)
        },
        "media_aprovadas": (
            [float(v) for v in probabilidades[aprovadas].mean(axis=0)]
            if aprovadas.any()
            else None
        ),
    }
    detalhe = list(zip(posicoes, familiaridade, vencedoras, confiancas, aprovadas))
    return imagem, resultado, detalhe


def desenhar_mapa(imagem, detalhe, classes, destino: Path, largura_saida=1150):
    mapa = imagem.copy()
    pincel = ImageDraw.Draw(mapa, "RGBA")
    for (esquerda, topo, lado), _fam, vencedora, confianca, aprovada in detalhe:
        caixa = [esquerda, topo, esquerda + lado - 1, topo + lado - 1]
        if aprovada:
            cor = CORES[classes[int(vencedora)]]
            pincel.rectangle(caixa, outline=cor + (255,), width=6)
            pincel.text(
                (esquerda + 12, topo + 12),
                f"{classes[int(vencedora)][:5]} {confianca * 100:.0f}%",
                fill=cor + (255,),
            )
        else:
            # escurecer em vez de apagar: o avaliador precisa poder ver
            # o que foi descartado e julgar se a porta errou
            pincel.rectangle(caixa, fill=(20, 20, 30, 130))
    proporcao = largura_saida / mapa.size[0]
    destino.parent.mkdir(parents=True, exist_ok=True)
    mapa.resize((largura_saida, int(mapa.size[1] * proporcao))).save(destino)


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__.split("\n")[2])
    analisador.add_argument("alvo", type=Path, help="imagem .jpg ou pasta com imagens")
    analisador.add_argument("--mapa", type=Path, default=None, help="PNG do mapa")
    analisador.add_argument("--json", type=Path, default=None, help="resumo em JSON")
    argumentos = analisador.parse_args()

    referencia, limiar, classes = carregar_referencia()
    calcular = montar_passo(*carregar_modelo())

    alvos = (
        sorted(p for p in argumentos.alvo.iterdir() if p.suffix.lower() == ".jpg")
        if argumentos.alvo.is_dir()
        else [argumentos.alvo]
    )
    if not alvos:
        print("Nenhuma imagem encontrada.", file=sys.stderr)
        return 1

    print(f"limiar de familiaridade: {limiar:.3f}\n")
    resumos = []
    for caminho in alvos:
        saida = avaliar(caminho, calcular, referencia, limiar, classes)
        if saida is None:
            print(f"{caminho.name}: sem janela avaliável")
            continue
        imagem, resumo, detalhe = saida
        resumos.append(resumo)
        votos = resumo["votos"]
        media = resumo["media_aprovadas"]
        rotulo = classes[int(np.argmax(media))] if media else "indeterminado"
        print(
            f"{caminho.name:<28}{resumo['aprovadas']:3d}/{resumo['janelas']:<3d} aprovadas"
            f"   votos {votos}   agregado {rotulo}"
        )
        if argumentos.mapa and len(alvos) == 1:
            desenhar_mapa(imagem, detalhe, classes, argumentos.mapa)
            print(f"mapa: {argumentos.mapa}")

    if argumentos.json:
        argumentos.json.parent.mkdir(parents=True, exist_ok=True)
        argumentos.json.write_text(
            json.dumps(resumos, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"resumo: {argumentos.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
