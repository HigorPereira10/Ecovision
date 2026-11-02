"""
ml/src/training/avaliar_quatro_classes.py

Decide se o modelo de quatro classes pode substituir o de tres.

TRES PERGUNTAS, NESTA ORDEM DE IMPORTANCIA
------------------------------------------
1. O ATALHO DE ORIGEM FOI EVITADO? A classe nova vem so do OLID. Se o
   modelo aprendeu "imagem com cara de OLID = deficiencia", ele vai
   chamar de deficiencia tambem as SAUDAVEIS do OLID, que vieram da
   mesma camera, do mesmo campo, no mesmo formato.

   Por isso a acuracia nas saudaveis do OLID e a metrica mais
   importante deste arquivo. Ela mede exatamente o que a metrica
   agregada esconde: um modelo que use a origem como atalho fecha com
   acuracia alta e nao serve para nada em campo.

   Tambem se mede a contaminacao no outro sentido: quantas imagens de
   PlantDoc e PlantVillage, que nao tem nenhuma deficiencia rotulada,
   passaram a cair na classe nova.

2. HOUVE REGRESSAO NAS TRES CLASSES ANTIGAS? A comparacao e PAREADA,
   nas MESMAS imagens, contra o modelo em producao. Ganhar uma classe
   nova perdendo acuracia nas doencas seria troca, nao melhora, e foi
   esse o criterio que ja reprovou uma versao anterior do ajuste (ver
   ajuste_dois_dominios.py).

3. O QUE O MODELO DIZ DA NOSSA PLANTA? As capturas de 2026-11-01, que
   motivaram tudo isto, sao o caso de uso real. O modelo de tres
   classes dizia pinta_preta em 16 das 23 janelas aprovadas. Se o de
   quatro continuar dizendo o mesmo, a classe nova nao resolveu o
   problema que foi criada para resolver.

   ATENCAO: isto NAO e metrica de acuracia, porque nao existe rotulo de
   especialista para essa planta. E observacao, e entra no texto como
   observacao.

USO
---
    python ml/src/training/avaliar_quatro_classes.py \\
        --laboratorio ml/data/plantvillage_tomate \\
        [--capturas <pasta com .jpg do dispositivo>]
"""

import argparse
import csv
import glob
import os

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import numpy as np
from PIL import Image

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELO_3C = os.path.join(RAIZ, "training", "modelo_hibrido_lab_campo.keras")
MODELO_4C = os.path.join(RAIZ, "training", "modelo_quatro_classes.keras")
PLANTDOC = os.path.join(RAIZ, "data", "plantdoc_tomate")
DIVISAO_OLID = os.path.join(RAIZ, "data", "olid_divisao.csv")

CLASSES_3 = ["septoriose", "pinta_preta", "saudavel"]
CLASSES_4 = ["septoriose", "pinta_preta", "saudavel", "deficiencia_nutricional"]
PASTA_CAMPO = {"distrator_septoria": 0, "pinta_preta": 1, "saudavel": 2}
PASTA_LAB = {"mancha_septoria": 0, "pinta_preta": 1, "folhas_saudaveis": 2}
TAMANHO = (224, 224)
LOTE = 16


def carregar(caminhos: list[str]) -> np.ndarray:
    return np.asarray(
        [
            np.asarray(
                Image.open(c).convert("RGB").resize(TAMANHO, Image.BILINEAR), np.float32
            )
            for c in caminhos
        ]
    )


def prever(modelo, caminhos: list[str]) -> np.ndarray:
    saida = []
    for i in range(0, len(caminhos), LOTE):
        saida.append(modelo.predict(carregar(caminhos[i : i + LOTE]), verbose=0))
    return np.vstack(saida) if saida else np.zeros((0, 1))


def coletar(raiz, splits, mapa):
    itens = []
    for split in splits:
        for pasta, indice in mapa.items():
            for caminho in glob.glob(os.path.join(raiz, split, pasta, "*")):
                if os.path.isfile(caminho):
                    itens.append((caminho, indice))
    return itens


def ler_divisao_olid(split: str) -> list[tuple[str, int]]:
    if not os.path.exists(DIVISAO_OLID):
        raise SystemExit(
            f"{DIVISAO_OLID} nao existe. Rode ajuste_quatro_classes.py antes: "
            "sem a divisao gravada, avaliar no teste do OLID nao e reproduzivel."
        )
    itens = []
    with open(DIVISAO_OLID, encoding="utf-8") as arquivo:
        for linha in csv.DictReader(arquivo):
            if linha["split"] == split:
                itens.append((os.path.join(RAIZ, linha["caminho"]), int(linha["classe_indice"])))
    return itens


def acuracia_por_classe(verdadeiro, previsto, classes, titulo):
    print(f"\n{titulo}")
    print(f"  {'classe':<26}{'n':>5}{'acertos':>9}{'acuracia':>10}")
    for i, nome in enumerate(classes):
        alvo = verdadeiro == i
        if not alvo.any():
            continue
        acertos = int((previsto[alvo] == i).sum())
        print(f"  {nome:<26}{int(alvo.sum()):>5}{acertos:>9}{acertos / alvo.sum() * 100:>9.1f}%")
    geral = float((previsto == verdadeiro).mean()) if len(verdadeiro) else 0.0
    print(f"  {'GERAL':<26}{len(verdadeiro):>5}{int((previsto == verdadeiro).sum()):>9}"
          f"{geral * 100:>9.1f}%")
    return geral


