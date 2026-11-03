"""
edge/src/sensores.py

Ciclo de SENSOR SEM FOTO, executado a cada 15 minutos via cron.

POR QUE EXISTE UM SEGUNDO CICLO
-------------------------------
O ciclo de main.py roda a cada 2 horas, e esse intervalo é ditado pela
FOTO: acionar o Ring LED, esperar o autofoco convergir (5,6 s a 27 s
medidos no dispositivo), comprimir 1,2 MB, subir para o Storage e rodar
a inferência TFLite. Ler o DHT22 e o sensor de solo leva 2 segundos e
produz três números.

Enquanto as duas coisas andavam juntas, a temperatura na tela inicial do
app podia ter 2 horas de idade, e não havia nada mais novo para buscar:
`leituras_ambientais.registro_imagem_id` era obrigatório no banco, então
leitura sem foto não existia. A migration 0008 do cloud removeu essa
amarra e abriu POST /leituras.

ESTE CICLO NÃO USA A FILA OFFLINE, DE PROPÓSITO
-----------------------------------------------
main.py enfileira em edge/src/fila/offline_queue.py antes de tentar a
rede, porque perder uma foto é perder um diagnóstico, e isso não se
recupera: aquele instante da planta passou.

Perder uma amostra de sensor custa quase nada. A próxima vem em 15
minutos, e uma série com um ponto faltando continua perfeitamente
legível, inclusive porque o gráfico já pula ponto sem medição. Enfileirar
traria fila em disco, drenagem, risco de acumular arquivo no cartão SD e
leitura chegando atrasada marcada como atual, tudo para proteger um dado
que se repõe sozinho.

Se a rede estiver fora, este ciclo loga e desiste. É a decisão certa
para este dado, e NÃO deve ser copiada para o ciclo da foto.

O LED NÃO É ACIONADO AQUI
-------------------------
Nada é fotografado, então acender o Ring LED seria consumo e desgaste
sem retorno. Isso também significa que este ciclo não depende do MOSFET
nem do GPIO18, que é justamente a linha comprometida na placa soldada
(ver docs/hardware/diagnostico-placa-2026-10-31.md).
"""

import logging
import sys
import uuid
from pathlib import Path

if __name__ == "__main__":
    # Mesma razão de main.py: o cron invoca este arquivo direto, então a
    # raiz do repositório não entra em sys.path sozinha.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import requests

from edge.src import config
from edge.src.sensors import dht22, soil_moisture

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ecovision.edge.sensores")


def ler_sensores() -> dict:
    """Lê DHT22 e sensor de solo, com tolerância a falha individual.

    Mesma política de main.py._ler_sensores(): sensor que falha vira
    None naquele campo em vez de abortar o ciclo. Aqui a razão é
    diferente, porém. Lá, era para não perder a foto por causa de um
    sensor instável. Aqui, é para o servidor receber "o ciclo das 14:15
    rodou e o DHT22 não respondeu", que é informação diferente de "não
    houve ciclo das 14:15": sem ela, a tela não distingue sensor
    quebrado de Pi desligado e segue exibindo a última leitura boa como
    se fosse a atual.
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
    """Manda as leituras para POST /leituras. Devolve se a API aceitou.

    A idempotency_key é gerada aqui, por ciclo. Sem fila offline não há
    reenvio automático, então na prática ela protege contra duas
    execuções simultâneas do cron, que acontece quando um ciclo demora
    mais do que o intervalo entre eles.
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
        # Sem retry e sem fila: ver o cabeçalho deste módulo. A próxima
        # amostra vem em 15 minutos.
        logger.warning("Falha de rede ao enviar a leitura.", exc_info=True)
        return False

    if not resposta.ok:
        logger.warning(
            "API recusou a leitura: HTTP %d, %s", resposta.status_code, resposta.text[:200]
        )
        return False

    return True


def ciclo_de_sensores() -> None:
    """Executa um ciclo: ler sensores -> enviar. Sem LED, sem foto, sem fila."""
    leituras = ler_sensores()
    logger.info("Leituras dos sensores: %s", leituras)

    if enviar_leitura(leituras):
        logger.info("Leitura registrada na API.")


if __name__ == "__main__":
    ciclo_de_sensores()
