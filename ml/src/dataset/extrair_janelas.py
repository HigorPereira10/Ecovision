"""
ml/src/dataset/extrair_janelas.py

Transforma as capturas do dispositivo em janelas prontas para rotular.

POR QUE ISTO EXISTE
-------------------
Medido em 2026-11-01, tres caminhos diferentes falharam no MESMO ponto,
que e a distancia entre o dado de treino e esta estufa:

  - quarta classe vinda do OLID: 83,3% dentro do proprio OLID, ZERO
    janelas vencidas nas capturas do dispositivo;
  - porta de familiaridade: recusa fundo, nao recusa folha estranha,
    porque e post-hoc (ver o benchmark citado em ajuste_quatro_classes);
  - geometria da lesao: separa entre fontes (AUC 0,849) e nao dentro
    da mesma fonte (0,627), e a medida ainda muda com a distancia da
    camera (22,7 a 20 cm contra 29,9 a 34 cm, mesma planta).

O unico dominio ao qual o projeto tem acesso ilimitado e o proprio. E
desde 2026-11-01 ele e consistente: foco travado em 20 cm, LED
funcionando, captura de 2 em 2 horas, folíolo chegando ao modelo com
222 px pela janela deslizante. Antes disso as capturas variavam demais
para servir de treino.

ROTULE O QUE DA PARA VER, NAO O QUE DA PARA SUPOR
-------------------------------------------------
As classes sugeridas sao DESCRITIVAS, e isso nao e preciosismo. Nao da
para afirmar "deficiencia de potassio" olhando uma foto sem saber o que
a planta recebeu de adubo: o OLID so pode porque foi ensaio controlado,
com privacao proposital. Ja "amarelecimento difuso" qualquer um verifica
olhando, e e defensavel sem laudo agronomico.

Afirmar etiologia a partir de rotulo visual e o tipo de coisa que a
banca derruba em uma pergunta.

A DIVISAO E POR TEMPO, NUNCA ALEATORIA
--------------------------------------
Capturas de 2 em 2 horas da mesma planta sao quase duplicatas. Uma
divisao aleatoria colocaria quadros praticamente identicos no treino e
no teste, e a acuracia resultante nao mediria nada. Por isso
montar_divisao() corta por DATA: treino ate um dia, teste do dia
seguinte em diante.

Isso ainda nao resolve o fato de ser UMA planta, em UM vaso, contra UM
fundo. Isso e limitacao a declarar no texto, nao problema a esconder
com metrica.

USO
---
    # 1. extrair janelas das capturas e montar as pastas de rotulo
    python -m ml.src.dataset.extrair_janelas --capturas <pasta> --saida <pasta>

    # 2. (voce move cada arquivo para a pasta da classe correspondente)

    # 3. gerar a divisao treino/teste por data
    python -m ml.src.dataset.extrair_janelas --divisao <pasta> --corte 2026-11-08
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

# Descritivas de proposito, ver o topo. `septoriose` e `pinta_preta`
# continuam porque sao o que o modelo ja sabe; as duas novas sao o que
# a planta de fato apresenta e o modelo nao sabe nomear.
# POR QUE UMA CLASSE SO PARA O ESTRESSE, E NAO AMARELECIMENTO E
# TECIDO SECO SEPARADOS: medido em 2026-11-02 sobre 56 janelas, as duas
# nao se separam. A fracao de tecido seco nas janelas chamadas de
# amarelecimento na sessao B deu 7,6%, e nas chamadas de tecido seco
# deu 7,7%. Sao a mesma coisa pela medida, e a fronteira derivou entre
# sessoes: o mesmo padrao de amarelo com manchas marrons foi rotulado
# de um jeito num dia e de outro no seguinte.
#
# Tem razao agronomica tambem, e e a mais forte: afirmar "amarelecimento
# por deficiencia" exige autoridade que este trabalho nao tem. Dizer
# "a folha esta alterada e nao e fungo conhecido" exige so o que se ve.
#
# O rotulo fino continua gravado na coluna classe_fina de rotulos.csv,
# entao a separacao volta a ser possivel quando houver dado que a
# sustente.
CLASSES = [
    "saudavel",
    "septoriose",
    "pinta_preta",
    "estresse_foliar",
    "descartar",  # janela inutil: desfocada, cortada ao meio, duvidosa
]

# Qualidade minima para valer o tempo de rotular. Janela sem quase nada
# de verde nao e folha, e a porta ja recusa a maioria delas.
# Mesmo limiar de cloud/app/core/janelas.py, e pelo mesmo motivo: com
# 0,08 um pote plastico verde-azulado passou por folha em producao
# (2026-11-03). O numero vem do percentil 5 das janelas ja rotuladas
# como folha, que e 20,5%.
COBERTURA_VERDE_MINIMA = 0.18

# Sessão = um ENQUADRAMENTO. Muda quando o vaso ou a câmera muda de
# lugar. Entra no nome do arquivo porque é metade da identidade de uma
# posição (ver chave_posicao).
SESSAO_PADRAO = "A"


def chave_posicao(nome_arquivo: str) -> str:
    """Identidade de uma posição: o ENQUADRAMENTO mais a célula da grade.

    ATENÇÃO, BUG CORRIGIDO AQUI: antes a chave era só `xNNNN_yNNNN`. Com
    um enquadramento só isso bastava, mas assim que o vaso muda de lugar
    a mesma célula da grade passa a mostrar OUTRAS folhas. Duas janelas
    completamente diferentes recebiam a mesma chave, e a trava
    anti-vazamento mandava as duas para o mesmo lado da divisão achando
    que eram a mesma folha.

    Pior: a contagem de "posições distintas", que é o número que decide
    quando há dado suficiente para treinar, ficava travada em 36 por
    mais que o enquadramento mudasse. Mover o vaso pareceria não
    adiantar nada, quando é justamente o que mais adianta.

    Arquivo sem sessão no nome vem da extração anterior a esta correção
    e é tratado como sessão A, que é de onde ele veio mesmo.
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
                # Grava o RECORTE NATIVO, nao o reduzido para 224: a
                # redução pertence ao treino, e guardar o original deixa
                # a decisão de escala em aberto se a janela mudar.
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
    (formato 2026-11-01T20-15-37...)."""
    try:
        return datetime.strptime(nome_captura[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def montar_divisao(pasta: Path, corte: date) -> int:
    """Gera a divisão treino/teste cortando por DATA.

    Nunca aleatória: ver o cabeçalho deste arquivo. Capturas de 2 em 2
    horas da mesma planta são quase duplicatas, e uma divisão aleatória
    colocaria quadros praticamente idênticos dos dois lados.
    """
    manifesto = pasta / "manifesto.csv"
    if not manifesto.exists():
        raise SystemExit(f"{manifesto} não existe. Rode a extração antes.")

    origem: dict[str, str] = {}
    with manifesto.open(encoding="utf-8") as arquivo:
        for linha in csv.DictReader(arquivo):
            origem[linha["arquivo"]] = linha["captura"]

    # TRAVA POR POSIÇÃO, além da trava por data.
    #
    # Medido em 2026-11-01, nas primeiras 47 janelas rotuladas: 2,4
    # imagens por posição da grade, porque capturas de 10 em 10 minutos
    # mostram a mesma folha. A posição `x0672 y0224` apareceu em três
    # capturas e as três são praticamente a mesma imagem.
    #
    # A divisão por data já separa, porque capturas do mesmo dia caem do
    # mesmo lado. Mas isso só vale enquanto ninguém mexer no corte: um
    # corte no meio de um dia, ou um reuso deste script com outra regra,
    # colocaria a mesma folha no treino e no teste sem nenhum aviso.
    # Esta trava torna isso impossível em vez de improvável.
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
