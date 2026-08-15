# edge — Software de Borda (Raspberry Pi Zero 2 W)

Referência arquitetural: **Tech Stack Blueprint Consolidado v3.0, Fase 2 (Software de Borda)**.

## Papel desta camada

O Pi Zero 2 W realiza **exclusivamente** captura, compressão e transmissão.
**Nenhuma inferência de IA roda aqui** , o hardware (quad-core 1GHz, 512MB RAM)
não tem capacidade para isso, e essa é uma decisão arquitetural deliberada
validada no Blueprint.

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
│   ├── main.py              # orquestração: captura -> sensores -> fila -> upload
│   ├── config.py            # variáveis de ambiente (URL da API, API Key, intervalos)
│   ├── capture.py           # Picamera2 + autofoco (AfMode.AUTO)
│   ├── compress.py          # Pillow + libjpeg-turbo
│   ├── sensors/
│   │   ├── dht22.py         # Adafruit_DHT
│   │   └── soil_moisture.py # Adafruit ADS1x15
│   ├── actuators/
│   │   └── led_flash.py     # RPi.GPIO, acionamento do Ring LED via MOSFET
│   ├── queue/
│   │   └── offline_queue.py # fila JSON Lines + fcntl (lock de arquivo)
│   └── upload/
│       └── uploader.py      # requests, retry/backoff, header Authorization (API Key)
├── scripts/
│   └── install.sh           # setup de dependências no Pi (libjpeg-turbo etc.)
├── crontab.example          # agendamento: captura 2h / upload da fila 15min
└── requirements.txt
```

## Pontos de atenção herdados do Blueprint

- Verificar `libjpeg-turbo` ativo antes de medir velocidade de compressão
 sem ele, o Pillow é ~5x mais lento.
- O Ring LED **precisa** passar pelo MOSFET (ver `edge/src/actuators/led_flash.py`)
 ligação direta ao GPIO pode danificar o pino ou o Pi.
- A Camera Module 3 requer cabo FFC específico para o conector CSI de
  22 pinos do Pi Zero, não é o mesmo cabo que acompanha o kit padrão da câmera.

## Pendências de grupo

- Nenhuma decisão em aberto nesta camada, Fase 2 foi validada sem
  alterações no Blueprint v3.0.
