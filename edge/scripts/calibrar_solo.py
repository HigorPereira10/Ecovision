#!/usr/bin/env python3
"""
Ferramenta de calibração do sensor capacitivo de umidade do solo.

Mostra o valor bruto do ADS1115, que define SOIL_DRY_RAW e SOIL_WET_RAW,
junto da tensão e da porcentagem correspondente na calibração vigente.

Uso:
    # uma leitura (mediana de 20 amostras)
    python edge/scripts/calibrar_solo.py

    # registra um ponto nomeado no CSV de calibração
    python edge/scripts/calibrar_solo.py --marcar "capacidade de campo"

    # acompanha uma secagem, uma linha a cada 10 minutos, até Ctrl+C
    python edge/scripts/calibrar_solo.py --monitorar --intervalo 600

O CSV é gravado em edge/data/calibracao_solo.csv, com horário, valor
bruto, tensão, porcentagem e rótulo de cada ponto.
"""

import argparse
import csv
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from edge.src import config  # noqa: E402
from edge.src.sensors import soil_moisture  # noqa: E402

# Fundo de escala do ADS1115 na configuração de soil_moisture.py
# (PGA=001, ±4,096 V), usado para exibir a tensão equivalente.
_FUNDO_DE_ESCALA_V = 4.096
_CONTAGEM_MAXIMA = 32767

_CSV = Path(__file__).resolve().parents[1] / "data" / "calibracao_solo.csv"
_COLUNAS = ["momento_utc", "bruto", "tensao_v", "pct_calibracao_atual", "desvio", "rotulo"]


def medir(amostras: int) -> tuple[int, float, float]:
    """Devolve (bruto mediano, tensão, desvio padrão das amostras).

    A mediana é imune a leituras espúrias do I2C; o desvio indica se o
    sensor está estável.
    """
    leituras = []
    for _ in range(amostras):
        leituras.append(soil_moisture._ler_bruto(config.SOIL_ADS1115_CHANNEL))
        time.sleep(0.05)

    bruto = int(statistics.median(leituras))
    desvio = statistics.stdev(leituras) if len(leituras) > 1 else 0.0
    tensao = bruto / _CONTAGEM_MAXIMA * _FUNDO_DE_ESCALA_V
    return bruto, tensao, desvio


def pct_atual(bruto: int) -> float:
    """Porcentagem que o sistema produziria para este valor bruto."""
    return soil_moisture.converter_para_pct(bruto)


def gravar(bruto: int, tensao: float, desvio: float, rotulo: str) -> None:
    _CSV.parent.mkdir(parents=True, exist_ok=True)
    novo = not _CSV.exists()
    with open(_CSV, "a", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        if novo:
            escritor.writerow(_COLUNAS)
        escritor.writerow([
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            bruto,
            f"{tensao:.3f}",
            pct_atual(bruto),
            f"{desvio:.1f}",
            rotulo,
        ])


def imprimir(bruto: int, tensao: float, desvio: float) -> None:
    print(f"  bruto ............. {bruto}")
    print(f"  tensao ............ {tensao:.3f} V")
    print(f"  desvio das amostras {desvio:.1f}")
    print(f"  pct na calibracao atual ({config.SOIL_DRY_RAW} seco / "
          f"{config.SOIL_WET_RAW} molhado) ... {pct_atual(bruto)}%")

    if desvio > 50:
        print("  AVISO: desvio alto. Sensor mal encaixado na terra, conector")
        print("         frouxo, ou alimentacao instavel. Nao calibre com isto.")

    if bruto >= config.SOIL_DRY_RAW:
        print("  AVISO: no piso da escala ou abaixo. A porcentagem esta sendo")
        print("         cortada em 0% e o valor real se perde.")
    if bruto <= config.SOIL_WET_RAW:
        print("  AVISO: no teto da escala ou acima. A porcentagem esta sendo")
        print("         cortada em 100% e o valor real se perde.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Le o valor bruto do sensor de solo, para calibracao."
    )
    parser.add_argument(
        "--amostras", type=int, default=20,
        help="quantas leituras tirar para a mediana (padrao 20)",
    )
    parser.add_argument(
        "--marcar", metavar="ROTULO",
        help="grava este ponto no CSV com o rotulo informado, "
             'por exemplo "capacidade de campo"',
    )
    parser.add_argument(
        "--monitorar", action="store_true",
        help="repete indefinidamente, gravando cada ponto no CSV",
    )
    parser.add_argument(
        "--intervalo", type=int, default=600,
        help="segundos entre leituras no modo monitorar (padrao 600)",
    )
    argumentos = parser.parse_args()

    if argumentos.monitorar:
        rotulo = argumentos.marcar or "secagem"
        print(f"Monitorando a cada {argumentos.intervalo}s. Ctrl+C para parar.")
        print(f"Gravando em {_CSV}")
        try:
            while True:
                bruto, tensao, desvio = medir(argumentos.amostras)
                gravar(bruto, tensao, desvio, rotulo)
                agora = datetime.now().strftime("%d/%m %H:%M")
                print(f"  {agora}  bruto={bruto}  {tensao:.3f}V  "
                      f"{pct_atual(bruto)}%  desvio={desvio:.1f}")
                time.sleep(argumentos.intervalo)
        except KeyboardInterrupt:
            print("\nInterrompido. O CSV esta salvo.")
        return 0

    bruto, tensao, desvio = medir(argumentos.amostras)
    print()
    imprimir(bruto, tensao, desvio)

    if argumentos.marcar:
        gravar(bruto, tensao, desvio, argumentos.marcar)
        print()
        print(f'  ponto "{argumentos.marcar}" gravado em {_CSV}')
        print()
        print("  Para usar este valor, edite o .env deste dispositivo:")
        print(f"      SOIL_WET_RAW={bruto}    # se este ponto e a capacidade de campo")
        print(f"      SOIL_DRY_RAW={bruto}    # se este ponto e o extremo seco")
        print("  e reinicie nada: os crons leem o .env a cada execucao.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
