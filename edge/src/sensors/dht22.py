"""
edge/src/sensors/dht22.py

Leitura do sensor DHT22 (temperatura/umidade do ar, protocolo 1-Wire),
via biblioteca Adafruit_DHT (Blueprint v3.0, Fase 1 e 2).

Precisão do sensor: ±0.5°C / ±2-5%RH. O BoM prevê 2 unidades (1 sobressalente).

Relação com o resto do sistema:
- Chamado por edge/src/main.py em cada ciclo de captura.
- A leitura resultante entra no pacote enviado para o endpoint
  /diagnostico e é persistida na tabela leituras_ambientais
  (cloud/app/db/models.py).
"""

import Adafruit_DHT

_SENSOR = Adafruit_DHT.DHT22

# DHT22 é propenso a falhas de leitura pontuais (timing 1-Wire sensível);
# read_retry já reexecuta internamente antes de desistir.
_RETRIES = 15
_DELAY_SECONDS = 2


def ler_dht22(pino: int) -> dict:
    """Lê temperatura e umidade do ar. Levanta RuntimeError se falhar
    após as tentativas internas do Adafruit_DHT."""
    umidade_ar_pct, temperatura_c = Adafruit_DHT.read_retry(
        _SENSOR, pino, retries=_RETRIES, delay_seconds=_DELAY_SECONDS
    )

    if temperatura_c is None or umidade_ar_pct is None:
        raise RuntimeError(
            f"Falha ao ler o DHT22 no pino {pino} após {_RETRIES} tentativas."
        )

    return {
        "temperatura_c": round(temperatura_c, 1),
        "umidade_ar_pct": round(umidade_ar_pct, 1),
    }
