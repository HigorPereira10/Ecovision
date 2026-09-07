"""
edge/tests/test_soil_moisture.py

O que este arquivo verifica, em português simples:

Que a conversão do valor bruto do ADC (ADS1115) para uma porcentagem de
umidade do solo (edge/src/sensors/soil_moisture.py) está matematicamente
correta nos dois extremos (seco/saturado) e no meio da faixa, que o
resultado nunca sai do intervalo 0-100% mesmo com um valor bruto fora da
faixa calibrada (ex.: sensor descalibrado ou ruído elétrico), e que uma
calibração inválida (seco e molhado com o mesmo valor bruto) dá um erro
claro em vez de uma divisão por zero.

As libs board/busio/adafruit_ads1x15 só existem de verdade em hardware
Raspberry Pi com o ADS1115 conectado; edge/tests/conftest.py substitui
essas libs por dublês antes de qualquer teste rodar.
"""

import pytest

from edge.src import config
from edge.src.sensors import soil_moisture


def _configurar_leitura_bruta(fake_analog_in_classe, valor_bruto):
    instancia_canal = fake_analog_in_classe.return_value
    instancia_canal.value = valor_bruto


@pytest.fixture(autouse=True)
def _calibracao_padrao(monkeypatch):
    monkeypatch.setattr(config, "SOIL_DRY_RAW", 18000)
    monkeypatch.setattr(config, "SOIL_WET_RAW", 8000)


def test_seco_da_zero_por_cento(fake_analog_in_classe):
    _configurar_leitura_bruta(fake_analog_in_classe, 18000)

    assert soil_moisture.ler_umidade_solo() == 0.0


def test_saturado_da_cem_por_cento(fake_analog_in_classe):
    _configurar_leitura_bruta(fake_analog_in_classe, 8000)

    assert soil_moisture.ler_umidade_solo() == 100.0


def test_meio_da_faixa_da_cinquenta_por_cento(fake_analog_in_classe):
    _configurar_leitura_bruta(fake_analog_in_classe, 13000)

    assert soil_moisture.ler_umidade_solo() == 50.0


def test_valor_fora_da_faixa_fica_limitado_entre_0_e_100(fake_analog_in_classe):
    _configurar_leitura_bruta(fake_analog_in_classe, 25000)
    assert soil_moisture.ler_umidade_solo() == 0.0

    _configurar_leitura_bruta(fake_analog_in_classe, 2000)
    assert soil_moisture.ler_umidade_solo() == 100.0


def test_calibracao_invalida_da_erro_claro_em_vez_de_dividir_por_zero(fake_analog_in_classe, monkeypatch):
    monkeypatch.setattr(config, "SOIL_DRY_RAW", 10000)
    monkeypatch.setattr(config, "SOIL_WET_RAW", 10000)
    _configurar_leitura_bruta(fake_analog_in_classe, 10000)

    with pytest.raises(RuntimeError, match="calibrado"):
        soil_moisture.ler_umidade_solo()
