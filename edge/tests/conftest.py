"""
Configuração compartilhada dos testes de edge/src.

Define as variáveis de ambiente exigidas por edge/src/config.py e
substitui as bibliotecas de hardware (RPi.GPIO, board, adafruit_dht,
smbus2) por dublês, para a suíte rodar fora do Raspberry Pi.
"""

import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

os.environ.setdefault("API_BASE_URL", "http://testserver.invalid")
os.environ.setdefault("DEVICE_API_KEY", "chave-de-teste")
os.environ.setdefault("DEVICE_ID", "pi-teste-automatizado")


class EstadoAds1115:
    """Valor bruto que o ADS1115 falso devolve na próxima conversão.

    O código sob teste continua montando a configuração e decodificando os
    dois bytes reais, o que cobre o protocolo e não só a conversão final.
    """

    valor_bruto = 0


class _MensagemI2cFalsa:
    """Imita o objeto devolvido por i2c_msg.write() / i2c_msg.read()."""

    def __init__(self, endereco: int, dados=None, tamanho: int = 0):
        self.endereco = endereco
        self.dados = list(dados or [])
        self.tamanho = tamanho

    def __iter__(self):
        return iter(self.dados)


def _montar_smbus2_falso() -> types.ModuleType:
    """ADS1115 falso no barramento I2C.

    Devolve EstadoAds1115.valor_bruto em complemento de dois, big-endian,
    como o chip.
    """

    class _I2cMsgFalso:
        @staticmethod
        def write(endereco, dados):
            return _MensagemI2cFalsa(endereco, dados=dados)

        @staticmethod
        def read(endereco, tamanho):
            return _MensagemI2cFalsa(endereco, tamanho=tamanho)

    class _SMBusFalso:
        def __init__(self, barramento):
            self.barramento = barramento

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def i2c_rdwr(self, *mensagens):
            for mensagem in mensagens:
                if mensagem.tamanho:
                    bruto = EstadoAds1115.valor_bruto & 0xFFFF
                    mensagem.dados = [(bruto >> 8) & 0xFF, bruto & 0xFF]

    modulo = types.ModuleType("smbus2")
    modulo.SMBus = _SMBusFalso
    modulo.i2c_msg = _I2cMsgFalso
    return modulo


def _instalar_fakes_de_hardware() -> None:
    """Registra os dublês de RPi.GPIO, board, adafruit_dht e smbus2 em
    sys.modules antes de os módulos de edge/src serem importados."""
    fake_gpio = MagicMock(name="RPi.GPIO")
    fake_gpio.BCM = "BCM"
    fake_gpio.OUT = "OUT"
    fake_gpio.HIGH = 1
    fake_gpio.LOW = 0
    fake_rpi = types.ModuleType("RPi")
    fake_rpi.GPIO = fake_gpio
    sys.modules["RPi"] = fake_rpi
    sys.modules["RPi.GPIO"] = fake_gpio

    fake_board = types.ModuleType("board")
    for nome_pino in ("D4", "D18", "D22", "D23", "D24", "D27"):
        setattr(fake_board, nome_pino, nome_pino)
    fake_board.SCL = "SCL"
    fake_board.SDA = "SDA"
    sys.modules["board"] = fake_board

    fake_adafruit_dht = types.ModuleType("adafruit_dht")
    fake_adafruit_dht.DHT22 = MagicMock(name="adafruit_dht.DHT22")
    sys.modules["adafruit_dht"] = fake_adafruit_dht

    sys.modules["smbus2"] = _montar_smbus2_falso()


_instalar_fakes_de_hardware()


@pytest.fixture
def fake_gpio():
    """RPi.GPIO falso, usado pelos testes de led_flash.py."""
    modulo = sys.modules["RPi.GPIO"]
    modulo.reset_mock()
    yield modulo


@pytest.fixture
def fake_dht22_classe():
    """adafruit_dht.DHT22 falso, usado pelos testes de dht22.py."""
    classe = sys.modules["adafruit_dht"].DHT22
    classe.reset_mock(return_value=True, side_effect=True)
    yield classe


@pytest.fixture
def fake_ads1115():
    """ADS1115 falso, usado pelos testes de soil_moisture.py.

    O teste define fake_ads1115.valor_bruto; o código sob teste decodifica
    os bytes devolvidos pelo chip simulado.
    """
    EstadoAds1115.valor_bruto = 0
    yield EstadoAds1115
    EstadoAds1115.valor_bruto = 0
