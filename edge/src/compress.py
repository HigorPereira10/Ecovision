"""
edge/src/compress.py

Compressão JPEG da imagem capturada, via Pillow + libjpeg-turbo
(Blueprint v3.0, Fase 2).

TAMANHO REAL: 1,3 a 1,5 MB, NÃO os 150-250KB do Blueprint
---------------------------------------------------------
Este módulo não redimensiona, só reencoda. Os 12MP da Camera Module 3
(4608x2592) a quality=70 dão 1,3 a 1,5 MB, e foi isso que as 122
capturas de 28/10 a 05/11 gravaram: média de 1450 KB por imagem.

O alvo de 150-250KB do Blueprint pressupunha redimensionar antes de
comprimir, o que era razoável quando a inferência recebia a foto inteira
reduzida para 224x224. **Deixou de ser possível em 2026-11-02**, quando o
diagnóstico passou a ser por janela deslizante
(cloud/app/core/janelas.py): o servidor recorta janelas de 896 px nativos
com passo de 448 e as entrega ao modelo no regime em que ele foi
treinado, com redução de 4x em vez dos 20,6x da foto inteira. Essa
geometria se aplica aos PIXELS DA IMAGEM RECEBIDA.

Encolher aqui não economizaria storage de graça: encolheria junto a
quantidade de janelas aproveitáveis e, abaixo de JANELAS_MINIMAS = 6, o
servidor passa a recusar o diagnóstico. Reduzir o upload significa, na
prática, degradar o diagnóstico.

SE O STORAGE APERTAR, a ordem de preferência é: reduzir a FREQUÊNCIA de
captura (crontab), ou apagar capturas antigas já representadas no
conjunto rotulado, ou subir de plano. Mexer em `quality` é o último
recurso, e não deve ser feito sem medir o efeito no diagnóstico: está
documentado em cloud/app/core/inference.py que até a escolha do
interpolador de redimensionamento (NEAREST contra BILINEAR) muda a classe
prevista, então artefato de compressão também pode mudar.

IMPORTANTE: verificar que libjpeg-turbo está de fato ativo no SO antes
de medir performance, sem ele, o Pillow é ~5x mais lento (Blueprint,
Pontos de Atenção).

Relação com o resto do sistema:
- Recebe a imagem crua de edge/src/capture.py.
- A imagem comprimida resultante é o que entra na fila offline
  (edge/src/fila/offline_queue.py) e, depois, é enviada para a API.
- O tamanho do que sai daqui é o que consome o bucket do Supabase
  Storage. Ver infra/supabase/README.md para o consumo medido.
"""

import io

from PIL import Image


def comprimir_imagem(bytes_imagem_crua: bytes, quality: int = 70) -> bytes:
    """Reencoda para JPEG sem redimensionar. Resulta em 1,3 a 1,5 MB.

    A resolução nativa é preservada de propósito: o diagnóstico por
    janela deslizante do servidor depende dela. Ver o cabeçalho deste
    módulo antes de tentar reduzir o tamanho do arquivo aqui.
    """
    imagem = Image.open(io.BytesIO(bytes_imagem_crua))
    imagem = imagem.convert("RGB")

    buffer = io.BytesIO()
    imagem.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()
