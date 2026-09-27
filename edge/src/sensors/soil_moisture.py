"""
edge/src/sensors/soil_moisture.py

Leitura do sensor capacitivo de umidade do solo, via ADC ADS1115
(I2C, 16-bit). O Raspberry Pi não tem ADC nativo, por isso o ADS1115 é
obrigatório (Blueprint v3.0, Fase 1).

Sensor capacitivo foi escolhido (não resistivo) por evitar corrosão por
eletrólise em uso contínuo no solo úmido.

Calibração: SOIL_DRY_RAW / SOIL_WET_RAW (edge/src/config.py) são os
valores brutos do ADC com o sensor seco e submerso, respectivamente.
CUIDADO: os valores atuais são apenas placeholders de fabricante.
Recalibrar com o sensor físico antes da coleta de campo, ou a
porcentagem devolvida aqui não reflete a umidade real do solo.

Relação com o resto do sistema:
- Chamado por edge/src/main.py em cada ciclo de captura.
- A leitura resultante entra no pacote enviado para o endpoint
  /diagnostico e é persistida na tabela leituras_ambientais
  (cloud/app/db/models.py).
"""

import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.ads1x15 import Pin
from adafruit_ads1x15.analog_in import AnalogIn

from edge.src import config

# As constantes de canal ficavam em ads1115 como P0..P3 em versões antigas
# da adafruit-circuitpython-ads1x15. Na versão atual elas mudaram de lugar
# e de nome: agora são Pin.A0..Pin.A3, em ads1x15. Descoberto ao rodar o
# ciclo completo no Raspberry Pi, que quebrava com AttributeError aqui.
_CANAIS_ADS = {
    0: Pin.A0,
    1: Pin.A1,
    2: Pin.A2,
    3: Pin.A3,
}


def _clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


def ler_umidade_solo() -> float:
    """Lê o canal analógico do sensor de solo via ADS1115 e retorna um
    percentual (0-100), onde 0% = seco (SOIL_DRY_RAW) e 100% = saturado
    (SOIL_WET_RAW)."""
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    canal = AnalogIn(ads, _CANAIS_ADS[config.SOIL_ADS1115_CHANNEL])

    valor_bruto = canal.value

    # Sensor capacitivo: valor bruto CAI conforme a umidade AUMENTA.
    faixa = config.SOIL_DRY_RAW - config.SOIL_WET_RAW
    if faixa == 0:
        raise RuntimeError(
            "SOIL_DRY_RAW e SOIL_WET_RAW estão iguais, sensor não calibrado "
            "(ver edge/src/config.py)."
        )

    umidade_pct = (config.SOIL_DRY_RAW - valor_bruto) / faixa * 100
    return round(_clamp(umidade_pct, 0.0, 100.0), 1)
