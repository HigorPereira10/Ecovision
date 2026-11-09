"""
Acionamento do LED de iluminação pelo MOSFET de canal N.

O LED nunca deve ser ligado diretamente ao GPIO, que fornece no máximo
cerca de 16 mA. ligar_led() e desligar_led() envolvem a captura da foto;
acionar_led() liga, espera e desliga, para testes manuais.
"""

import time

import RPi.GPIO as GPIO

_pinos_configurados: set[int] = set()


def _garantir_configurado(pino: int) -> None:
    if pino in _pinos_configurados:
        return
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pino, GPIO.OUT, initial=GPIO.LOW)
    _pinos_configurados.add(pino)


def ligar_led(pino: int) -> None:
    """Coloca a porta do MOSFET em nível alto, ligando o LED."""
    _garantir_configurado(pino)
    GPIO.output(pino, GPIO.HIGH)


def desligar_led(pino: int) -> None:
    """Coloca a porta do MOSFET em nível baixo, desligando o LED."""
    _garantir_configurado(pino)
    GPIO.output(pino, GPIO.LOW)


def acionar_led(pino_mosfet: int, duracao_segundos: float = 0.5) -> None:
    """Liga o LED via MOSFET pelo tempo especificado e desliga em seguida."""
    ligar_led(pino_mosfet)
    try:
        time.sleep(duracao_segundos)
    finally:
        desligar_led(pino_mosfet)
