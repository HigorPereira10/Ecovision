"""
edge/src/actuators/led_flash.py

Acionamento do Ring LED (flash dominante, 5V) através do MOSFET de
canal N, NUNCA ligar o LED diretamente ao GPIO.

Motivo (Blueprint v3.0, Fase 1, correção crítica): os pinos GPIO do
Raspberry Pi suportam no máximo ~16mA, e o Ring LED de 5V exige mais
corrente do que isso. O MOSFET funciona como chave digital: o GPIO
comanda o gate (baixa corrente), e o MOSFET permite a passagem da
corrente maior exigida pelo LED a partir da fonte 5V/3A dedicada.

API: ligar_led()/desligar_led() são as primitivas usadas por main.py para
abraçar exatamente a chamada de captura da foto (sincronismo real com a
câmera). acionar_led() é um atalho bloqueante (liga, espera, desliga) para
uso avulso/teste manual do LED sem câmera.

Relação com o resto do sistema:
- Chamado por edge/src/main.py, imediatamente antes/durante a captura.
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
    """Coloca o gate do MOSFET em nível alto, ligando o Ring LED."""
    _garantir_configurado(pino)
    GPIO.output(pino, GPIO.HIGH)


def desligar_led(pino: int) -> None:
    """Coloca o gate do MOSFET em nível baixo, desligando o Ring LED."""
    _garantir_configurado(pino)
    GPIO.output(pino, GPIO.LOW)


def acionar_led(pino_mosfet: int, duracao_segundos: float = 0.5) -> None:
    """Liga o LED via MOSFET pelo tempo especificado e desliga em seguida."""
    ligar_led(pino_mosfet)
    try:
        time.sleep(duracao_segundos)
    finally:
        desligar_led(pino_mosfet)
