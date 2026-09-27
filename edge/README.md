# edge: Software de Borda (Raspberry Pi 3 Model B+)

Referência arquitetural: **Tech Stack Blueprint Consolidado v3.0, Fase 2 (Software de Borda)**.

> Hardware: **Raspberry Pi 3 Model B+ (Anatel)**, troca em relação ao
> Pi Zero 2 W do Blueprint original, ver
> [ADR 0004](../docs/decisions/0004-raspberry-pi-3b-plus.md).

## Papel desta camada

O Pi realiza **exclusivamente** captura, compressão e transmissão.
**Nenhuma inferência de IA roda aqui**: decisão arquitetural deliberada
validada no Blueprint, independente da capacidade do hardware (o Pi 3B+,
quad-core Cortex-A53 @1.4GHz / 1GB RAM, tem folga de sobra para
captura/compressão/fila, mas a inferência continua no backend por
design, não por limitação de hardware).

Responsabilidades:
- Capturar fotos da folha via Picamera2 (Camera Module 3, autofoco PDAF),
  acionando o Ring LED (flash dominante) através do MOSFET de canal N:
  **nunca ligar o LED direto no GPIO** (Blueprint, Fase 1, correção crítica).
- Ler os sensores ambientais: DHT22 (temperatura/umidade do ar) e sensor
  capacitivo de umidade do solo via ADS1115 (ADC I2C).
- Comprimir a imagem (Pillow + libjpeg-turbo, quality=70) para 150-250KB.
- Manter uma fila offline (JSON Lines) para quando a rede cair, com
  upload por retry/backoff quando a conexão voltar.
- Agendar captura a cada 2h e drenagem da fila a cada 15min via `cron`.

## Estrutura

```
edge/
├── src/
│   ├── main.py              # orquestração: sensores -> LED -> foto -> fila -> upload
│   ├── config.py            # variáveis de ambiente (URL da API, API Key, intervalos)
│   ├── capture.py           # Picamera2 + autofoco (AfMode.Auto)
│   ├── compress.py          # Pillow + libjpeg-turbo
│   ├── sensors/
│   │   ├── dht22.py         # adafruit-circuitpython-dht
│   │   └── soil_moisture.py # Adafruit ADS1x15
│   ├── actuators/
│   │   └── led_flash.py     # RPi.GPIO, acionamento do Ring LED via MOSFET
│   ├── fila/
│   │   └── offline_queue.py # fila JSON Lines + fcntl (lock de arquivo)
│   └── upload/
│       └── uploader.py      # requests, retry/backoff, header Authorization (API Key)
├── scripts/
│   └── install.sh           # setup de dependências no Pi (apt + venv + crontab)
├── crontab.example          # agendamento: captura 2h / upload da fila 15min
├── requirements.txt
└── tests/                   # testes automatizados (ver edge/tests/README.md)
```

## Testes automatizados

A parte do código que não depende de hardware (fila offline + envio
para a API) tem testes automatizados em [`edge/tests/`](tests/README.md),
cobrindo, sem precisar da Raspberry Pi física, o ciclo completo de
guardar fotos pendentes, confirmar envio, e os casos de falha de rede.
Ver [`edge/tests/README.md`](tests/README.md) para uma explicação de
cada teste e como rodar (WSL/Linux ou Windows).

## Pontos de atenção herdados do Blueprint

- Verificar `libjpeg-turbo` ativo antes de medir velocidade de compressão:
  sem ele, o Pillow é ~5x mais lento.
- O Ring LED **precisa** passar pelo MOSFET (ver `edge/src/actuators/led_flash.py`):
  ligação direta ao GPIO pode danificar o pino ou o Pi.
- A Camera Module 3 usa o conector CSI **padrão de 15 pinos** do Pi 3B+
  (mesmo do Pi 4), o cabo que já acompanha a câmera serve direto, sem
  adaptador (diferente do Pi Zero, que usava um conector mini de 22
  pinos, ver [ADR 0004](../docs/decisions/0004-raspberry-pi-3b-plus.md)).

## Decisões de implementação que corrigem riscos identificados em revisão

- **`edge/src/config.py`**: `QUEUE_DIR` é ancorado em `__file__` (não no
  diretório de trabalho de quem chamou o script), necessário porque o
  cron normalmente roda com cwd diferente da raiz do repositório.
- **`edge/crontab.example`** + **`edge/scripts/install.sh`**: os logs do
  cron vão para `edge/data/logs/` (dentro do repo), não `/var/log/`, que
  normalmente exige root.
- **`edge/src/main.py`**: falha de leitura de um sensor ambiental (DHT22
  ou solo) não aborta o ciclo, a foto (dado mais valioso) ainda é
  capturada, com `None` no(s) campo(s) que falharam.
- **`edge/src/sensors/dht22.py`**: usa `adafruit-circuitpython-dht` em
  vez do legado `Adafruit_DHT` (descontinuado, instalação frágil em
  Raspberry Pi OS atual), mesma linha CircuitPython/Blinka do ADS1115.
- **`edge/requirements.txt`**: `picamera2` não é instalado via pip aqui, 
  vem do `apt` em `install.sh` (`python3-picamera2`), porque depende
  de bindings do libcamera compilados para o sistema.
- **`edge/src/upload/uploader.py`**: cada envio agora manda um
  `idempotency_key` (o `id` já gerado por `offline_queue.enfileirar()`),
  pois sem isso, um reenvio após a API confirmar 200 mas o Pi cair antes de
  tirar o registro da fila local criaria uma linha duplicada no banco
  (ver `cloud/app/api/routes/diagnostico.py`).

## Pendências de grupo

- Confirmar compatibilidade física do dissipador/case com o formato do
  Pi 3B+ (ver [ADR 0004](../docs/decisions/0004-raspberry-pi-3b-plus.md)).
- Calibração real de `SOIL_DRY_RAW`/`SOIL_WET_RAW` (`edge/src/config.py`)
  assim que o sensor físico estiver disponível em protoboard.
