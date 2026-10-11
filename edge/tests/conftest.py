"""
edge/tests/conftest.py

Configuração compartilhada dos testes automatizados de edge/src/.

edge/src/config.py exige algumas variáveis de ambiente (URL da API,
chave do dispositivo) assim que é importado. No dispositivo real elas
vêm do arquivo edge/.env. Para os testes rodarem sem precisar desse
arquivo nem de um Raspberry Pi de verdade, este conftest define valores
de teste ANTES de qualquer teste ser coletado.

Como rodar (dentro do WSL/Ubuntu, já que edge/src/fila/offline_queue.py
usa fcntl, um recurso que só existe em Linux/Unix, não no Python do
Windows):

    cd Ecovision
    pip install -r edge/tests/requirements-test.txt
    pytest edge/tests -v
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

    Os testes de soil_moisture.py escrevem aqui em vez de simular a
    leitura inteira, mas o código sob teste continua montando a
    configuração e decodificando os dois bytes de verdade. Isso é
    proposital: o dublê anterior substituía a conversão inteira, e por
    isso não pegou que a API da Adafruit tinha mudado de `ads1115.P0`
    para `ads1x15.Pin.A0`, deixando os testes verdes enquanto o
    Raspberry Pi quebrava.
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
    """ADS1115 falso que responde pelo barramento I2C.

    O smbus2 real só funciona onde existe /dev/i2c-N com o módulo
    conectado. Este dublê devolve EstadoAds1115.valor_bruto codificado
    em complemento de dois, big-endian, como o chip faria.
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
    """Substitui RPi.GPIO, board, adafruit_dht e smbus2 por dublês em
    sys.modules, ANTES de qualquer teste importar os módulos de
    edge/src/actuators e edge/src/sensors. Essas libs só existem de
    verdade (e só instalam) em hardware Raspberry Pi com os componentes
    físicos conectados; sem esse dublê, os testes desses módulos nem
    conseguiriam importar o código fora do Pi."""
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
    """RPi.GPIO falso, usado pelos testes de edge/src/actuators/led_flash.py."""
    modulo = sys.modules["RPi.GPIO"]
    modulo.reset_mock()
    yield modulo


@pytest.fixture
def fake_dht22_classe():
    """adafruit_dht.DHT22 falso, usado pelos testes de edge/src/sensors/dht22.py."""
    classe = sys.modules["adafruit_dht"].DHT22
    classe.reset_mock(return_value=True, side_effect=True)
    yield classe


@pytest.fixture
def fake_ads1115():
    """ADS1115 falso, usado pelos testes de edge/src/sensors/soil_moisture.py.

    O teste define `fake_ads1115.valor_bruto`, e o código sob teste faz
    a conversão para porcentagem passando pela decodificação real dos
    dois bytes devolvidos pelo chip.
    """
    EstadoAds1115.valor_bruto = 0
    yield EstadoAds1115
    EstadoAds1115.valor_bruto = 0
