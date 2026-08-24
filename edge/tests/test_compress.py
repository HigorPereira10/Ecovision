"""
edge/tests/test_compress.py

O que este arquivo verifica, em português simples:

Que a função que comprime as fotos antes de mandar para a internet
(edge/src/compress.py) realmente entrega um arquivo JPEG válido. Ou
seja, depois de comprimida, a imagem não fica corrompida e ainda pode
ser aberta normalmente por qualquer programa. Também confere que pedir
mais "qualidade" gera um arquivo maior, como esperado de qualquer
compressor JPEG: um sinal de que o parâmetro está de fato sendo usado
(e não ignorado silenciosamente).

Não testa a câmera em si (Picamera2), só a etapa de compressão que vem
depois da foto já capturada, a parte que roda em qualquer computador,
sem precisar do Raspberry Pi.
"""

import io

from PIL import Image

from edge.src.compress import comprimir_imagem


def _imagem_de_teste_com_textura() -> bytes:
    """Gera uma imagem com um padrão de cores variado (não uma cor
    lisa), para se parecer mais com uma foto real de folha do que um
    retângulo de cor sólida. Uma imagem de cor sólida "engana" o
    compressor JPEG e não mostra a compressão de verdade."""
    imagem = Image.new("RGB", (800, 600))
    pixels = imagem.load()
    for x in range(800):
        for y in range(600):
            pixels[x, y] = ((x * 3) % 256, (y * 5) % 256, (x + y) % 256)
    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")
    return buffer.getvalue()


def test_imagem_comprimida_e_um_jpeg_valido():
    bruta = _imagem_de_teste_com_textura()
    comprimida = comprimir_imagem(bruta, quality=70)

    imagem_reaberta = Image.open(io.BytesIO(comprimida))
    imagem_reaberta.verify()
    assert imagem_reaberta.format == "JPEG"


def test_qualidade_maior_gera_arquivo_maior():
    bruta = _imagem_de_teste_com_textura()
    baixa_qualidade = comprimir_imagem(bruta, quality=20)
    alta_qualidade = comprimir_imagem(bruta, quality=95)

    assert len(alta_qualidade) > len(baixa_qualidade)
