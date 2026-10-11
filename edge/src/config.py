"""
edge/src/config.py

Configuração via variáveis de ambiente do dispositivo (ver
infra/env/edge.env.example para o template das chaves esperadas).

Relação com o resto do sistema:
- Consumido por todos os módulos de edge/src/.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Caminho da pasta edge/, usado para ancorar caminhos (.env, QUEUE_DIR)
# de forma absoluta, independente do diretório de trabalho de quem
# chamou o script. Isso importa porque o cron normalmente roda com
# cwd == home do usuário, não a raiz do repositório.
_EDGE_DIR = Path(__file__).resolve().parents[1]

# O cron não carrega variáveis de ambiente automaticamente, então este
# comando lê edge/.env aqui (gerado por edge/scripts/install.sh a partir
# de infra/env/edge.env.example) para que main.py/uploader.py funcionem
# tanto invocados pelo cron quanto manualmente. Não sobrescreve
# variáveis já definidas no ambiente (ex.: exportadas manualmente ou por
# systemd).
load_dotenv(_EDGE_DIR / ".env")


def _obrigatoria(nome: str) -> str:
    valor = os.environ.get(nome)
    if not valor:
        raise RuntimeError(
            f"Variável de ambiente obrigatória ausente: {nome} "
            f"(ver infra/env/edge.env.example)"
        )
    return valor


def _inteira(nome: str, padrao: int) -> int:
    return int(os.environ.get(nome, padrao))


def _flutuante(nome: str, padrao: float) -> float:
    return float(os.environ.get(nome, padrao))


# --- API / autenticação ---
API_BASE_URL = _obrigatoria("API_BASE_URL")
DEVICE_API_KEY = _obrigatoria("DEVICE_API_KEY")
DEVICE_ID = _obrigatoria("DEVICE_ID")

# --- Agendamento (Blueprint v3.0, Fase 2) ---
CAPTURE_INTERVAL_MINUTES = _inteira("CAPTURE_INTERVAL_MINUTES", 120)
QUEUE_DRAIN_INTERVAL_MINUTES = _inteira("QUEUE_DRAIN_INTERVAL_MINUTES", 15)

# --- GPIO ---
LED_MOSFET_PIN = _inteira("LED_MOSFET_PIN", 18)
DHT22_PIN = _inteira("DHT22_PIN", 4)
# CUIDADO COM O NOME: isto NÃO é quanto tempo o LED fica aceso. É só a
# espera, com o LED já ligado, antes de disparar a câmera, para o brilho
# estabilizar (ver main.py). O LED permanece aceso durante a captura
# inteira, e quem domina esse tempo é o autofoco: medido no dispositivo,
# o ciclo levou de 5,6s a 27s conforme a luz ambiente.
#
# O nome enganoso já se propagou para a documentação, que afirmava um
# "flash de 0,5s" (corrigido em docs/planejamento/lista-compras-hardware.md
# e no Blueprint v4, seção 3.2). Importa porque é esse tempo que dimensiona
# a potência do resistor em série do LED.
LED_FLASH_DURATION_SECONDS = _flutuante("LED_FLASH_DURATION_SECONDS", 0.5)

# --- ADS1115 (sensor de umidade do solo, I2C) ---
# O canal é configurável porque nem sempre dá para usar o A0: no
# dispositivo atual esse pino do módulo não faz contato, e a montagem
# usa o A1 (ver ADR 0015). Na placa soldada isso deve voltar para 0.
SOIL_ADS1115_CHANNEL = _inteira("SOIL_ADS1115_CHANNEL", 0)

# Valores brutos do ADC (0-26400 no fundo de escala de 4,096V) com o
# sensor seco e saturado. São ESPECÍFICOS de cada sensor e da tensão
# que o alimenta, por isso vivem no .env de cada dispositivo, não aqui.
# Os defaults abaixo continuam sendo placeholders de fabricante e não
# servem para medir nada.
#
# Calibração real medida em 2026-10-11, no ecovision-pi-01, com o
# sensor alimentado em 3,3V:
#
#     seco, suspenso no ar ..... 17468  (2,184 V)
#     submerso ateh a linha .....  7179  (0,897 V)
#
# PENDENTE: refazer com o sensor em TERRA. Água pura é o extremo
# absoluto de saturação, então a faixa acima provavelmente superestima
# o que o solo real entrega, e é o solo que o ADR 0005 usa como limiar.
SOIL_DRY_RAW = _inteira("SOIL_DRY_RAW", 18000)
SOIL_WET_RAW = _inteira("SOIL_WET_RAW", 8000)

# --- Compressão de imagem (Blueprint, Fase 2) ---
JPEG_QUALITY = _inteira("JPEG_QUALITY", 70)

# --- Fila offline (Blueprint, Fase 2) ---
# ATENÇÃO, BUG JÁ CORRIGIDO AQUI: o default era um caminho relativo
# ("edge/data/queue"), que resolvia para lugares diferentes dependendo
# de quem chamava o script (manual, na raiz do repo, vs. cron, com
# cwd == home do usuário). Dados podiam "sumir" de um lado sem erro
# nenhum. Agora está ancorado em _EDGE_DIR (baseado em __file__), igual
# ao .env acima. QUEUE_DIR só deve ser definido por variável de
# ambiente se alguém precisar de fato apontar para outro lugar
# (ex.: disco externo).
_QUEUE_DIR_ENV = os.environ.get("QUEUE_DIR")
QUEUE_DIR = Path(_QUEUE_DIR_ENV) if _QUEUE_DIR_ENV else (_EDGE_DIR / "data" / "queue")
QUEUE_FILE = QUEUE_DIR / "fila.jsonl"
QUEUE_IMAGES_DIR = QUEUE_DIR / "images"

# --- Logs (cron redireciona stdout/stderr para cá, ver crontab.example) ---
LOGS_DIR = _EDGE_DIR / "data" / "logs"

# --- Upload / retry (Blueprint, Fase 2: "retry/backoff") ---
UPLOAD_TIMEOUT_SECONDS = _flutuante("UPLOAD_TIMEOUT_SECONDS", 30.0)
UPLOAD_MAX_RETRIES = _inteira("UPLOAD_MAX_RETRIES", 5)
UPLOAD_BACKOFF_FACTOR = _flutuante("UPLOAD_BACKOFF_FACTOR", 1.0)
