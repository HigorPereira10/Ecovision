"""
Recompressão JPEG da imagem capturada (Pillow com libjpeg-turbo).

A imagem não é redimensionada: o diagnóstico por janelas na API recorta
janelas de 896 pixels da resolução nativa, e reduzir a imagem diminuiria o
número de janelas aproveitáveis. Na qualidade 70, cada captura fica entre
1,3 e 1,5 MB. Alterar a qualidade pode afetar o diagnóstico e deve ser
avaliado antes. Sem libjpeg-turbo, o Pillow fica cerca de cinco vezes mais
lento.
"""

import io

from PIL import Image


def comprimir_imagem(bytes_imagem_crua: bytes, quality: int = 70) -> bytes:
    """Recomprime em JPEG mantendo a resolução nativa."""
    imagem = Image.open(io.BytesIO(bytes_imagem_crua))
    imagem = imagem.convert("RGB")

    buffer = io.BytesIO()
    imagem.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()
