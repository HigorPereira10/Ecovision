"""
edge/src/compress.py

Compressão JPEG da imagem capturada, via Pillow + libjpeg-turbo
(Blueprint v3.0, Fase 2). quality=70 gera arquivos de 150-250KB a
partir dos 12MP da Camera Module 3.

IMPORTANTE: verificar que libjpeg-turbo está de fato ativo no SO antes
de medir performance, sem ele, o Pillow é ~5x mais lento (Blueprint,
Pontos de Atenção).

Relação com o resto do sistema:
- Recebe a imagem crua de edge/src/capture.py.
- A imagem comprimida resultante é o que entra na fila offline
  (edge/src/queue/offline_queue.py) e, depois, é enviada para a API.
"""

# from PIL import Image

# def comprimir_imagem(bytes_imagem_crua: bytes, quality: int = 70) -> bytes:
#     """Comprime para JPEG, alvo de 150-250KB."""
#     raise NotImplementedError
