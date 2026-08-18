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

# Cron não carrega variáveis de ambiente automaticamente — lê edge/.env
# aqui (gerado por edge/scripts/install.sh a partir de
# infra/env/edge.env.example) para que main.py/uploader.py funcionem tanto
# invocados pelo cron quanto manualmente. Não sobrescreve variáveis já
# definidas no ambiente (ex.: exportadas manualmente ou por systemd).
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


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
# totalmente seco e totalmente submerso em água. Defaults abaixo são
# apenas placeholders de fabricante — TODO: calibrar com o sensor físico
# assim que o hardware estiver montado (Blueprint, Fase 1 do Plano de
# Execução: "montar em protoboard e validar cada sensor isoladamente").
SOIL_DRY_RAW = _inteira("SOIL_DRY_RAW", 18000)
SOIL_WET_RAW = _inteira("SOIL_WET_RAW", 8000)

# --- Compressão de imagem (Blueprint, Fase 2) ---
JPEG_QUALITY = _inteira("JPEG_QUALITY", 70)

# --- Fila offline (Blueprint, Fase 2) ---
QUEUE_DIR = Path(os.environ.get("QUEUE_DIR", "edge/data/queue"))
QUEUE_FILE = QUEUE_DIR / "fila.jsonl"
QUEUE_IMAGES_DIR = QUEUE_DIR / "images"

# --- Upload / retry (Blueprint, Fase 2: "retry/backoff") ---
UPLOAD_TIMEOUT_SECONDS = _flutuante("UPLOAD_TIMEOUT_SECONDS", 30.0)
UPLOAD_MAX_RETRIES = _inteira("UPLOAD_MAX_RETRIES", 5)
UPLOAD_BACKOFF_FACTOR = _flutuante("UPLOAD_BACKOFF_FACTOR", 1.0)
