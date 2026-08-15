"""
edge/src/actuators/led_flash.py

Acionamento do Ring LED (flash dominante, 5V) através do MOSFET de
canal N, NUNCA ligar o LED diretamente ao GPIO.

Motivo (Blueprint v3.0, Fase 1, correção crítica): os pinos GPIO do
Raspberry Pi suportam no máximo ~16mA, e o Ring LED de 5V exige mais
corrente do que isso. O MOSFET funciona como chave digital: o GPIO
comanda o gate (baixa corrente), e o MOSFET permite a passagem da
corrente maior exigida pelo LED a partir da fonte 5V/3A dedicada.

Responsabilidades quando implementado:
- Configurar o pino GPIO ligado ao gate do MOSFET como saída.
- Acionar o LED por ~0,5s, sincronizado com a captura da foto
  (edge/src/capture.py).

Relação com o resto do sistema:
- Chamado por edge/src/main.py, imediatamente antes/durante a captura.
"""

# import RPi.GPIO as GPIO

# def acionar_led(pino_mosfet: int, duracao_segundos: float = 0.5) -> None:
#     """Liga o LED via MOSFET pelo tempo especificado e desliga em seguida."""
#     raise NotImplementedError
