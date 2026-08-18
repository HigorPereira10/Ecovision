"""
edge/src/capture.py

Captura de imagem via Picamera2 (Camera Module 3), conforme Blueprint
v3.0. Usa autofoco programático (AfMode.Auto), decisão que
substituiu a Camera Module V2 (foco fixo ~1m) porque a distância real
de operação do EcoVision é de ~15cm.

Relação com o resto do sistema:
- Chamado por edge/src/main.py em cada ciclo de captura, entre
  ligar_led() e desligar_led() (edge/src/actuators/led_flash.py), para
  garantir que a foto é tirada com o flash aceso.
- A imagem capturada aqui alimenta edge/src/compress.py.
"""

import io

from libcamera import controls
from picamera2 import Picamera2

# Tempo de estabilização do autofoco antes de capturar (segundos).
_AUTOFOCUS_SETTLE_SECONDS = 0.3


def capturar_imagem() -> bytes:
    """Captura uma foto com autofoco PDAF e retorna os bytes crus (JPEG
    de resolução nativa, ainda não recomprimido — ver compress.py)."""
    picam2 = Picamera2()
    try:
        config = picam2.create_still_configuration()
        picam2.configure(config)
        picam2.set_controls({"AfMode": controls.AfModeEnum.Auto})

        picam2.start()
        picam2.autofocus_cycle()

        buffer = io.BytesIO()
        picam2.capture_file(buffer, format="jpeg")
        return buffer.getvalue()
    finally:
        picam2.stop()
        picam2.close()
