"""
edge/src/capture.py

Captura de imagem via Picamera2 (Camera Module 3). A lente com foco
motorizado foi escolhida no lugar da Camera V2 (foco fixo em ~1m)
porque a distância de operação do EcoVision é de poucos centímetros
(ver ADR 0001).

POR QUE FOCO FIXO E NÃO AUTOFOCO
--------------------------------
O autofoco funciona: medido em 2026-11-01, convergia em AfState 2
(focado) em todos os ciclos. O problema não é ele errar, são três
outras coisas.

1. ESCALA CONSTANTE. O autofoco pode pousar em planos diferentes
   conforme o que estiver mais contrastado no quadro, e aí o mesmo
   folíolo chega ao modelo com tamanhos diferentes entre uma captura e
   a seguinte. Para a série temporal servir como conjunto de dados
   depois, a escala precisa ser a mesma em todas as fotos.

2. RISCO DE PRENDER NO FUNDO. A cena tem parede e fios atrás da
   planta. Nada impede o autofoco de escolher esse plano num ciclo em
   que a folha esteja balançando.

3. TEMPO. O autofoco respondia por cerca de 3,8s de cada ciclo, com o
   LED aceso o tempo todo. Fixar o foco devolve esse tempo e reduz a
   dissipação no resistor em série do LED.

LensPosition é expresso em DIOPTRIAS, ou seja 1/metro, não em
centímetros: 20 cm viram 100/20 = 5,0. A lente desta câmera aceita de
0 (infinito) a 15 (6,7 cm), e valor fora da faixa é recusado aqui em
vez de ser silenciosamente saturado pelo driver.

Com CAMERA_FOCUS_CM igual a zero o módulo volta ao autofoco, que é o
comportamento certo para um dispositivo ainda sem a distância medida.

Relação com o resto do sistema:
- Chamado por edge/src/main.py em cada ciclo de captura, entre
  ligar_led() e desligar_led() (edge/src/actuators/led_flash.py), para
  garantir que a foto é tirada com o flash aceso.
- A imagem capturada aqui alimenta edge/src/compress.py.
- A distância vem de CAMERA_FOCUS_CM (edge/src/config.py), definida no
  .env de cada dispositivo.
"""

import io
import logging

from libcamera import controls
from picamera2 import Picamera2

from edge.src import config

logger = logging.getLogger("ecovision.edge.capture")

# Faixa aceita pela lente da Camera Module 3, em dioptrias. O limite
# superior é o que impede pedir uma distância que a lente não alcança:
# 15 dioptrias são 6,7 cm.
_DIOPTRIAS_MINIMAS = 0.0
_DIOPTRIAS_MAXIMAS = 15.0


def _controles_de_foco() -> dict:
    """Traduz CAMERA_FOCUS_CM nos controles da lente.

    Devolve autofoco quando a distância não está configurada, e também
    quando está fora do que a lente alcança: nesse caso é melhor uma
    foto focada pelo autofoco, com um aviso no log, do que uma foto
    garantidamente desfocada por um valor saturado em silêncio.
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
    """Captura uma foto e retorna os bytes crus (JPEG de resolução
    nativa, ainda não recomprimido, ver compress.py).

    Usa foco fixo na distância de CAMERA_FOCUS_CM. Sem ela configurada,
    cai no autofoco PDAF (ver _controles_de_foco)."""
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
