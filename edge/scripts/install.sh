#!/bin/bash
#
# edge/scripts/install.sh
#
# Script de setup do ambiente no Raspberry Pi 3 Model B+ (Anatel), Raspberry
# Pi OS Lite 64-bit — ver docs/decisions/0004-raspberry-pi-3b-plus.md pela
# troca de hardware (era Pi Zero 2 W). Necessário 64-bit para Picamera2/libcamera,
# conforme Tech Stack Blueprint v3.0, Fase 2.
#
# Uso: rodar a partir da raiz do repositório, já clonado no Pi:
#   bash edge/scripts/install.sh
#
# Idempotente: pode ser reexecutado sem duplicar configuração.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_DIR="$REPO_ROOT/edge/.venv"

echo "==> 1/6: Atualizando o sistema operacional"
sudo apt update
sudo apt upgrade -y

echo "==> 2/6: Instalando libjpeg-turbo (Pillow ~5x mais lento sem ela)"
sudo apt install -y libjpeg-turbo-progs libturbojpeg0-dev

echo "==> 3/6: Instalando dependências de sistema do Picamera2/libcamera"
sudo apt install -y python3-picamera2 python3-libcamera libcamera-apps \
  python3-venv python3-pip i2c-tools libgpiod3
# libgpiod3: exigido pelo Blinka/adafruit-circuitpython-dht (leitura do DHT22)
# em Raspberry Pi OS Bullseye+ — ver edge/src/sensors/dht22.py. Nome do pacote
# mudou de libgpiod2 pra libgpiod3 a partir do Debian trixie (bump de ABI da
# libgpiod upstream).

echo "==> 4/6: Criando/ativando virtualenv e instalando requirements.txt"
python3 -m venv --system-site-packages "$VENV_DIR"
# --system-site-packages: picamera2/libcamera vêm do apt (passo 3), não do pip.
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$REPO_ROOT/edge/requirements.txt"

echo "==> 5/6: Instalando o crontab a partir de edge/crontab.example"
# Os logs do cron (crontab.example) vão para dentro do repo, não /var/log/
# (que normalmente exige root) — garantir que o diretório já existe antes
# do cron tentar escrever neles pela primeira vez.
mkdir -p "$REPO_ROOT/edge/data/logs"
CRONTAB_TMP="$(mktemp)"
sed \
  -e "s#/caminho/venv/bin/python#$VENV_DIR/bin/python#g" \
  -e "s#/caminho/edge#$REPO_ROOT/edge#g" \
  "$REPO_ROOT/edge/crontab.example" | grep -v '^#' | grep -v '^\s*$' > "$CRONTAB_TMP"
(crontab -l 2>/dev/null || true; cat "$CRONTAB_TMP") | crontab -
rm -f "$CRONTAB_TMP"

echo "==> 6/6: Variáveis de ambiente"
ENV_FILE="$REPO_ROOT/edge/.env"
if [ ! -f "$ENV_FILE" ]; then
  cp "$REPO_ROOT/infra/env/edge.env.example" "$ENV_FILE"
  echo "    Criado $ENV_FILE a partir do template — edite com os valores reais"
  echo "    (API_BASE_URL, DEVICE_API_KEY, DEVICE_ID, pinos GPIO, calibração do solo)."
else
  echo "    $ENV_FILE já existe, não foi sobrescrito."
fi

echo "==> Setup concluído."
echo "    Habilitar a interface I2C (sensor de solo) e a câmera via 'sudo raspi-config' se ainda não estiverem ativas."
