"""
Mapas de ativação Grad-CAM do modelo em produção, separados por classe.

O Grad-CAM indica as regiões que mais pesaram na decisão: calor sobre o
tecido alterado é evidência de que o modelo aprendeu o sintoma, e calor
sobre o fundo indicaria um atalho. Não é prova de acerto. As janelas de
cada classe são ordenadas por foco em tecido texturado, e não por
confiança, que favorece janelas de fundo ou de fruto.

O preprocess_input da MobileNetV2 faz parte do grafo, mas não aparece em
modelo.layers; a travessia manual precisa aplicá-lo.

Uso:
    python -m ml.src.porta.gradcam_dominio <captura.jpg> <pasta_de_saida>
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parents[3]
MODELO = RAIZ / "ml" / "training" / "modelo_dominio_proprio.keras"
CLASSES = ["septoriose", "pinta_preta", "saudavel", "estresse_foliar"]
ROTULO = {
    "septoriose": "Septoriose",
    "pinta_preta": "Pinta-preta",
    "saudavel": "Saudável",
    "estresse_foliar": "Estresse foliar",
}
POR_CLASSE = 4


def foco_em_tecido(recorte, mapa):
    """Fração do calor sobre tecido texturado (folha), e não sobre
    superfícies lisas (fruto, vaso, fundo), medida pelo gradiente médio
    ponderado pelo calor. Usado só para escolher exemplos."""
    cinza = recorte.mean(axis=2)
    gy, gx = np.gradient(cinza)
    textura = np.hypot(gx, gy)
    peso = mapa / max(mapa.sum(), 1e-6)
    return float((textura * peso).sum())


def gradcam(modelo, entrada, indice):
    """Mapa de ativação para a classe `indice`, na janela `entrada`
    (pixels crus de 0 a 255)."""
    import keras
    import tensorflow as tf

    base = modelo.get_layer("mobilenetv2_1.00_224")
    posteriores = modelo.layers[modelo.layers.index(base) + 1 :]
    lote = tf.convert_to_tensor(entrada[None, ...])
    with tf.GradientTape() as fita:
        x = modelo.layers[1](lote, training=False)  # aumento de dados, inativo
        x = keras.applications.mobilenet_v2.preprocess_input(x)
        mapas = base(x, training=False)
        fita.watch(mapas)
        y = mapas
        for camada in posteriores:
            y = camada(y, training=False)
        alvo = y[:, indice]
    gradientes = fita.gradient(alvo, mapas)
    pesos = tf.reduce_mean(gradientes, axis=(0, 1, 2))
    mapa = tf.maximum(tf.reduce_sum(mapas[0] * pesos, axis=-1), 0)
    maximo = tf.reduce_max(mapa)
    mapa = np.asarray(mapa / maximo if maximo > 0 else mapa)
    return np.asarray(
        Image.fromarray((mapa * 255).astype("uint8")).resize((224, 224), Image.BILINEAR)
    ) / 255.0


def main() -> int:
    import keras

    from ml.src.porta.avaliar import janelas_da_captura

    if len(sys.argv) < 3:
        raise SystemExit(__doc__.strip().splitlines()[-1])
    captura, saida = Path(sys.argv[1]), Path(sys.argv[2])
    saida.mkdir(parents=True, exist_ok=True)

    modelo = keras.models.load_model(MODELO)
    _imagem, recortes, posicoes = janelas_da_captura(captura)
    probabilidades = modelo.predict(np.asarray(recortes, np.float32), verbose=0)

    # Uma linha por classe que o modelo de fato usou nesta captura.
    presentes = [i for i in range(len(CLASSES)) if (probabilidades.argmax(1) == i).any()]
    if not presentes:
        raise SystemExit("Nenhuma classe prevista nesta captura.")

    figura, eixos = plt.subplots(
        len(presentes) * 2, POR_CLASSE,
        figsize=(POR_CLASSE * 3.4, len(presentes) * 7.0),
        squeeze=False,
    )
    for linha, indice in enumerate(presentes):
        desta = np.where(probabilidades.argmax(1) == indice)[0]
        # Ordena por foco em tecido, não por confiança.
        focos = [foco_em_tecido(recortes[j], gradcam(modelo, recortes[j], indice))
                 for j in desta]
        escolhidas = desta[np.argsort(focos)[::-1]][:POR_CLASSE]
        print(f"\n{ROTULO[CLASSES[indice]]}  ({len(desta)} janelas)")
        for coluna in range(POR_CLASSE):
            cima, baixo = eixos[linha * 2][coluna], eixos[linha * 2 + 1][coluna]
            if coluna >= len(escolhidas):
                cima.axis("off"), baixo.axis("off")
                continue
            janela = escolhidas[coluna]
            recorte = recortes[janela]
            mapa = gradcam(modelo, recorte, indice)
            x, y, _lado = posicoes[janela]
            confianca = probabilidades[janela][indice]

            cima.imshow(recorte.astype("uint8"))
            cima.axis("off")
            cima.set_title(
                f"{ROTULO[CLASSES[indice]]}  {confianca * 100:.0f}%", fontsize=11
            )
            baixo.imshow(recorte.astype("uint8"))
            baixo.imshow(mapa, cmap="inferno", alpha=0.55)
            baixo.axis("off")
            baixo.set_title(f"x{x} y{y}", fontsize=9)
            print(f"   x{x:<5}y{y:<5}{confianca * 100:5.1f}%")

    plt.tight_layout()
    destino = saida / f"gradcam_{captura.stem}.png"
    plt.savefig(destino, dpi=96, facecolor="white")
    print(f"\nmapa: {destino}")

    contagem = {
        CLASSES[i]: int((probabilidades.argmax(1) == i).sum())
        for i in range(len(CLASSES))
        if (probabilidades.argmax(1) == i).any()
    }
    print(f"votos nas {len(recortes)} janelas: {contagem}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
