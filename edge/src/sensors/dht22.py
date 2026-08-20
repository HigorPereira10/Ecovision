"""
edge/src/sensors/dht22.py

Leitura do sensor DHT22 (temperatura/umidade do ar, protocolo 1-Wire),
via adafruit-circuitpython-dht (Blueprint v3.0, Fase 1 e 2).

Precisão do sensor: ±0.5°C / ±2-5%RH. O BoM prevê 2 unidades (1 sobressalente).

Biblioteca: usamos adafruit-circuitpython-dht (import adafruit_dht) em vez
do antigo Adafruit_DHT — este último está descontinuado e tem histórico de
falha de instalação em versões recentes do Raspberry Pi OS. A nova lib
também deixa a integração consistente com o ADS1115 (mesma linha
CircuitPython/Blinka, ver soil_moisture.py). Requer o pacote de sistema
libgpiod2 (instalado em edge/scripts/install.sh).

adafruit_dht levanta RuntimeError com frequência em leituras normais
(erros de checksum/timing são esperados no protocolo 1-Wire do DHT22) —
por isso o retry manual abaixo, em vez de tratar RuntimeError como falha
definitiva na primeira tentativa.

Relação com o resto do sistema:
- Chamado por edge/src/main.py em cada ciclo de captura.
- A leitura resultante entra no pacote enviado para o endpoint
  /diagnostico e é persistida na tabela leituras_ambientais
  (cloud/app/db/models.py).
"""

import time

import adafruit_dht
import board

_RETRIES = 5
_RETRY_DELAY_SECONDS = 2.0


def _pino_board(pino: int):
    """Converte um pino BCM (ex.: 4) no objeto board.D4 esperado pela lib."""
    nome_pino = f"D{pino}"
    if not hasattr(board, nome_pino):
        raise RuntimeError(
            f"Pino BCM {pino} não mapeado em board.{nome_pino} "
            f"(verifique o valor de DHT22_PIN)."
        )
    return getattr(board, nome_pino)


def ler_dht22(pino: int) -> dict:
    """Lê temperatura e umidade do ar. Levanta RuntimeError se falhar em
    todas as tentativas (o DHT22 falha pontualmente com frequência —
    isso é esperado, não indica sensor com defeito)."""
    dispositivo = adafruit_dht.DHT22(_pino_board(pino))
    try:
        ultimo_erro: Exception | None = None
        for _ in range(_RETRIES):
            try:
                temperatura_c = dispositivo.temperature
                umidade_ar_pct = dispositivo.humidity
            except RuntimeError as erro:
                ultimo_erro = erro
                time.sleep(_RETRY_DELAY_SECONDS)
                continue

            if temperatura_c is not None and umidade_ar_pct is not None:
                return {
                    "temperatura_c": round(temperatura_c, 1),
                    "umidade_ar_pct": round(umidade_ar_pct, 1),
                }
            time.sleep(_RETRY_DELAY_SECONDS)

        raise RuntimeError(
            f"Falha ao ler o DHT22 no pino {pino} após {_RETRIES} tentativas."
        ) from ultimo_erro
    finally:
        dispositivo.exit()
