"""
Captura de imagem pela Camera Module 3 (Picamera2), em resolução nativa.

O foco é fixado em CAMERA_FOCUS_CM em vez do autofoco, por três motivos:
escala constante da folha entre capturas, nenhum risco de o foco se
prender ao fundo e menos tempo com o LED aceso. LensPosition é expresso em
dioptrias (100 / centímetros); a lente aceita de 0 (infinito) a 15
(6,7 cm). Com CAMERA_FOCUS_CM igual a zero, usa o autofoco.
"""

import io
import logging

from libcamera import controls
from picamera2 import Picamera2

from edge.src import config

logger = logging.getLogger("ecovision.edge.capture")

# Faixa aceita pela lente, em dioptrias (15 dioptrias = 6,7 cm).
_DIOPTRIAS_MINIMAS = 0.0
_DIOPTRIAS_MAXIMAS = 15.0


def _controles_de_foco() -> dict:
    """Traduz CAMERA_FOCUS_CM nos controles da lente.

    Usa o autofoco quando a distância não está configurada ou está fora do
    alcance da lente, com aviso no log.
    """
    distancia_cm = config.CAMERA_FOCUS_CM
    if distancia_cm <= 0:
        return {"AfMode": controls.AfModeEnum.Auto}

    dioptrias = 100.0 / distancia_cm
    if not (_DIOPTRIAS_MINIMAS <= dioptrias <= _DIOPTRIAS_MAXIMAS):
        logger.warning(
            "CAMERA_FOCUS_CM=%.1f cm está fora do alcance da lente "
            "(mínimo %.1f cm). Usando autofoco neste ciclo.",
            distancia_cm, 100.0 / _DIOPTRIAS_MAXIMAS,
        )
        return {"AfMode": controls.AfModeEnum.Auto}

    return {
        "AfMode": controls.AfModeEnum.Manual,
        "LensPosition": dioptrias,
    }


def capturar_imagem() -> bytes:
    """Captura uma foto e devolve os bytes JPEG em resolução nativa, ainda
    não recomprimidos (ver compress.py)."""
    picam2 = Picamera2()
    try:
        picam2.configure(picam2.create_still_configuration())
        foco = _controles_de_foco()
        picam2.set_controls(foco)

        picam2.start()
        if foco["AfMode"] == controls.AfModeEnum.Auto:
            picam2.autofocus_cycle()

        buffer = io.BytesIO()
        picam2.capture_file(buffer, format="jpeg")
        return buffer.getvalue()
    finally:
        picam2.stop()
        picam2.close()
