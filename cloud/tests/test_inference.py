"""
cloud/tests/test_inference.py

O que este arquivo verifica, em português simples:

Desde 2026-10-10 existe um modelo real em ml/models/modelo.tflite (3
classes). Ainda assim, a API precisa continuar de pé quando o modelo
não puder ser carregado (runtime ausente, arquivo faltando, arquivo
corrompido), devolvendo um resultado "placeholder" e avisando no log,
em vez de recusar subir. Uma falha no modelo nunca pode derrubar o
upload da imagem nem a gravação no banco.

Também confere o pré-processamento da imagem, que tem duas
particularidades capazes de corromper TODO diagnóstico sem levantar
erro nenhum, e por isso valem teste próprio:

1. Os pixels precisam sair CRUS, de 0 a 255. O modelo normaliza por
   dentro; dividir por 255 aqui faz tudo virar "saudavel" com ~90% de
   confiança, inclusive folha doente.
2. O redimensionamento precisa ser por vizinho mais próximo, igual ao
   do treino. Com interpolação diferente, 2 das 6 imagens de
   ml/validacao_externa/ trocam de classe.
"""

import io
from pathlib import Path

import numpy as np
from PIL import Image

from app.core import inference


def _imagem_de_teste() -> bytes:
    imagem = Image.new("RGB", (800, 600), color=(100, 150, 80))
    buffer = io.BytesIO()
    imagem.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_preprocessar_imagem_gera_formato_esperado():
    array = inference.preprocessar_imagem(_imagem_de_teste())

    assert array.shape == (1, 224, 224, 3)
    assert array.dtype == np.float32


def test_preprocessar_imagem_devolve_pixels_crus_e_nao_normalizados():
    """Regressão: a versão anterior dividia por 255. Como o modelo
    normaliza por dentro, isso colapsava toda predição para 'saudavel'
    sem erro nenhum."""
    array = inference.preprocessar_imagem(_imagem_de_teste())

    # A imagem de teste é lisa, cor (100, 150, 80). Se alguém voltar a
    # normalizar, esses valores viram 0.39/0.59/0.31 e o teste pega.
    assert array.max() > 1.0, "os pixels foram normalizados; o modelo espera 0-255"
    assert round(float(array[0, 0, 0, 1])) == 150


def test_preprocessar_imagem_usa_vizinho_mais_proximo_no_redimensionamento():
    """Regressão: o padrão do Pillow é bicúbico, e o treino usou vizinho
    mais próximo. Medido nas 6 imagens de validação externa, a troca de
    interpolação muda a classe de 2 delas."""
    # Tabuleiro de 2x2 pixels: com vizinho mais próximo, a ampliação
    # para 224x224 preserva exatamente os dois valores originais. Com
    # bicúbico ou bilinear, aparecem tons intermediários nas bordas.
    original = Image.new("RGB", (2, 2))
    original.putpixel((0, 0), (0, 0, 0))
    original.putpixel((1, 0), (255, 255, 255))
    original.putpixel((0, 1), (255, 255, 255))
    original.putpixel((1, 1), (0, 0, 0))
    buffer = io.BytesIO()
    original.save(buffer, format="PNG")

    array = inference.preprocessar_imagem(buffer.getvalue())

    valores = set(np.unique(array).tolist())
    assert valores <= {0.0, 255.0}, (
        f"apareceram tons intermediarios {sorted(valores)[:5]}: o redimensionamento "
        "nao esta usando vizinho mais proximo"
    )


def test_classes_do_modelo_batem_com_o_conversor():
    """A ordem aqui precisa ser a mesma de ml/src/export/convert_tflite.py.
    Se divergir, cada predição sai com o nome e a recomendação de outra
    doença, e nada falha de forma visível."""
    assert inference._CLASSES_DO_MODELO == [
        "septoriose",
        "pinta_preta",
        "saudavel",
        "estresse_foliar",
    ]

    # Toda classe do modelo precisa existir no catálogo agronômico,
    # senão o produtor recebe diagnóstico sem orientação nenhuma.
    for classe in inference._CLASSES_DO_MODELO:
        assert classe in inference._INFO_POR_CLASSE, f"{classe} fora do catalogo"


def test_carregar_modelo_com_arquivo_inexistente_retorna_none_sem_quebrar():
    interpretador = inference.carregar_modelo_tflite("/caminho/que/nao/existe.tflite")
    assert interpretador is None


def test_rodar_inferencia_sem_modelo_devolve_placeholder():
    array = inference.preprocessar_imagem(_imagem_de_teste())
    resultado = inference.rodar_inferencia(None, array)

    assert resultado == {
        "classe": "indisponivel",
        "confianca": 0.0,
        "recomendacao": None,
        "severidade": None,
    }


