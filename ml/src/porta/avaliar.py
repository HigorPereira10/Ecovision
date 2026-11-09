"""
Avalia uma captura do dispositivo por janelas, com verificação de
familiaridade, e gera o mapa de classes por janela.

Reduzir o quadro inteiro de 4608 × 2592 para 224 × 224 deixa o folíolo
com 12 a 31 pixels, faixa em que a acurácia fica perto do acaso (80,7%
com a folha a 224 pixels e 47,4% a 56 pixels, em 249 imagens rotuladas).
Este módulo divide a captura em janelas de JANELA_NATIVA pixels, reduz
cada uma para 224 × 224 (redução de cerca de 4 vezes, próxima do treino),
descarta as janelas sem familiaridade suficiente (ver referencia.py) e
classifica as restantes.

Limitação: a verificação recusa janelas de fundo, mas não caule, flor ou
fruto, que se parecem com o material de treino.

Uso:
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

# Janela de 896 pixels reduzida para 224: redução de 4 vezes, no regime em
# que a acurácia medida fica acima de 70%.
JANELA_NATIVA = 896
PASSO_NATIVO = 448  # sobreposição de metade, para não cortar folha ao meio

# Decodificação do JPEG em metade da resolução, sem alterar o resultado.
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
    """Localiza a camada de classificação pelo tipo, e não pelo nome, para
    servir aos modelos de três e de quatro classes."""
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
