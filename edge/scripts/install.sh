#!/bin/bash
#
# edge/scripts/install.sh
#
# Script de setup do ambiente no Raspberry Pi Zero 2 W (Raspberry Pi OS Lite 64-bit),
# conforme Tech Stack Blueprint v3.0, Fase 2.
#
# Ainda NÃO implementado, apenas o roteiro do que este script deve fazer quando escrito:
#   1. Atualizar o SO (apt update/upgrade).
#   2. Instalar libjpeg-turbo (dependência de performance do Pillow,
#      ver Pontos de Atenção do Blueprint: sem ela, compressão ~5x mais lenta).
#   3. Instalar dependências do sistema para Picamera2/libcamera.
#   4. Criar/ativar o virtualenv Python e instalar edge/requirements.txt.
#   5. Instalar o crontab a partir de edge/crontab.example.
#   6. Configurar as variáveis de ambiente do dispositivo
#      (ver infra/env/edge.env.example).
#
# TODO: implementar cada passo acima.
