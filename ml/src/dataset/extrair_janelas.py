"""
Extrai janelas das capturas do dispositivo para rotulagem e gera a divisão
entre treino e teste.

As classes de rótulo são descritivas: identificar a causa de uma
alteração (como uma deficiência nutricional) a partir de uma foto exigiria
conhecer o manejo da planta. A divisão é feita por data e por posição na
grade, nunca de forma aleatória, porque capturas próximas da mesma planta
são quase idênticas e vazariam do treino para o teste.

Uso:
    # 1. extrair janelas das capturas e montar as pastas de rótulo
    python -m ml.src.dataset.extrair_janelas --capturas <pasta> --saida <pasta>

    # 2. mover cada arquivo para a pasta da classe correspondente

    # 3. gerar a divisão treino/teste por data
    python -m ml.src.dataset.extrair_janelas --divisao <pasta> --corte AAAA-MM-DD
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
from collections import Counter
from datetime import date, datetime
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

RAIZ = Path(__file__).resolve().parents[3]

# Classes descritivas. Amarelecimento e tecido seco formam uma única classe
# de estresse foliar: as duas não se separaram nas medições e a fronteira
# variou entre sessões de rotulagem. O rótulo detalhado fica na coluna
# classe_fina de rotulos.csv.
CLASSES = [
    "saudavel",
    "septoriose",
    "pinta_preta",
    "estresse_foliar",
    "descartar",  # janela inutil: desfocada, cortada ao meio, duvidosa
]

# Cobertura verde mínima, a mesma de cloud/app/core/janelas.py (percentil 5
# das janelas rotuladas como folha: 20,5%).
COBERTURA_VERDE_MINIMA = 0.18

# Sessão = enquadramento: muda quando o vaso ou a câmera mudam de lugar e
# compõe a identidade de uma posição (ver chave_posicao).
SESSAO_PADRAO = "A"


def chave_posicao(nome_arquivo: str) -> str:
    """Identidade de uma posição: o enquadramento mais a célula da grade.

    Sem o enquadramento, janelas diferentes de sessões distintas
    receberiam a mesma chave. Arquivos sem sessão no nome são tratados
    como sessão A.
    """
    celula = re.search(r"x\d+_y\d+", nome_arquivo)
    if not celula:
        return nome_arquivo
    prefixo = nome_arquivo.split("__", 1)[0] if "__" in nome_arquivo else ""
    if not prefixo or prefixo.startswith("diag"):
        prefixo = SESSAO_PADRAO
    return f"{prefixo}:{celula.group(0)}"


def _cobertura_verde(recorte) -> float:
    import numpy as np

    r, g, b = recorte[..., 0], recorte[..., 1], recorte[..., 2]
    mx = recorte.max(axis=2)
    mn = recorte.min(axis=2)
    saturacao = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
    verde = (g > r * 1.06) & (g > b * 1.06) & (saturacao > 0.18) & (mx > 45)
    return float(verde.mean())


def extrair(pasta_capturas: Path, pasta_saida: Path, sessao: str) -> int:
    import numpy as np
    from PIL import Image

    from ml.src.porta.avaliar import (
        carregar_modelo,
        carregar_referencia,
        janelas_da_captura,
        montar_passo,
    )

    capturas = sorted(
        p for p in pasta_capturas.iterdir() if p.suffix.lower() in (".jpg", ".jpeg")
    )
    if not capturas:
        raise SystemExit(f"Nenhuma captura em {pasta_capturas}")

    referencia, limiar, _classes = carregar_referencia()
    calcular = montar_passo(*carregar_modelo())

    entrada = pasta_saida / "_para_rotular"
    entrada.mkdir(parents=True, exist_ok=True)
    for nome in CLASSES:
        (pasta_saida / nome).mkdir(parents=True, exist_ok=True)

    manifesto = pasta_saida / "manifesto.csv"
    novo = not manifesto.exists()
    ja_vistos: set[str] = set()
    if not novo:
        with manifesto.open(encoding="utf-8") as arquivo:
            ja_vistos = {linha["arquivo"] for linha in csv.DictReader(arquivo)}

    gravadas = 0
    with manifesto.open("a", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        if novo:
            escritor.writerow(
                ["arquivo", "captura", "x", "y", "lado", "familiaridade", "verde"]
            )

        for caminho in capturas:
            imagem, recortes, posicoes = janelas_da_captura(caminho)
            if not recortes:
                continue
            vetores, _probs = calcular(recortes)
            normal = vetores / np.linalg.norm(vetores, axis=1, keepdims=True)
            familiaridade = (normal @ referencia.T).max(axis=1)

            aproveitadas = 0
            for indice, (recorte, (x, y, lado)) in enumerate(zip(recortes, posicoes)):
                if familiaridade[indice] < limiar:
                    continue
                verde = _cobertura_verde(recorte)
                if verde < COBERTURA_VERDE_MINIMA:
                    continue
                nome = f"{sessao}__{caminho.stem}__x{x:04d}_y{y:04d}.png"
                if nome in ja_vistos:
                    continue
                # Grava o recorte sem reduzir para 224 px; a redução fica
                # para o treino.
                pedaco = imagem.crop((x, y, x + lado, y + lado))
                pedaco.save(entrada / nome)
                escritor.writerow(
                    [nome, caminho.name, x, y, lado,
                     f"{familiaridade[indice]:.4f}", f"{verde:.4f}"]
                )
                aproveitadas += 1
                gravadas += 1
            print(f"  {caminho.name}: {aproveitadas}/{len(recortes)} janelas aproveitadas")

    print(f"\n{gravadas} janelas novas em {entrada}")
    print("\nAgora mova cada arquivo de _para_rotular/ para a pasta da classe:")
    for nome in CLASSES:
        print(f"  {nome}/")
    print("\nO que sobrar em _para_rotular/ fica para a próxima rodada.")
    return 0


def _data_da_captura(nome_captura: str) -> date | None:
    """Extrai a data do nome do arquivo gravado pelo dispositivo
    (formato AAAA-MM-DDTHH-MM-SS)."""
    try:
        return datetime.strptime(nome_captura[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def montar_divisao(pasta: Path, corte: date) -> int:
    """Gera a divisão treino/teste cortando por data, nunca de forma
    aleatória."""
    manifesto = pasta / "manifesto.csv"
    if not manifesto.exists():
        raise SystemExit(f"{manifesto} não existe. Rode a extração antes.")

    origem: dict[str, str] = {}
    with manifesto.open(encoding="utf-8") as arquivo:
        for linha in csv.DictReader(arquivo):
            origem[linha["arquivo"]] = linha["captura"]

    # Trava por posição, além da trava por data: janelas da mesma posição
    # da grade mostram a mesma folha e ficam sempre do mesmo lado da
    # divisão, mesmo que o corte caia no meio de um dia.
    posicoes: dict[str, str] = {}
    linhas: list[tuple[str, str, str]] = []
    sem_data = 0
    conflitos = 0
    for classe in CLASSES:
        if classe == "descartar":
            continue
        for caminho in sorted((pasta / classe).glob("*.png")):
            captura = origem.get(caminho.name, "")
            dia = _data_da_captura(captura)
            if dia is None:
                sem_data += 1
                continue
            posicao = chave_posicao(caminho.name)
            split = "train" if dia < corte else "test"
            if posicao in posicoes and posicoes[posicao] != split:
                # A posição já foi para o outro lado: manda esta junto,
                # nunca separa. Vazamento é pior que desbalanceio.
                split = posicoes[posicao]
                conflitos += 1
            posicoes[posicao] = split
            linhas.append((str(caminho.relative_to(RAIZ)), classe, split))

    destino = pasta / "divisao.csv"
    with destino.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["caminho", "classe", "split"])
        escritor.writerows(linhas)

    contagem = Counter((classe, split) for _c, classe, split in linhas)
    print(f"divisão gravada em {destino}  (corte: {corte:%d/%m/%Y})")
    print(f"\n  {'classe':<26}{'treino':>8}{'teste':>8}")
    for classe in CLASSES:
        if classe == "descartar":
            continue
        t, v = contagem[(classe, "train")], contagem[(classe, "test")]
        if t or v:
            print(f"  {classe:<26}{t:>8}{v:>8}")
    print(f"\n  posições distintas: {len(posicoes)}  "
          f"({len(linhas) / max(1, len(posicoes)):.1f} imagens por posição)")
    if conflitos:
        print(f"  {conflitos} imagem(ns) realocada(s) para manter a posição inteira "
              "de um lado só (trava anti-vazamento).")
    if sem_data:
        print(f"  {sem_data} arquivo(s) sem data reconhecível, fora da divisão.")

    magras = [c for c in CLASSES if c != "descartar"
              and 0 < contagem[(c, "train")] < 50]
    if magras:
        print("\n  ATENÇÃO, classes com menos de 50 imagens de treino: "
              + ", ".join(magras))
        print("  As classes atuais têm de 52 a 127. Abaixo disso a classe")
        print("  nova vira ruído estatístico e o treino não muda nada.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[2])
    parser.add_argument("--capturas", type=Path, help="pasta com os .jpg do dispositivo")
    parser.add_argument("--saida", type=Path, help="pasta onde montar o fluxo de rótulo")
    parser.add_argument("--sessao", default=SESSAO_PADRAO,
                        help="nome do ENQUADRAMENTO (A, B, C...). Muda sempre que o vaso ou a câmera muda de lugar: é metade da identidade de uma posição.")
    parser.add_argument("--divisao", type=Path, help="gera a divisão da pasta já rotulada")
    parser.add_argument("--corte", help="data do corte treino/teste (AAAA-MM-DD)")
    argumentos = parser.parse_args()

    if argumentos.divisao:
        if not argumentos.corte:
            raise SystemExit("--divisao exige --corte AAAA-MM-DD")
        return montar_divisao(
            argumentos.divisao, datetime.strptime(argumentos.corte, "%Y-%m-%d").date()
        )
    if not argumentos.capturas or not argumentos.saida:
        raise SystemExit("Use --capturas e --saida, ou --divisao e --corte.")
    return extrair(argumentos.capturas, argumentos.saida, argumentos.sessao)


if __name__ == "__main__":
    raise SystemExit(main())
