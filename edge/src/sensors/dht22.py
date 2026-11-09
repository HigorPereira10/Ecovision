"""
Leitura do DHT22 (temperatura e umidade do ar) com adafruit-circuitpython-dht.

O protocolo do DHT22 gera erros pontuais de checksum e temporização em
operação normal; por isso a leitura é repetida algumas vezes antes de ser
considerada falha. Requer libgpiod3 no sistema (instalado por
edge/scripts/install.sh).
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


def _leitura_plausivel(temperatura_c, umidade_ar_pct) -> bool:
    """Indica se o par devolvido pela biblioteca é uma medição real.

    O sensor pode responder 0,0 nos dois campos em vez de falhar; esse par
    é tratado como falha. A faixa aceita é larga de propósito: o objetivo é
    separar falha de medição, e não validar valores agronômicos.
    """
    if temperatura_c is None or umidade_ar_pct is None:
        return False
    if temperatura_c == 0.0 and umidade_ar_pct == 0.0:
        return False
    if not (-20.0 <= temperatura_c <= 70.0):
        return False
    if not (0.0 < umidade_ar_pct <= 100.0):
        return False
    return True


def ler_dht22(pino: int) -> dict:
    """Lê temperatura e umidade do ar.

    Levanta RuntimeError se todas as tentativas falharem ou se o sensor
    responder com valor implausível; o ciclo de captura trata o erro
    registrando o campo como ausente."""
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

            if _leitura_plausivel(temperatura_c, umidade_ar_pct):
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
