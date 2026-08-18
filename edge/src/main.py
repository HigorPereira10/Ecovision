"""
edge/src/main.py

Orquestrador principal do ciclo de captura, executado periodicamente
via cron (Blueprint v3.0, Fase 2: agendamento de captura a cada 2h).

Fluxo:
1. Ler sensores (sensors/dht22.py, sensors/soil_moisture.py).
2. Acionar o Ring LED via MOSFET (actuators/led_flash.py), abraçando a
   captura da foto para garantir sincronismo real entre flash e câmera.
3. Capturar a foto (capture.py) com autofoco.
4. Comprimir a imagem (compress.py).
5. Enfileirar o pacote (imagem + leituras) na fila offline
   (queue/offline_queue.py).
6. Tentar drenar a fila e enviar para a API (upload/uploader.py), de
   forma best-effort — uma falha de rede aqui não deve derrubar o cron
   de captura, já que a drenagem "de verdade" está garantida pelo cron
   separado de 15min (crontab.example).

Relação com o resto do sistema:
- É o script chamado pelo `crontab.example`.
- Depende de todos os demais módulos de edge/src/.
- O destino final dos dados é o endpoint POST /diagnostico da API
  (cloud/app/api/routes/diagnostico.py).
"""

import logging
import sys
from pathlib import Path

if __name__ == "__main__":
    # Cron invoca este arquivo diretamente (`python edge/src/main.py`),
    # então a raiz do repositório não entra em sys.path por padrão — precisa
    # ser adicionada manualmente para os imports `edge.src.*` funcionarem.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from edge.src import capture, compress, config
from edge.src.actuators import led_flash
from edge.src.queue import offline_queue
from edge.src.sensors import dht22, soil_moisture
from edge.src.upload import uploader

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ecovision.edge")


def ciclo_de_captura() -> None:
    """Executa um ciclo completo: sensores -> LED -> foto -> compressão -> fila -> upload."""
    leituras = {
        **dht22.ler_dht22(config.DHT22_PIN),
        "umidade_solo_pct": soil_moisture.ler_umidade_solo(),
    }
    logger.info("Leituras dos sensores: %s", leituras)

    led_flash.ligar_led(config.LED_MOSFET_PIN)
    try:
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
        # Melhor esforço: se a rede estiver fora agora, o cron de
        # drenagem (15min) tenta de novo depois. O ciclo de captura não
        # deve falhar por causa disso.
        logger.warning("Falha ao tentar drenar a fila imediatamente.", exc_info=True)


if __name__ == "__main__":
    ciclo_de_captura()
