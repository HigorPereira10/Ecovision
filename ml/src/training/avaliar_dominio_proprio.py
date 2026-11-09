"""
Avalia o modelo em produção sobre as janelas rotuladas no domínio próprio
e gera as figuras correspondentes em docs/figuras/modelo/.

O conjunto de teste é o enquadramento F inteiro, que não entrou no treino
(a divisão é por enquadramento porque janelas da mesma captura se
sobrepõem): 18 janelas úteis, 10 de estresse foliar e 8 sadias, com
baseline trivial de 55,6%.

A matriz de confusão é retangular: as linhas são as duas classes
rotuladas neste domínio, e as colunas, as quatro que o modelo pode
responder, o que mostra quantas janelas sem doença foram chamadas de
doença. O modelo de três classes é avaliado nas mesmas janelas para
mostrar para onde ele envia as janelas de estresse.

Uso (de dentro de ml/):
    python -m src.training.avaliar_dominio_proprio

As métricas são gravadas em ml/models/metricas_modelo_dominio.json.
"""

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from matplotlib.patches import Patch
from PIL import Image

RAIZ = Path(__file__).resolve().parents[2]
ROTULADO = RAIZ / "data" / "estufa_rotulada"
FIGURAS = RAIZ.parent / "docs" / "figuras" / "modelo"

MODELO_ATUAL = RAIZ / "models" / "modelo_dominio.tflite"
MODELO_ANTIGO = RAIZ / "models" / "modelo.tflite"

# Ordem das saídas, igual a _CLASSES_DO_MODELO em cloud/app/core/inference.py.
CLASSES_4 = ["septoriose", "pinta_preta", "saudavel", "estresse_foliar"]
CLASSES_3 = ["septoriose", "pinta_preta", "saudavel"]

ENQUADRAMENTO_TESTE = "posF.jpg"
TAMANHO_ENTRADA = (224, 224)

ROTULO_BONITO = {
    "septoriose": "Septoriose",
    "pinta_preta": "Pinta-preta",
    "saudavel": "Saudável",
    "estresse_foliar": "Estresse foliar",
}

# Mesma paleta das figuras existentes: azul para intensidade nas
# matrizes, azul e laranja para comparar duas series.
AZUL = "#1f4e79"
AZUL_CLARO = "#c6dbef"
LARANJA = "#d9772e"
CINZA = "#6b7566"
FUNDO = "#fbfbf9"


# --------------------------------------------------------------------
# dados


def carregar_rotulos() -> list[dict]:
    """Junta rotulos.csv com manifesto.csv, que tem a captura de origem."""
    manifesto = {
        l["arquivo"]: l
        for l in csv.DictReader(open(ROTULADO / "manifesto.csv", encoding="utf-8"))
    }
    linhas = []
    for l in csv.DictReader(open(ROTULADO / "rotulos.csv", encoding="utf-8")):
        if l["classe"] == "descartar":
            continue
        m = manifesto.get(l["arquivo"])
        if m is None:
            raise RuntimeError(
                f"{l['arquivo']} esta em rotulos.csv e nao em manifesto.csv. "
                "Os dois tem que ser versionados juntos."
            )
        linhas.append({
            "arquivo": l["arquivo"],
            "classe": l["classe"],
            "captura": m["captura"],
            "caminho": ROTULADO / l["classe"] / l["arquivo"],
        })
    return linhas


def preprocessar(caminho: Path) -> np.ndarray:
    """Mesmo pré-processamento de cloud/app/core/inference.py: RGB,
    vizinho mais próximo, pixels de 0 a 255."""
    imagem = Image.open(caminho).convert("RGB")
    imagem = imagem.resize(TAMANHO_ENTRADA, Image.Resampling.NEAREST)
    return np.expand_dims(np.asarray(imagem, dtype=np.float32), axis=0)


