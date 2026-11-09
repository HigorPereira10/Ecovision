"""Configuração do dispositivo por variáveis de ambiente (modelo em infra/env/edge.env.example)."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Caminhos ancorados na pasta edge/, independentes do diretório de
# trabalho (o cron roda a partir do diretório do usuário).
_EDGE_DIR = Path(__file__).resolve().parents[1]

# O cron não carrega variáveis de ambiente: edge/.env é lido aqui, sem
# sobrescrever variáveis já definidas.
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

# --- Agendamento ---
CAPTURE_INTERVAL_MINUTES = _inteira("CAPTURE_INTERVAL_MINUTES", 120)
QUEUE_DRAIN_INTERVAL_MINUTES = _inteira("QUEUE_DRAIN_INTERVAL_MINUTES", 15)

# --- GPIO ---
LED_MOSFET_PIN = _inteira("LED_MOSFET_PIN", 18)
DHT22_PIN = _inteira("DHT22_PIN", 4)
# Espera, com o LED já aceso, antes de disparar a câmera. O LED permanece
# aceso durante toda a captura (cerca de 2,4 s com foco fixo).
LED_FLASH_DURATION_SECONDS = _flutuante("LED_FLASH_DURATION_SECONDS", 0.5)

# --- ADS1115 (sensor de umidade do solo, I2C) ---
# Canal configurável: no dispositivo atual o pino A0 do módulo não faz
# contato e a leitura usa o A1.
SOIL_ADS1115_CHANNEL = _inteira("SOIL_ADS1115_CHANNEL", 0)

# Valores brutos do ADC com o sensor seco e no extremo úmido. Dependem de
# cada sensor e da tensão de alimentação; os padrões abaixo são apenas
# provisórios. A escala resultante é relativa ao sensor e não equivale a
# umidade volumétrica. Para aproximar a fração de água disponível, meça
# SOIL_DRY_RAW no ponto de murcha permanente e SOIL_WET_RAW na capacidade
# de campo.
SOIL_DRY_RAW = _inteira("SOIL_DRY_RAW", 18000)
SOIL_WET_RAW = _inteira("SOIL_WET_RAW", 8000)

# --- Câmera ---
# Distância de foco fixo, em centímetros (convertida para dioptrias em
# capture.py); zero usa o autofoco. Depende de cada montagem: ela define
# quantos pixels a folha ocupa na janela enviada ao modelo.
CAMERA_FOCUS_CM = _flutuante("CAMERA_FOCUS_CM", 0.0)

# --- Compressão de imagem ---
JPEG_QUALITY = _inteira("JPEG_QUALITY", 70)

# --- Fila local ---
# Ancorada em edge/ para que cron e execução manual usem o mesmo diretório.
_QUEUE_DIR_ENV = os.environ.get("QUEUE_DIR")
QUEUE_DIR = Path(_QUEUE_DIR_ENV) if _QUEUE_DIR_ENV else (_EDGE_DIR / "data" / "queue")
QUEUE_FILE = QUEUE_DIR / "fila.jsonl"
QUEUE_IMAGES_DIR = QUEUE_DIR / "images"

# --- Logs (o cron redireciona a saída para cá) ---
LOGS_DIR = _EDGE_DIR / "data" / "logs"

# --- Envio ---
UPLOAD_TIMEOUT_SECONDS = _flutuante("UPLOAD_TIMEOUT_SECONDS", 30.0)
UPLOAD_MAX_RETRIES = _inteira("UPLOAD_MAX_RETRIES", 5)
UPLOAD_BACKOFF_FACTOR = _flutuante("UPLOAD_BACKOFF_FACTOR", 1.0)
