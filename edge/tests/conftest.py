"""
edge/tests/conftest.py

Configuração compartilhada dos testes automatizados de edge/src/.

edge/src/config.py exige algumas variáveis de ambiente (URL da API,
chave do dispositivo) assim que é importado. No dispositivo real elas
vêm do arquivo edge/.env. Para os testes rodarem sem precisar desse
arquivo nem de um Raspberry Pi de verdade, este conftest define valores
de teste ANTES de qualquer teste ser coletado.

Como rodar (dentro do WSL/Ubuntu, já que edge/src/queue/offline_queue.py
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


def _instalar_fakes_de_hardware() -> None:
    """Substitui RPi.GPIO, board, busio e as libs do DHT22/ADS1115 por
    dublês em sys.modules, ANTES de qualquer teste importar os módulos
    de edge/src/actuators e edge/src/sensors. Essas libs só existem de
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

    fake_busio = types.ModuleType("busio")
    fake_busio.I2C = MagicMock(name="busio.I2C")
    sys.modules["busio"] = fake_busio

    fake_adafruit_dht = types.ModuleType("adafruit_dht")
    fake_adafruit_dht.DHT22 = MagicMock(name="adafruit_dht.DHT22")
    sys.modules["adafruit_dht"] = fake_adafruit_dht

    sys.modules["adafruit_ads1x15"] = types.ModuleType("adafruit_ads1x15")

    fake_ads1115 = types.ModuleType("adafruit_ads1x15.ads1115")
    fake_ads1115.P0, fake_ads1115.P1, fake_ads1115.P2, fake_ads1115.P3 = "P0", "P1", "P2", "P3"
    fake_ads1115.ADS1115 = MagicMock(name="ADS1115")
    sys.modules["adafruit_ads1x15.ads1115"] = fake_ads1115

    fake_analog_in_mod = types.ModuleType("adafruit_ads1x15.analog_in")
    fake_analog_in_mod.AnalogIn = MagicMock(name="AnalogIn")
    sys.modules["adafruit_ads1x15.analog_in"] = fake_analog_in_mod


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
def fake_analog_in_classe():
    """AnalogIn falso, usado pelos testes de edge/src/sensors/soil_moisture.py."""
    classe = sys.modules["adafruit_ads1x15.analog_in"].AnalogIn
    classe.reset_mock(return_value=True, side_effect=True)
    yield classe