def prever(caminho_modelo: Path, amostras: list[dict], classes: list[str]) -> list[str]:
    interp = tf.lite.Interpreter(model_path=str(caminho_modelo))
    interp.allocate_tensors()
    entrada = interp.get_input_details()[0]
    saida = interp.get_output_details()[0]

    n_saidas = int(saida["shape"][-1])
    if n_saidas != len(classes):
        raise RuntimeError(
            f"{caminho_modelo.name} tem {n_saidas} saidas e a lista de classes "
            f"tem {len(classes)}. Nao da para rotular as predicoes."
        )

    previstas = []
    for a in amostras:
        interp.set_tensor(entrada["index"], preprocessar(a["caminho"]))
        interp.invoke()
        probs = interp.get_tensor(saida["index"])[0]
        previstas.append(classes[int(np.argmax(probs))])
    return previstas


# --------------------------------------------------------------------
# figuras


def _titular(fig, titulo: str, subtitulo: str):
    """Não desenha título nem subtítulo: a legenda fica no documento.
    Os argumentos registram a legenda sugerida de cada figura."""
    return


def _pt(x: float, casas: int = 1) -> str:
    """Numero com virgula decimal, que e o separador em portugues."""
    return f"{x:.{casas}f}".replace(".", ",")


def _salvar(fig, nome: str):
    FIGURAS.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        destino = FIGURAS / f"{nome}.{ext}"
        fig.savefig(destino, dpi=200, bbox_inches="tight", facecolor=FUNDO)
    plt.close(fig)
    print(f"  {nome}.png e .svg")


def figura_matriz(amostras, previstas, nome, titulo, subtitulo):
    """Matriz linhas = classes verdadeiras, colunas = as 4 possiveis."""
    verdadeiras = sorted({a["classe"] for a in amostras})
    matriz = np.zeros((len(verdadeiras), len(CLASSES_4)), dtype=int)
    for a, p in zip(amostras, previstas):
        matriz[verdadeiras.index(a["classe"]), CLASSES_4.index(p)] += 1

    fig, ax = plt.subplots(figsize=(8.2, 1.3 + 1.5 * len(verdadeiras)), facecolor=FUNDO)
    maximo = matriz.max() or 1
    ax.imshow(matriz, cmap="Blues", vmin=0, vmax=maximo, aspect="auto")

    for i in range(len(verdadeiras)):
        total_linha = matriz[i].sum() or 1
        for j in range(len(CLASSES_4)):
            n = matriz[i, j]
            cor = "white" if n > maximo * 0.55 else "#1a1a1a"
            ax.text(j, i - 0.12, str(n), ha="center", va="center",
                    fontsize=19, fontweight="bold", color=cor)
            ax.text(j, i + 0.22, f"{n / total_linha * 100:.0f}%", ha="center",
                    va="center", fontsize=11, color=cor)

    ax.set_xticks(range(len(CLASSES_4)))
    ax.set_xticklabels([ROTULO_BONITO[c] for c in CLASSES_4], fontsize=11)
    ax.set_yticks(range(len(verdadeiras)))
    ax.set_yticklabels([ROTULO_BONITO[c] for c in verdadeiras], fontsize=11)
    ax.set_xlabel("Classe prevista pelo modelo", fontsize=11, labelpad=10)
    ax.set_ylabel("Classe verdadeira", fontsize=11, labelpad=10)
    for lado in ("top", "right", "left", "bottom"):
        ax.spines[lado].set_visible(False)
    ax.tick_params(length=0)

    _titular(fig, titulo, subtitulo)
    _salvar(fig, nome)


