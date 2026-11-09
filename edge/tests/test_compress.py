"""
Testes de edge/src/compress.py: a recompressão gera um JPEG válido e a
qualidade configurada afeta o tamanho do arquivo.
"""

import io

from PIL import Image

from edge.src.compress import comprimir_imagem


def _imagem_de_teste_com_textura() -> bytes:
    """Gera uma imagem com padrão de cores variado, mais próxima de uma
    foto real do que uma cor sólida, que o JPEG comprime trivialmente."""
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
