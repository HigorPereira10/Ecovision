"""
edge/src/queue/offline_queue.py

Fila offline em disco (formato JSON Lines) para tolerar quedas de rede
no ambiente de estufa (Blueprint v3.0, Fase 2).

Responsabilidades quando implementado:
- Enfileirar um registro (metadados + caminho da imagem comprimida)
  como uma linha JSON no arquivo de fila.
- Usar `fcntl` para lock de arquivo, evitando corrupção se o cron
  disparar captura e drenagem simultaneamente.
- Expor uma função de leitura/drenagem que remove da fila apenas os
  itens confirmados como enviados (edge/src/upload/uploader.py).

Relação com o resto do sistema:
- Escrito por edge/src/main.py a cada ciclo de captura.
- Drenado por edge/src/upload/uploader.py, agendado a cada 15min via cron.
"""

# import fcntl
# import json
# from pathlib import Path

# def enfileirar(registro: dict, caminho_fila: "Path") -> None:
#     """Adiciona um registro como nova linha JSON na fila, com lock de arquivo."""
#     raise NotImplementedError

# def ler_pendentes(caminho_fila: "Path") -> list:
#     """Lê os registros ainda não enviados."""
#     raise NotImplementedError

# def remover_enviados(caminho_fila: "Path", ids_enviados: list) -> None:
#     """Remove da fila os registros já confirmados como enviados."""
#     raise NotImplementedError