def figura_comparacao(amostras, prev_antigo, prev_atual, nome):
    """Para onde cada modelo manda as mesmas 18 janelas."""
    def distribuicao(previstas):
        c = Counter(previstas)
        return [c.get(k, 0) for k in CLASSES_4]

    antigo, atual = distribuicao(prev_antigo), distribuicao(prev_atual)
    x = np.arange(len(CLASSES_4))
    largura = 0.38

    fig, ax = plt.subplots(figsize=(8.6, 4.6), facecolor=FUNDO)
    ax.bar(x - largura / 2, antigo, largura, label="Modelo de 3 classes",
           color=LARANJA, edgecolor="none")
    ax.bar(x + largura / 2, atual, largura, label="Modelo em produção (4 classes)",
           color=AZUL, edgecolor="none")

    for xi, (a, b) in enumerate(zip(antigo, atual)):
        if a:
            ax.text(xi - largura / 2, a + 0.25, str(a), ha="center", fontsize=11,
                    fontweight="bold", color=LARANJA)
        if b:
            ax.text(xi + largura / 2, b + 0.25, str(b), ha="center", fontsize=11,
                    fontweight="bold", color=AZUL)

    ax.set_xticks(x)
    ax.set_xticklabels([ROTULO_BONITO[c] for c in CLASSES_4], fontsize=11)
    ax.set_ylabel("Janelas classificadas", fontsize=11)
    # Folga de 12% para o rótulo numérico acima da barra mais alta.
    ax.set_ylim(0, max(max(antigo), max(atual)) * 1.12)
    ax.legend(frameon=False, fontsize=10.5, loc="lower left",
              bbox_to_anchor=(0, 1.0), ncol=2, borderaxespad=0.6)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.spines["left"].set_color(CINZA)
    ax.spines["bottom"].set_color(CINZA)
    ax.grid(axis="y", color="#e4e4dc", linewidth=0.8)
    ax.set_axisbelow(True)

    n_est = sum(1 for a in amostras if a["classe"] == "estresse_foliar")
    n_sau = len(amostras) - n_est
    _titular(
        fig, "Para onde cada modelo manda as mesmas janelas",
        f"Enquadramento F retido, {len(amostras)} janelas: {n_est} de estresse foliar "
        f"e {n_sau} de folha sadia.\nO modelo de 3 classes não tem a saída de "
        "estresse, então distribui essas janelas entre as doenças.")
    _salvar(fig, nome)


def figura_distribuicao(todas, nome):
    """Quantas janelas rotuladas por classe e por enquadramento."""
    capturas = sorted({a["captura"] for a in todas})
    classes = ["estresse_foliar", "saudavel"]
    cores = {"estresse_foliar": LARANJA, "saudavel": AZUL}

    contagem = defaultdict(Counter)
    for a in todas:
        contagem[a["captura"]][a["classe"]] += 1

    fig, ax = plt.subplots(figsize=(9.2, 4.8), facecolor=FUNDO)
    base = np.zeros(len(capturas))
    for c in classes:
        valores = np.array([contagem[cap].get(c, 0) for cap in capturas], dtype=float)
        ax.bar(range(len(capturas)), valores, 0.62, bottom=base,
               color=cores[c], edgecolor="none")
        for i, (v, b) in enumerate(zip(valores, base)):
            if v:
                ax.text(i, b + v / 2, int(v), ha="center", va="center",
                        fontsize=10.5, fontweight="bold", color="white")
        base += valores

    # Os nomes de arquivo das capturas trazem a resposta do modelo antigo
    # ("diag141-septoriose-55pct"); na figura, só o identificador é exibido.
    rotulos_x = [
        cap.replace(".jpg", "").split("-")[0]
           .replace("pos", "Enquadr. ")
           .replace("diag", "Diag. ")
        for cap in capturas
    ]
    ax.set_xticks(range(len(capturas)))
    ax.set_xticklabels(rotulos_x, fontsize=9)
    ax.set_ylabel("Janelas rotuladas", fontsize=11)
    ax.legend(handles=[Patch(color=cores[c], label=ROTULO_BONITO[c]) for c in classes],
              frameon=False, fontsize=10.5, loc="lower left",
              bbox_to_anchor=(0, 1.0), ncol=2, borderaxespad=0.6)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.spines["left"].set_color(CINZA)
    ax.spines["bottom"].set_color(CINZA)
    ax.grid(axis="y", color="#e4e4dc", linewidth=0.8)
    ax.set_axisbelow(True)

    # marca o enquadramento retido
    if ENQUADRAMENTO_TESTE in capturas:
        i = capturas.index(ENQUADRAMENTO_TESTE)
        ax.annotate("retido para teste", xy=(i, base[i]), xytext=(i, base[i] + 4.5),
                    ha="center", fontsize=10, color=CINZA,
                    arrowprops=dict(arrowstyle="->", color=CINZA, lw=1.1))
        ax.set_ylim(0, base.max() + 7)

    _titular(
        fig, "Janelas rotuladas no domínio próprio, por enquadramento",
        f"{len(todas)} janelas úteis de 193 rotuladas à mão nas capturas do próprio "
        "dispositivo.\nAs descartadas (sem folha em foco, só caule ou fruto) não "
        "aparecem.")
    _salvar(fig, nome)


