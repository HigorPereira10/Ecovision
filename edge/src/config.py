"""
edge/src/config.py

Configuração via variáveis de ambiente do dispositivo (ver
infra/env/edge.env.example para o template das chaves esperadas).

Deve conter, quando implementado:
- API_BASE_URL (endpoint da API no Railway)
- DEVICE_API_KEY (mesma API Key validada em cloud/app/core/security.py)
- DEVICE_ID (identificador único do Pi, usado também no caminho da
  imagem no Supabase Storage: {device_id}/{timestamp}.jpg)
- CAPTURE_INTERVAL_MINUTES (padrão: 120, conforme Blueprint)
- QUEUE_DRAIN_INTERVAL_MINUTES (padrão: 15, conforme Blueprint)
- GPIO pins: LED_MOSFET_PIN, DHT22_PIN
- I2C address do ADS1115 (sensor de solo)

Relação com o resto do sistema:
- Consumido por todos os módulos de edge/src/.
"""

# import os

# API_BASE_URL = os.environ["API_BASE_URL"]
# DEVICE_API_KEY = os.environ["DEVICE_API_KEY"]
# DEVICE_ID = os.environ["DEVICE_ID"]
# TODO: demais variáveis (pinos GPIO, intervalos)
