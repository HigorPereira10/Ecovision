"""
edge/src/capture.py

Captura de imagem via Picamera2 (Camera Module 3), conforme Blueprint
v3.0. Usa autofoco programático (AfMode.AUTO), decisão que
substituiu a Camera Module V2 (foco fixo ~1m) porque a distância real
de operação do EcoVision é de ~15cm.

Responsabilidades quando implementado:
- Inicializar a Picamera2 com o modo de autofoco correto.
- Disparar a captura sincronizada com o acionamento do Ring LED
  (actuators/led_flash.py).
- Retornar a imagem crua (antes da compressão, feita em compress.py).

Relação com o resto do sistema:
- Chamado por edge/src/main.py em cada ciclo de captura.
- A imagem capturada aqui alimenta edge/src/compress.py.
"""

# from picamera2 import Picamera2

# def capturar_imagem() -> bytes:
#     """Captura uma foto com autofoco PDAF e retorna os bytes crus."""
#     raise NotImplementedError
