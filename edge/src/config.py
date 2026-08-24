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
LED_FLASH_DURATION_SECONDS = _flutuante("LED_FLASH_DURATION_SECONDS", 0.5)

# --- ADS1115 (sensor de umidade do solo, I2C) ---
SOIL_ADS1115_CHANNEL = _inteira("SOIL_ADS1115_CHANNEL", 0)

# Valores brutos do ADC (0-26400 no ganho padrão) lidos com o sensor
# totalmente seco e totalmente submerso em água. Os defaults abaixo são
# apenas placeholders de fabricante.
# TODO, CUIDADO: calibrar com o sensor físico assim que o hardware
# estiver montado (Blueprint, Fase 1 do Plano de Execução: "montar em
# protoboard e validar cada sensor isoladamente"). Sem essa calibração,
# a leitura de umidade do solo não é confiável.
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