def main() -> None:
    import keras

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[2])
    parser.add_argument("--laboratorio", required=True)
    parser.add_argument("--capturas", default=None, help="pasta com capturas do dispositivo")
    argumentos = parser.parse_args()

    modelo4 = keras.models.load_model(MODELO_4C)
    modelo3 = keras.models.load_model(MODELO_3C)

    # --- 1. o atalho de origem ---
    print("=" * 72)
    print("1. O ATALHO DE ORIGEM FOI EVITADO?")
    print("=" * 72)
    olid_teste = ler_divisao_olid("test")
    caminhos = [c for c, _ in olid_teste]
    verdadeiro = np.array([r for _, r in olid_teste])
    previsto = prever(modelo4, caminhos).argmax(axis=1)
    acuracia_por_classe(verdadeiro, previsto, CLASSES_4,
                        "OLID, conjunto de teste (mesma camera, mesmo campo)")

    saudaveis = verdadeiro == 2
    if saudaveis.any():
        virou_deficiencia = int((previsto[saudaveis] == 3).sum())
        print(f"\n  >>> SAUDAVEIS do OLID chamadas de deficiencia: "
              f"{virou_deficiencia}/{int(saudaveis.sum())} "
              f"({virou_deficiencia / saudaveis.sum() * 100:.0f}%)")
        print("      Alto aqui = o modelo usou a ORIGEM como atalho, e nao serve.")

    # contaminacao: dados sem nenhuma deficiencia rotulada
    lab_teste = coletar(argumentos.laboratorio, ("test",), PASTA_LAB)
    campo_teste = coletar(PLANTDOC, ("test",), PASTA_CAMPO)
    for rotulo, itens in (("PlantVillage", lab_teste), ("PlantDoc", campo_teste)):
        if not itens:
            continue
        p = prever(modelo4, [c for c, _ in itens]).argmax(axis=1)
        n = int((p == 3).sum())
        print(f"  {rotulo}: {n}/{len(itens)} ({n / len(itens) * 100:.1f}%) "
              f"caíram na classe nova, sem terem deficiencia rotulada")

    # --- 2. regressao nas tres antigas ---
    print()
    print("=" * 72)
    print("2. HOUVE REGRESSAO? (comparacao pareada, nas mesmas imagens)")
    print("=" * 72)
    for rotulo, itens in (("laboratorio (PlantVillage test)", lab_teste),
                          ("campo (PlantDoc test)", campo_teste)):
        if not itens:
            continue
        caminhos = [c for c, _ in itens]
        v = np.array([r for _, r in itens])
        p3 = prever(modelo3, caminhos).argmax(axis=1)
        p4 = prever(modelo4, caminhos).argmax(axis=1)
        a3 = float((p3 == v).mean())
        a4 = float((p4 == v).mean())
        print(f"\n  {rotulo}  (n={len(itens)})")
        print(f"    3 classes: {a3 * 100:5.1f}%")
        print(f"    4 classes: {a4 * 100:5.1f}%   ({(a4 - a3) * 100:+.1f} p.p.)")
        acuracia_por_classe(v, p4, CLASSES_4, "    detalhe do modelo de 4 classes:")

    # --- 3. a nossa planta ---
    if argumentos.capturas:
        print()
        print("=" * 72)
        print("3. O QUE O MODELO DIZ DA NOSSA PLANTA (observacao, nao metrica)")
        print("=" * 72)
        import sys

        sys.path.insert(0, RAIZ.rsplit(os.sep + "ml", 1)[0])
        from ml.src.porta.avaliar import carregar_referencia, janelas_da_captura

        referencia, limiar, _ = carregar_referencia()
        base = keras.Model(modelo4.inputs,
                           modelo4.get_layer("global_average_pooling2d").output)
        densa = [c for c in modelo4.layers if isinstance(c, keras.layers.Dense)][-1]
        kernel, bias = densa.get_weights()

        for caminho in sorted(glob.glob(os.path.join(argumentos.capturas, "*.jpg"))):
            _img, recortes, _pos = janelas_da_captura(caminho)
            vet = base.predict(np.asarray(recortes, np.float32), verbose=0)
            fam = ((vet / np.linalg.norm(vet, axis=1, keepdims=True)) @ referencia.T).max(1)
            z = vet @ kernel + bias
            aprovadas = fam >= limiar
            if not aprovadas.any():
                continue
            venc = z[aprovadas].argmax(axis=1)
            votos = {CLASSES_4[i]: int((venc == i).sum()) for i in range(4)}
            print(f"  {os.path.basename(caminho):<34}"
                  f"{int(aprovadas.sum()):>3}/{len(recortes):<3} aprovadas   {votos}")

    print("\nLEMBRETE: so promover para producao se (1) as saudaveis do OLID "
          "nao viraram deficiencia e (2) nao houve regressao nas tres antigas.")


if __name__ == "__main__":
    main()
