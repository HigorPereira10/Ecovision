"""
Testes de edge/src/actuators/led_flash.py: níveis enviados ao GPIO,
configuração única do pino e LED sempre desligado ao final, mesmo em caso
de erro durante a captura.
"""

import pytest

from edge.src.actuators import led_flash


@pytest.fixture(autouse=True)
def _pinos_limpos(fake_gpio):
    led_flash._pinos_configurados.clear()
    yield


def test_ligar_led_configura_o_pino_e_manda_nivel_alto(fake_gpio):
    led_flash.ligar_led(18)

    fake_gpio.setmode.assert_called_once_with(fake_gpio.BCM)
    fake_gpio.setup.assert_called_once_with(18, fake_gpio.OUT, initial=fake_gpio.LOW)
    fake_gpio.output.assert_called_once_with(18, fake_gpio.HIGH)


def test_desligar_led_manda_nivel_baixo(fake_gpio):
    led_flash.desligar_led(18)

    fake_gpio.output.assert_called_once_with(18, fake_gpio.LOW)


def test_pino_so_e_configurado_uma_vez_mesmo_usado_varias_vezes(fake_gpio):
    led_flash.ligar_led(18)
    led_flash.desligar_led(18)
    led_flash.ligar_led(18)

    assert fake_gpio.setup.call_count == 1


def test_pinos_diferentes_sao_configurados_separadamente(fake_gpio):
    led_flash.ligar_led(18)
    led_flash.ligar_led(23)

    assert fake_gpio.setup.call_count == 2


def test_acionar_led_liga_e_depois_desliga_o_mesmo_pino(fake_gpio):
    led_flash.acionar_led(18, duracao_segundos=0)

    assert fake_gpio.output.call_args_list[0].args == (18, fake_gpio.HIGH)
    assert fake_gpio.output.call_args_list[-1].args == (18, fake_gpio.LOW)


def test_acionar_led_desliga_o_led_mesmo_se_a_espera_falhar(fake_gpio, monkeypatch):
    def _sleep_com_erro(segundos):
        raise RuntimeError("falha simulada durante o flash")

    monkeypatch.setattr(led_flash.time, "sleep", _sleep_com_erro)

    with pytest.raises(RuntimeError):
        led_flash.acionar_led(18, duracao_segundos=0.5)

    assert fake_gpio.output.call_args_list[-1].args == (18, fake_gpio.LOW)
