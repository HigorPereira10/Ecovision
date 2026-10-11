"""
edge/src/sensors/soil_moisture.py

Leitura do sensor capacitivo de umidade do solo, via ADC ADS1115
(I2C, 16-bit). O Raspberry Pi não tem ADC nativo, por isso o ADS1115 é
obrigatório (Blueprint, Fase 1).

Sensor capacitivo foi escolhido (não resistivo) por evitar corrosão por
eletrólise em uso contínuo no solo úmido.

POR QUE smbus2 E NÃO A BIBLIOTECA DA ADAFRUIT
---------------------------------------------
Este módulo conversa com o ADS1115 escrevendo direto nos registradores
dele, em vez de usar adafruit-circuitpython-ads1x15 como antes.

Motivo: a pilha da Adafruit (Blinka -> Adafruit-PureIO 1.1.11) monta a
chamada ioctl do I2C manualmente com ctypes, e essa montagem falha no
Raspberry Pi 3B+ com Raspberry Pi OS trixie (Python 3.13, kernel 6.18,
ARM 64 bits). Toda leitura de registrador levanta
`OSError: [Errno 5] Input/output error`.

Medido no dispositivo real, com o mesmo módulo e a mesma fiação:

    adafruit_ads1x15 ......  0 sucessos em 3 tentativas
    smbus2 ................ 10 sucessos em 10 tentativas

O smbus2 usa o caminho padrão do kernel para I2C, então não depende de
reimplementação de ioctl. A troca também remove uma dependência que já
havia quebrado este projeto uma vez, quando as constantes de canal
mudaram de `ads1115.P0` para `ads1x15.Pin.A0` entre versões.

O protocolo do ADS1115 é simples o suficiente para justificar isso:
escreve-se a configuração desejada no registrador 0x01, espera-se a
conversão e lê-se o resultado no registrador 0x00.

CALIBRAÇÃO
----------
SOIL_DRY_RAW / SOIL_WET_RAW (edge/src/config.py) são os valores brutos
do ADC com o sensor seco e submerso. Precisam ser medidos com o sensor
físico; valores de fabricante não refletem a umidade real do solo.

Relação com o resto do sistema:
- Chamado por edge/src/main.py em cada ciclo de captura.
- A leitura resultante entra no pacote enviado para o endpoint
  /diagnostico e é persistida na tabela leituras_ambientais
  (cloud/app/db/models.py).
"""

import time

from smbus2 import SMBus, i2c_msg

from edge.src import config

# Barramento I2C exposto nos pinos 3 (SDA/GPIO2) e 5 (SCL/GPIO3) do
# header de 40 pinos. O /dev/i2c-0 existe, mas é o barramento interno
# usado pela câmera, não pelo header.
_BARRAMENTO = 1

# 0x48 é o endereço padrão do ADS1115, válido com o pino ADDR ligado ao
# GND. Solto, o endereço fica indefinido e o módulo some do barramento.
_ENDERECO = 0x48

_REG_CONVERSAO = 0x00
_REG_CONFIG = 0x01

# Bits do registrador de configuração que não dependem do canal:
#   0x8000  OS=1, dispara uma conversão
#   0x0200  PGA=001, fundo de escala +-4.096V (3,3V lê 26400)
#   0x0100  MODE=1, disparo único em vez de contínuo
#   0x0080  DR=100, 128 amostras por segundo
#   0x0003  COMP_QUE=11, comparador desligado (não usamos o pino ALERT)
_CONFIG_BASE = 0x8000 | 0x0200 | 0x0100 | 0x0080 | 0x0003

# Bits MUX, que selecionam a entrada analógica contra o GND.
_MUX_POR_CANAL = {0: 0x4000, 1: 0x5000, 2: 0x6000, 3: 0x7000}

# A 128 amostras por segundo cada conversão leva 7,8ms. A margem evita
# ler o resultado da conversão anterior.
_ESPERA_CONVERSAO_SEGUNDOS = 0.010


def _clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


def _ler_bruto(canal: int) -> int:
    """Dispara uma conversão no canal informado e devolve o valor bruto
    com sinal (o ADS1115 entrega complemento de dois em 16 bits)."""
    if canal not in _MUX_POR_CANAL:
        raise RuntimeError(
            f"SOIL_ADS1115_CHANNEL inválido: {canal}. O ADS1115 tem os "
            f"canais 0 a 3."
        )

    configuracao = _CONFIG_BASE | _MUX_POR_CANAL[canal]

    with SMBus(_BARRAMENTO) as barramento:
        barramento.i2c_rdwr(
            i2c_msg.write(
                _ENDERECO,
                [_REG_CONFIG, (configuracao >> 8) & 0xFF, configuracao & 0xFF],
            )
        )
        time.sleep(_ESPERA_CONVERSAO_SEGUNDOS)

        aponta_conversao = i2c_msg.write(_ENDERECO, [_REG_CONVERSAO])
        resultado = i2c_msg.read(_ENDERECO, 2)
        barramento.i2c_rdwr(aponta_conversao, resultado)

    byte_alto, byte_baixo = list(resultado)
    valor = (byte_alto << 8) | byte_baixo
    return valor - 0x10000 if valor > 0x7FFF else valor


def ler_umidade_solo() -> float:
    """Lê o canal analógico do sensor de solo via ADS1115 e retorna um
    percentual (0-100), onde 0% = seco (SOIL_DRY_RAW) e 100% = saturado
    (SOIL_WET_RAW)."""
    # Sensor capacitivo: valor bruto CAI conforme a umidade AUMENTA.
    faixa = config.SOIL_DRY_RAW - config.SOIL_WET_RAW
    if faixa == 0:
        raise RuntimeError(
            "SOIL_DRY_RAW e SOIL_WET_RAW estão iguais, sensor não calibrado "
            "(ver edge/src/config.py)."
        )

    valor_bruto = _ler_bruto(config.SOIL_ADS1115_CHANNEL)

    umidade_pct = (config.SOIL_DRY_RAW - valor_bruto) / faixa * 100
    return round(_clamp(umidade_pct, 0.0, 100.0), 1)
