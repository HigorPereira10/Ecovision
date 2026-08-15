"""
edge/src/upload/uploader.py

Upload HTTP dos registros pendentes para a API, com retry/backoff
(Blueprint v3.0, Fase 2).

Responsabilidades quando implementado:
- Ler os pendentes da fila (edge/src/queue/offline_queue.py).
- Enviar POST /diagnostico para a API no Railway, autenticado via
  header Authorization com a API Key estática (config.DEVICE_API_KEY).
- Implementar retry com backoff exponencial em caso de falha de rede.
- Remover da fila apenas os itens confirmados (HTTP 2xx) pela API.

Relação com o resto do sistema:
- Consome a fila escrita por edge/src/main.py.
- Único ponto de contato do edge/ com o endpoint
  cloud/app/api/routes/diagnostico.py.
- Agendado a cada 15min via `crontab.example`.
"""

# import requests
# from edge.src import config
# from edge.src.queue import offline_queue

# def drenar_fila_e_enviar() -> None:
#     """Lê pendentes, envia com retry/backoff, remove da fila os confirmados."""
#     raise NotImplementedError
