#!/bin/bash
#
# Instalação do software do dispositivo no Raspberry Pi 3 Model B+
# (Raspberry Pi OS Lite, 64 bits). Executar a partir da raiz do
# repositório já clonado:
#
#   bash edge/scripts/install.sh
#
# Pode ser executado mais de uma vez sem duplicar a configuração.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_DIR="$REPO_ROOT/edge/.venv"

echo "==> 1/7: Atualizando o sistema operacional"
sudo apt update
sudo apt upgrade -y

echo "==> 2/7: Instalando libjpeg-turbo (Pillow ~5x mais lento sem ela)"
sudo apt install -y libjpeg-turbo-progs libturbojpeg0-dev

echo "==> 3/7: Instalando dependências de sistema do Picamera2/libcamera"
# libgpiod3: exigido pela leitura do DHT22 (Adafruit Blinka) a partir do Debian trixie.
sudo apt install -y python3-picamera2 python3-libcamera libcamera-apps \
  python3-venv python3-pip i2c-tools libgpiod3

echo "==> 4/7: Criando/ativando virtualenv e instalando requirements.txt"
# --system-site-packages: o Picamera2 e o libcamera vêm do apt (passo 3).
python3 -m venv --system-site-packages "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$REPO_ROOT/edge/requirements.txt"

echo "==> 5/7: Verificando se o Pillow está de fato usando libjpeg-turbo"
"$VENV_DIR/bin/python" -c "
from PIL import features
if features.check_feature('libjpeg_turbo'):
    print('    libjpeg-turbo ativo no Pillow.')
else:
    print('    AVISO: Pillow NAO esta usando libjpeg-turbo, compressao vai ficar mais lenta.')
"

echo "==> 6/7: Instalando o crontab a partir de edge/crontab.example"
# Os registros do cron ficam em edge/data/logs/, sem exigir permissão de root.
mkdir -p "$REPO_ROOT/edge/data/logs"
CRONTAB_TMP="$(mktemp)"
sed \
  -e "s#/caminho/venv/bin/python#$VENV_DIR/bin/python#g" \
  -e "s#/caminho/edge#$REPO_ROOT/edge#g" \
  "$REPO_ROOT/edge/crontab.example" | grep -v '^#' | grep -v '^\s*$' > "$CRONTAB_TMP"
(crontab -l 2>/dev/null || true; cat "$CRONTAB_TMP") | crontab -
rm -f "$CRONTAB_TMP"

echo "==> 7/7: Variáveis de ambiente"
ENV_FILE="$REPO_ROOT/edge/.env"
if [ ! -f "$ENV_FILE" ]; then
  cp "$REPO_ROOT/infra/env/edge.env.example" "$ENV_FILE"
  echo "    Criado $ENV_FILE a partir do template, edite com os valores reais"
  echo "    (API_BASE_URL, DEVICE_API_KEY, DEVICE_ID, pinos GPIO, calibração do solo)."
else
  echo "    $ENV_FILE já existe, não foi sobrescrito."
fi

echo "==> Setup concluído."
echo "    Habilitar a interface I2C (sensor de solo) e a câmera via 'sudo raspi-config' se ainda não estiverem ativas."