# --------------------------------------------------------------------


def main() -> int:
    if not MODELO_ATUAL.exists():
        sys.exit(f"modelo nao encontrado: {MODELO_ATUAL}")

    todas = carregar_rotulos()
    teste = [a for a in todas if a["captura"] == ENQUADRAMENTO_TESTE]
    if not teste:
        sys.exit(f"nenhuma janela do enquadramento {ENQUADRAMENTO_TESTE}")

    print(f"{len(todas)} janelas uteis, {len(teste)} no enquadramento retido")
    print()

    print("rodando o modelo em producao (4 classes)...")
    prev_atual = prever(MODELO_ATUAL, teste, CLASSES_4)
    print("rodando o modelo antigo (3 classes)...")
    prev_antigo = prever(MODELO_ANTIGO, teste, CLASSES_3) if MODELO_ANTIGO.exists() else None

    acertos = sum(1 for a, p in zip(teste, prev_atual) if a["classe"] == p)
    maioria = Counter(a["classe"] for a in teste).most_common(1)[0][1]
    sadias = [(a, p) for a, p in zip(teste, prev_atual) if a["classe"] == "saudavel"]
    falso_doenca = sum(1 for _, p in sadias if p in ("septoriose", "pinta_preta"))

    print()
    print("=== ENQUADRAMENTO F RETIDO ===")
    print(f"  acuracia ................ {acertos}/{len(teste)} = {acertos/len(teste)*100:.1f}%")
    print(f"  baseline trivial ........ {maioria}/{len(teste)} = {maioria/len(teste)*100:.1f}%")
    print(f"  janelas sadias .......... {len(sadias)}")
    print(f"  chamadas de DOENCA ...... {falso_doenca}")
    if prev_antigo is not None:
        ac_antigo = sum(1 for a, p in zip(teste, prev_antigo) if a["classe"] == p)
        fd_antigo = sum(1 for (a, _), p in zip(sadias, [p for a, p in zip(teste, prev_antigo) if a["classe"] == "saudavel"]) if p in ("septoriose", "pinta_preta"))
        print(f"  modelo antigo, acuracia . {ac_antigo}/{len(teste)} = {ac_antigo/len(teste)*100:.1f}%")
        print(f"  modelo antigo, falsa doenca em sadias . {fd_antigo}")

    print()
    print("gerando figuras em docs/figuras/modelo/ ...")
    figura_matriz(
        teste, prev_atual, "matriz-confusao-dominio-proprio",
        "Matriz de confusão: enquadramento retido",
        f"Modelo em produção, 4 classes. {len(teste)} janelas do enquadramento F, que "
        f"nunca entrou no treino.\nAcurácia {_pt(acertos/len(teste)*100)}%, contra "
        f"{_pt(maioria/len(teste)*100)}% da baseline trivial. Contagem e percentual da linha.")

    if prev_antigo is not None:
        figura_comparacao(teste, prev_antigo, prev_atual,
                          "comparacao-tres-quatro-classes")

    figura_distribuicao(todas, "distribuicao-janelas-dominio-proprio")

    metricas = {
        "enquadramento_teste": ENQUADRAMENTO_TESTE,
        "janelas_teste": len(teste),
        "janelas_uteis_total": len(todas),
        "acuracia": round(acertos / len(teste), 4),
        "baseline_trivial": round(maioria / len(teste), 4),
        "janelas_sadias": len(sadias),
        "sadias_chamadas_de_doenca": falso_doenca,
        "previstas": dict(Counter(prev_atual)),
    }
    if prev_antigo is not None:
        metricas["modelo_antigo_previstas"] = dict(Counter(prev_antigo))
    destino = RAIZ / "models" / "metricas_modelo_dominio.json"
    destino.write_text(json.dumps(metricas, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  metricas em {destino.relative_to(RAIZ.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
