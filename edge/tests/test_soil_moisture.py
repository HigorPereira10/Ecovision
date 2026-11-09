"""
Testes de edge/src/sensors/soil_moisture.py: conversão do valor bruto em
porcentagem, limite de 0 a 100%, recusa de calibração inválida e de canal
inexistente, e decodificação dos bytes do ADS1115.
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
    """O ADS1115 devolve complemento de dois em 16 bits; sem a conversão
    de sinal, a umidade sairia invertida."""
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
