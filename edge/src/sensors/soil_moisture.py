"""
Leitura do sensor capacitivo de umidade do solo pelo conversor ADS1115 (I2C, 16 bits).

O acesso ao ADS1115 é feito diretamente pelos registradores, com smbus2:
a pilha I2C da Adafruit (Blinka/Adafruit-PureIO) falha com
"OSError: [Errno 5]" neste Raspberry Pi (Raspberry Pi OS trixie, 64 bits).
O protocolo é simples: grava-se a configuração no registrador 0x01,
aguarda-se a conversão e lê-se o resultado no registrador 0x00.

SOIL_DRY_RAW e SOIL_WET_RAW (config.py) são os valores brutos dos extremos
da escala e precisam ser medidos em cada sensor.
"""

import time

from smbus2 import SMBus, i2c_msg

from edge.src import config

# Barramento I2C dos pinos 3 (SDA) e 5 (SCL); /dev/i2c-0 é o barramento
# interno da câmera.
_BARRAMENTO = 1

# Endereço padrão do ADS1115, com o pino ADDR ligado ao GND.
_ENDERECO = 0x48

_REG_CONVERSAO = 0x00
_REG_CONFIG = 0x01

# Bits do registrador de configuração que não dependem do canal:
#   0x8000  OS=1, dispara uma conversão
#   0x0200  PGA=001, fundo de escala de ±4,096 V
#   0x0100  MODE=1, disparo único
#   0x0080  DR=100, 128 amostras por segundo
#   0x0003  COMP_QUE=11, comparador desligado
_CONFIG_BASE = 0x8000 | 0x0200 | 0x0100 | 0x0080 | 0x0003

# Bits MUX, que selecionam a entrada analógica contra o GND.
_MUX_POR_CANAL = {0: 0x4000, 1: 0x5000, 2: 0x6000, 3: 0x7000}

# Cada conversão leva 7,8 ms a 128 amostras por segundo; a margem evita
# ler o resultado anterior.
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


def converter_para_pct(valor_bruto: int) -> float:
    """Converte um valor bruto do ADC em percentual de 0 a 100.

    Separada de ler_umidade_solo() para ser reutilizada por
    edge/scripts/calibrar_solo.py, que mostra a porcentagem correspondente
    a cada leitura bruta.
    """
    # Sensor capacitivo: o valor bruto diminui quando a umidade aumenta.
    faixa = config.SOIL_DRY_RAW - config.SOIL_WET_RAW
    if faixa == 0:
        raise RuntimeError(
            "SOIL_DRY_RAW e SOIL_WET_RAW estão iguais, sensor não calibrado "
            "(ver edge/src/config.py)."
        )

    umidade_pct = (config.SOIL_DRY_RAW - valor_bruto) / faixa * 100
    return round(_clamp(umidade_pct, 0.0, 100.0), 1)


def ler_umidade_solo() -> float:
    """Lê o sensor de solo e devolve um percentual de 0 (SOIL_DRY_RAW) a 100
    (SOIL_WET_RAW).

    O percentual é relativo aos extremos de calibração do sensor e não
    equivale a umidade volumétrica.
    """
    return converter_para_pct(_ler_bruto(config.SOIL_ADS1115_CHANNEL))