def test_caminho_do_modelo_resolve_a_partir_da_raiz_do_repo():
    """Regressão: TFLITE_MODEL_PATH é relativo e era resolvido contra o
    diretório de trabalho do processo. Como a API sobe de dentro de
    cloud/, ela procurava em cloud/ml/models/ e subia SEM MODELO, em
    silêncio, devolvendo placeholder como se nada estivesse errado."""
    from pathlib import Path

    from app.config import get_settings

    caminho = Path(get_settings().caminho_do_modelo)

    assert caminho.is_absolute(), "o caminho precisa independer de onde o processo rodou"
    assert caminho.is_file(), (
        f"modelo nao encontrado em {caminho}. O .tflite e versionado no repositorio "
        "(Blueprint Secao 4.4): se sumiu ou foi renomeado, a API sobe sem inferencia."
    )


# --------------------------------------------- guarda de qualidade de imagem

def _imagem_jpeg(cor, tamanho=(224, 224)) -> bytes:
    from io import BytesIO
    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", tamanho, cor).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_foto_escura_demais_e_reprovada():
    """O caso que motivou a guarda: o modelo responde 'saudavel' com 0,93
    a 0,97 de confiança para imagem preta, e a confiança CRESCE conforme
    a foto escurece. Classificar isso afirmaria 'sua planta está
    saudável' sobre uma imagem onde não se vê nada."""
    motivo = inference.avaliar_qualidade_imagem(_imagem_jpeg((10, 10, 12)))

    assert motivo is not None
    assert "escura" in motivo.lower()
    assert "iluminação" in motivo.lower(), "a mensagem tem que dizer o que fazer"


def test_imagem_lisa_e_reprovada_por_falta_de_detalhe():
    """Parede, lente tampada ou fora de foco total: brilho pode estar
    perfeito e não haver folha nenhuma. Textura zero é o sinal."""
    motivo = inference.avaliar_qualidade_imagem(_imagem_jpeg((128, 128, 128)))

    assert motivo is not None
    assert "detalhe" in motivo.lower()
    assert "lente" in motivo.lower()


def test_foto_real_do_conjunto_de_validacao_passa():
    """A guarda não pode reprovar foto boa. Usa a imagem MAIS ESCURA do
    conjunto de validação externa (brilho 74,6, textura 35,2), que é o
    pior caso real conhecido: se ela passar, as outras passam."""
    from pathlib import Path

    caminho = Path(__file__).resolve().parents[2] / "ml" / "validacao_externa" / "pinta_preta_01.jpg"
    if not caminho.is_file():
        import pytest

        pytest.skip("conjunto de validação externa não disponível")

    assert inference.avaliar_qualidade_imagem(caminho.read_bytes()) is None


def test_limiares_mantem_margem_sobre_a_pior_foto_boa():
    """Trava de regressão sobre os números, não sobre o comportamento.

    Os limiares foram escolhidos a partir de medição (brilho de 74,6 a
    207,1 e textura de 35,2 a 71,4 nas fotos boas). Subir TEXTURA_MINIMA
    para perto de 35 passaria a reprovar foto legítima, e o sintoma
    seria o sistema recusando analisar plantas de verdade."""
    assert inference.TEXTURA_MINIMA < 35.2, "nao pode alcancar a pior foto boa"
    assert inference.BRILHO_MINIMO < 74.6
    # E não pode ser tão frouxo a ponto de deixar passar 25% de luz
    # (brilho 51,4 / textura 17,8), que foi o caso medido em que o
    # modelo devolveu 0,97 de confiança para lixo.
    assert inference.TEXTURA_MINIMA > 17.8


def test_modelo_com_numero_de_saidas_diferente_da_lista_nao_carrega(tmp_path, caplog):
    """BUG REAL de 2026-11-02: o padrao de TFLITE_MODEL_PATH foi trocado
    para o modelo de 4 classes, mas cloud/.env define a mesma variavel e
    ganha do padrao. Rodou o modelo ANTIGO de 3 saidas com 4 nomes
    listados, e elegeu "septoriose" com severidade ALTA numa planta sem
    doenca, sem erro nenhum.

    A protecao que existia so pegava o caso inverso (modelo maior que a
    lista). Este teste trava o caso perigoso: lista maior que o modelo.
    """
    import logging

    caminho = Path(__file__).resolve().parents[2] / "ml" / "models" / "modelo.tflite"
    if not caminho.is_file():
        pytest.skip("modelo de 3 classes nao esta no disco")

    original = inference._CLASSES_DO_MODELO
    inference._CLASSES_DO_MODELO = ["a", "b", "c", "d"]  # 4 nomes, modelo tem 3
    try:
        with caplog.at_level(logging.ERROR):
            interpretador = inference.carregar_modelo_tflite(str(caminho))
    finally:
        inference._CLASSES_DO_MODELO = original

    assert interpretador is None, "carregar com nomes a mais devolve None"
    assert "saídas" in caplog.text, "o log tem que dizer o que esta errado"
