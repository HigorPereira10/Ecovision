"""
edge/src/sensors/dht22.py

Leitura do sensor DHT22 (temperatura/umidade do ar, protocolo 1-Wire),
via adafruit-circuitpython-dht (Blueprint v3.0, Fase 1 e 2).

Precisão do sensor: ±0.5°C / ±2-5%RH. O BoM prevê 2 unidades (1 sobressalente).

Biblioteca: usamos adafruit-circuitpython-dht (import adafruit_dht) em vez
do antigo Adafruit_DHT, que está descontinuado e tem histórico de
falha de instalação em versões recentes do Raspberry Pi OS. Requer o
pacote de sistema libgpiod2 (instalado em edge/scripts/install.sh).

Esta é a única parte do projeto que ainda usa a pilha Blinka. O sensor
de solo saiu dela e fala I2C direto via smbus2, porque a camada de I2C
da Blinka quebra neste Raspberry Pi (ver soil_moisture.py). O DHT22 não
é afetado: ele usa 1-Wire por GPIO, não I2C.

ATENÇÃO: adafruit_dht levanta RuntimeError com frequência em leituras
normais (erros de checksum/timing são esperados no protocolo 1-Wire do
DHT22). Por isso existe o retry manual abaixo, em vez de tratar
RuntimeError como falha definitiva já na primeira tentativa.

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


def _leitura_plausivel(temperatura_c, umidade_ar_pct) -> bool:
    """Decide se o par devolvido pela biblioteca é uma medição de verdade.

    POR QUE NÃO BASTA CHECAR None: em 2026-10-31, às 21:30, o sensor
    passou a devolver `0.0` em AMBOS os campos em vez de `None` ou de
    levantar erro. Como `0.0 is not None`, a checagem antiga aceitava,
    e o zero entrou no banco como medição válida. Três ciclos gravaram
    0,0 grau e 0,0 por cento, e cada um disparou alerta ambiental falso,
    porque 0 grau fica abaixo do limiar mínimo de 10 definido em
    cloud/app/core/alertas_ambientais.py.

    Zero exato nos dois campos ao mesmo tempo não é medição possível
    numa estufa: seria a temperatura de congelamento junto de ar
    completamente seco. É a assinatura da falha, não um valor.

    O resto da faixa é deliberadamente larga. O objetivo aqui é separar
    falha de medição, não validar agronomia: limites estreitos
    descartariam leitura real de madrugada fria ou de dia muito quente,
    e essa decisão pertence aos limiares de alerta, na nuvem, não ao
    driver do sensor.

    Recusar faz o ler_dht22 levantar RuntimeError, que o
    `_ler_sensores()` de edge/src/main.py já trata gravando None e
    seguindo o ciclo. A foto não se perde por causa do sensor.
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
    """Lê temperatura e umidade do ar. Levanta RuntimeError se falhar em
    todas as tentativas (o DHT22 falha pontualmente com frequência;
    isso é esperado, não indica sensor com defeito), e também quando o
    sensor responde com valor implausível (ver _leitura_plausivel)."""
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
