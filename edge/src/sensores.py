"""
Ciclo de leitura dos sensores, sem foto, executado pelo cron a cada 15 minutos.

Não usa a fila local: uma amostra perdida é reposta pela seguinte, e
enfileirar faria leituras antigas chegarem como atuais. Sem rede, o ciclo
registra a falha e encerra. O LED não é acionado.
"""

import logging
import sys
import uuid
from pathlib import Path

if __name__ == "__main__":
    # O cron executa este arquivo diretamente (ver main.py).
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import requests

from edge.src import config
from edge.src.sensors import dht22, soil_moisture

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ecovision.edge.sensores")


def ler_sensores() -> dict:
    """Lê DHT22 e sensor de solo; um sensor que falha vira None.

    O envio com campos nulos permite à API distinguir sensor com falha de
    dispositivo desligado.
    """
    leituras: dict = {}

    try:
        leituras.update(dht22.ler_dht22(config.DHT22_PIN))
    except Exception:
        logger.warning("Falha ao ler o DHT22, enviando sem essa leitura.", exc_info=True)
        leituras["temperatura_c"] = None
        leituras["umidade_ar_pct"] = None

    try:
        leituras["umidade_solo_pct"] = soil_moisture.ler_umidade_solo()
    except Exception:
        logger.warning(
            "Falha ao ler o sensor de solo, enviando sem essa leitura.", exc_info=True
        )
        leituras["umidade_solo_pct"] = None

    return leituras


def enviar_leitura(leituras: dict) -> bool:
    """Envia as leituras para POST /leituras e devolve se a API aceitou.

    A idempotency_key evita duplicidade quando duas execuções do cron se
    sobrepõem.
    """
    corpo = {
        "device_id": config.DEVICE_ID,
        "idempotency_key": str(uuid.uuid4()),
        "temperatura_c": leituras.get("temperatura_c"),
        "umidade_ar_pct": leituras.get("umidade_ar_pct"),
        "umidade_solo_pct": leituras.get("umidade_solo_pct"),
    }

    try:
        resposta = requests.post(
            f"{config.API_BASE_URL}/leituras",
            json=corpo,
            headers={"Authorization": config.DEVICE_API_KEY},
            timeout=config.UPLOAD_TIMEOUT_SECONDS,
        )
    except requests.RequestException:
        # Sem nova tentativa: a próxima amostra vem em 15 minutos.
        logger.warning("Falha de rede ao enviar a leitura.", exc_info=True)
        return False

    if not resposta.ok:
        logger.warning(
            "API recusou a leitura: HTTP %d, %s", resposta.status_code, resposta.text[:200]
        )
        return False

    return True


def ciclo_de_sensores() -> None:
    """Executa um ciclo: leitura dos sensores e envio, sem LED, foto ou fila."""
    leituras = ler_sensores()
    logger.info("Leituras dos sensores: %s", leituras)

    if enviar_leitura(leituras):
        logger.info("Leitura registrada na API.")


if __name__ == "__main__":
    ciclo_de_sensores()
