"""
edge/tests/test_soil_moisture.py

O que este arquivo verifica, em português simples:

Que a conversão do valor bruto do ADC (ADS1115) para uma porcentagem de
umidade do solo (edge/src/sensors/soil_moisture.py) está matematicamente
correta nos dois extremos (seco/saturado) e no meio da faixa, que o
resultado nunca sai do intervalo 0-100% mesmo com um valor bruto fora da
faixa calibrada (ex.: sensor descalibrado ou ruído elétrico), que uma
calibração inválida (seco e molhado com o mesmo valor bruto) dá um erro
claro em vez de uma divisão por zero, e que um canal inexistente é
recusado antes de tocar no barramento.

O smbus2 só conversa de verdade com o chip em hardware Raspberry Pi com
o ADS1115 conectado; edge/tests/conftest.py substitui a lib por um
dublê que devolve os dois bytes como o chip faria. A decodificação
desses bytes (big-endian, complemento de dois) roda de verdade aqui.
"""

import pytest

from edge.src import config
from edge.src.sensors import soil_moisture


@pytest.fixture(autouse=True)
def _calibracao_padrao(monkeypatch):
    monkeypatch.setattr(config, "SOIL_DRY_RAW", 18000)
    monkeypatch.setattr(config, "SOIL_WET_RAW", 8000)
    monkeypatch.setattr(config, "SOIL_ADS1115_CHANNEL", 1)


def test_seco_da_zero_por_cento(fake_ads1115):
    fake_ads1115.valor_bruto = 18000

    assert soil_moisture.ler_umidade_solo() == 0.0


def test_saturado_da_cem_por_cento(fake_ads1115):
    fake_ads1115.valor_bruto = 8000

    assert soil_moisture.ler_umidade_solo() == 100.0


def test_meio_da_faixa_da_cinquenta_por_cento(fake_ads1115):
    fake_ads1115.valor_bruto = 13000

    assert soil_moisture.ler_umidade_solo() == 50.0


def test_valor_fora_da_faixa_fica_limitado_entre_0_e_100(fake_ads1115):
    fake_ads1115.valor_bruto = 25000
    assert soil_moisture.ler_umidade_solo() == 0.0

    fake_ads1115.valor_bruto = 2000
    assert soil_moisture.ler_umidade_solo() == 100.0


def test_valor_negativo_do_adc_e_decodificado_como_negativo(fake_ads1115):
    """O ADS1115 devolve complemento de dois em 16 bits. Sem a conversão
    de sinal, -500 viraria 65036 e a umidade sairia como 0% (seco) em
    vez de 100% (saturado), invertendo a leitura."""
    fake_ads1115.valor_bruto = -500

    assert soil_moisture.ler_umidade_solo() == 100.0


def test_calibracao_invalida_da_erro_claro_em_vez_de_dividir_por_zero(monkeypatch):
    monkeypatch.setattr(config, "SOIL_DRY_RAW", 10000)
    monkeypatch.setattr(config, "SOIL_WET_RAW", 10000)

    with pytest.raises(RuntimeError, match="calibrado"):
        soil_moisture.ler_umidade_solo()


def test_canal_inexistente_da_erro_claro(monkeypatch, fake_ads1115):
    monkeypatch.setattr(config, "SOIL_ADS1115_CHANNEL", 7)

    with pytest.raises(RuntimeError, match="SOIL_ADS1115_CHANNEL"):
        soil_moisture.ler_umidade_solo()
