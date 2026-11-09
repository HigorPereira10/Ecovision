"""
Ciclo de captura, executado pelo cron a cada 2 horas.

1. Lê os sensores; a falha de um sensor não impede a captura da foto.
2. Aciona o LED e aguarda LED_FLASH_DURATION_SECONDS antes da foto.
3. Captura a imagem e a recomprime em JPEG.
4. Grava imagem e leituras na fila local.
5. Tenta drenar a fila (melhor esforço; o cron de 15 minutos garante o envio).
"""

import logging
import sys
import time
from pathlib import Path

if __name__ == "__main__":
    # O cron executa este arquivo diretamente; a raiz do repositório
    # precisa estar em sys.path para os imports edge.src.*.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from edge.src import capture, compress, config
from edge.src.actuators import led_flash
from edge.src.fila import offline_queue
from edge.src.sensors import dht22, soil_moisture
from edge.src.upload import uploader

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ecovision.edge")


def _ler_sensores() -> dict:
    """Lê DHT22 e sensor de solo; um sensor que falha vira None, sem
    interromper o ciclo."""
    leituras: dict = {}

    try:
        leituras.update(dht22.ler_dht22(config.DHT22_PIN))
    except Exception:
        logger.warning("Falha ao ler o DHT22, seguindo sem essa leitura.", exc_info=True)
        leituras["temperatura_c"] = None
        leituras["umidade_ar_pct"] = None

    try:
        leituras["umidade_solo_pct"] = soil_moisture.ler_umidade_solo()
    except Exception:
        logger.warning("Falha ao ler o sensor de solo, seguindo sem essa leitura.", exc_info=True)
        leituras["umidade_solo_pct"] = None

    return leituras


def ciclo_de_captura() -> None:
    """Executa um ciclo completo: sensores, LED, foto, compressão, fila e envio."""
    leituras = _ler_sensores()
    logger.info("Leituras dos sensores: %s", leituras)

    led_flash.ligar_led(config.LED_MOSFET_PIN)
    try:
        # O LED fica aceso durante toda a captura; esta espera só deixa o
        # brilho estabilizar antes do disparo.
        time.sleep(config.LED_FLASH_DURATION_SECONDS)
        imagem_crua = capture.capturar_imagem()
    finally:
        led_flash.desligar_led(config.LED_MOSFET_PIN)

    imagem_comprimida = compress.comprimir_imagem(imagem_crua, quality=config.JPEG_QUALITY)
    logger.info("Imagem comprimida: %d bytes", len(imagem_comprimida))

    registro_id = offline_queue.enfileirar(imagem_comprimida, leituras)
    logger.info("Registro %s enfileirado.", registro_id)

    try:
        uploader.drenar_fila_e_enviar()
    except Exception:
        # Melhor esforço: sem rede agora, o cron de drenagem tenta depois.
        logger.warning("Falha ao tentar drenar a fila imediatamente.", exc_info=True)


if __name__ == "__main__":
    ciclo_de_captura()
