# edge

Software do dispositivo de campo, um Raspberry Pi 3 Model B+ com Camera
Module 3, sensores ambientais e LED de iluminação. O dispositivo faz
apenas aquisição e transmissão: a classificação das imagens ocorre na API.

## Funções

- Ler a temperatura e a umidade do ar (DHT22) e a umidade do solo (sensor
  capacitivo lido pelo conversor ADS1115, via I2C).
- Fotografar a planta em resolução nativa (4608 × 2592), com o LED
  acionado por MOSFET e foco fixo na distância calibrada.
- Recomprimir a imagem em JPEG (qualidade 70) e gravá-la na fila local
  antes do envio, para que nenhuma captura se perca em quedas de rede.
- Enviar as capturas para `POST /diagnostico` e as leituras de 15 minutos
  para `POST /leituras`, com a credencial própria do dispositivo.

## Hardware

| Componente | Modelo | Função |
|---|---|---|
| Computador | Raspberry Pi 3 Model B+, cartão microSD de 32 GB | Execução do software |
| Câmera | Camera Module 3 (IMX708) | Captura da folha, com autofoco |
| Sensor de ar | DHT22 (AM2302) | Temperatura e umidade relativa |
| Sensor de solo | Capacitivo v1.2 + ADS1115 (16 bits) | Umidade do solo |
| Iluminação | LED de potência branco, 3 W | Iluminação durante a captura |
| Acionamento | MOSFET IRLZ44N, resistor de porta de 10 kΩ | Comando do LED pelo GPIO18 |
| Resistores | 6,8 Ω / 2 W (LED), 10 kΩ (pull-up do DHT22) | Limitação de corrente e pull-up |
| Fonte | 5 V / 3 A, micro-USB | Alimentação |

Pinagem (conector de 40 pinos):

| Pino | Função | Ligação |
|---|---|---|
| 1 | 3,3 V | DHT22 (VCC) e resistor de pull-up |
| 2 | 5 V | LED, terminal positivo |
| 3 | GPIO2 (SDA) | ADS1115, SDA |
| 5 | GPIO3 (SCL) | ADS1115, SCL |
| 6 | GND | MOSFET, fonte |
| 7 | GPIO4 | DHT22, dados (pull-up de 10 kΩ para 3,3 V) |
| 9 | GND | DHT22 (GND) |
| 12 | GPIO18 | MOSFET, porta, via resistor de 10 kΩ |
| 17 | 3,3 V | ADS1115 (VDD) e sensor de solo (VCC) |
| 20 | GND | ADS1115 (GND e ADDR, endereço 0x48) e sensor de solo (GND) |

O sensor de solo deve ser alimentado em 3,3 V, nunca em 5 V, e o LED
nunca deve ser ligado diretamente a um GPIO. O esquema completo está em
[`docs/figuras/hardware/esquematico-eletronico.png`](../docs/figuras/hardware/esquematico-eletronico.png).

## Estrutura

```
edge/
├── src/
│   ├── main.py            # ciclo de captura: sensores, LED, foto, fila, envio
│   ├── sensores.py        # ciclo de leitura de 15 minutos, sem foto
│   ├── config.py          # configuração por variáveis de ambiente
│   ├── capture.py         # câmera (Picamera2), com foco fixo
│   ├── compress.py        # recompressão JPEG (Pillow com libjpeg-turbo)
│   ├── sensors/           # DHT22 e sensor de solo (ADS1115 via smbus2)
│   ├── actuators/         # acionamento do LED
│   ├── fila/              # fila local em JSON Lines, com trava de arquivo
│   └── upload/            # envio com novas tentativas e espera exponencial
├── scripts/
│   ├── install.sh         # instalação no Raspberry Pi
│   └── calibrar_solo.py   # leitura bruta do sensor de solo para calibração
├── crontab.example        # agendamento dos ciclos
└── tests/                 # testes automatizados (ver tests/README.md)
```

## Instalação

No Raspberry Pi OS Lite de 64 bits, com as interfaces I2C e de câmera
habilitadas (`sudo raspi-config`):

```bash
git clone <repositório> && cd <repositório>
bash edge/scripts/install.sh
```

O script atualiza o sistema, instala as dependências (Picamera2,
libcamera, libjpeg-turbo, i2c-tools), cria o ambiente virtual em
`edge/.venv`, instala o agendamento do cron e cria `edge/.env` a partir de
`infra/env/edge.env.example`. Pode ser executado mais de uma vez.

Em seguida, preencha `edge/.env`. As variáveis obrigatórias são
`API_BASE_URL`, `DEVICE_ID` e `DEVICE_API_KEY`; a credencial é gerada na
API por `python -m scripts.provisionar_dispositivo <device_id> "<nome>"`.

## Agendamento

| Ciclo | Quando | O que faz |
|---|---|---|
| Captura (`main.py`) | A cada 2 horas, no minuto 0 | Sensores, LED, foto, fila local e envio |
| Leituras (`sensores.py`) | Minutos 5, 20, 35 e 50 | Só sensores, sem foto e sem fila |
| Drenagem da fila (`upload/uploader.py`) | A cada 15 minutos | Reenvio das capturas pendentes |

Os ciclos de captura e de leitura compartilham uma trava (`flock`), porque
a biblioteca de leitura do DHT22 não admite acessos simultâneos. Os
registros de execução ficam em `edge/data/logs/`.

## Calibração

- **Umidade do solo:** `python edge/scripts/calibrar_solo.py` mostra o
  valor bruto do ADC; os extremos vão em `SOIL_DRY_RAW` e `SOIL_WET_RAW`.
  A escala resultante é relativa ao sensor e não equivale a umidade
  volumétrica. Se o pino A0 do módulo não fizer contato, use
  `SOIL_ADS1115_CHANNEL=1`.
- **Foco da câmera:** com o autofoco ativo, leia `LensPosition` nos
  metadados da captura (dioptrias; centímetros = 100 / valor) e defina
  `CAMERA_FOCUS_CM`. A distância determina quantos pixels a folha ocupa e
  afeta diretamente a acurácia; o dispositivo em operação usa 19,9 cm.

## Verificação

```bash
ping <endereço da API>
i2cdetect -y 1                          # deve listar 0x48 (ADS1115)
edge/.venv/bin/python edge/src/main.py  # ciclo manual de captura
```
