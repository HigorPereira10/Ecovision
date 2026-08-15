"""
edge/src/main.py

Orquestrador principal do ciclo de captura, executado periodicamente
via cron (Blueprint v3.0, Fase 2: agendamento de captura a cada 2h).

Fluxo esperado quando implementado:
1. Ler sensores (sensors/dht22.py, sensors/soil_moisture.py).
2. Acionar o Ring LED via MOSFET (actuators/led_flash.py) por ~0,5s
   durante a captura.
3. Capturar a foto (capture.py) com autofoco.
4. Comprimir a imagem (compress.py).
5. Enfileirar o pacote (imagem + leituras) na fila offline
   (queue/offline_queue.py).
6. Tentar drenar a fila e enviar para a API (upload/uploader.py),
   também disparado separadamente a cada 15min via cron para casos de
   rede instável.

Relação com o resto do sistema:
- É o script chamado pelo `crontab.example`.
- Depende de todos os demais módulos de edge/src/.
- O destino final dos dados é o endpoint POST /diagnostico da API
  (cloud/app/api/routes/diagnostico.py).
"""

# from edge.src import capture, compress
# from edge.src.sensors import dht22, soil_moisture
# from edge.src.actuators import led_flash
# from edge.src.queue import offline_queue
# from edge.src.upload import uploader

# def ciclo_de_captura() -> None:
#     """Executa um ciclo completo: sensores -> LED -> foto -> compressão -> fila -> upload."""
#     raise NotImplementedError

# if __name__ == "__main__":
#     ciclo_de_captura()
