"""
Carregamento e execução do modelo .tflite, verificação de qualidade da
imagem e catálogo de recomendações por classe.

O modelo é carregado uma vez, na inicialização, com um runtime leve
(ai-edge-litert ou tflite-runtime); o pacote tensorflow completo excede a
memória do servidor. A API nunca deixa de iniciar por causa do modelo: sem
runtime, sem arquivo ou com falha de carregamento, a inferência devolve um
resultado provisório e o restante do fluxo (armazenamento e banco)
continua funcionando.
"""

import io
import logging
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

logger = logging.getLogger("ecovision.cloud.inference")

TAMANHO_ENTRADA = (224, 224)

RESULTADO_INDISPONIVEL = {
    "classe": "indisponivel",
    "confianca": 0.0,
    "recomendacao": None,
    "severidade": None,
}

# --- Guarda de qualidade de imagem ---

CLASSE_IMAGEM_INADEQUADA = "imagem_inadequada"

# O modelo não tem uma saída para "não é folha": toda entrada é
# distribuída entre as classes conhecidas. Imagens pretas, ruído ou verde
# liso saem como "saudavel" com mais de 0,90 de confiança, e a confiança
# aumenta conforme a foto escurece. Sem esta verificação, capturas
# noturnas ou com o LED falhando produziriam falsos negativos com alta
# confiança. Uma captura reprovada é gravada normalmente (foto, leituras e
# alerta), mas nenhum diagnóstico é afirmado.

# Limiares medidos em fotos reais classificáveis:
#   brilho médio:            74,6 a 207,1
#   textura (desvio padrão): 35,2 a 71,4
# e em fotos inadequadas:
#   25% de luz:              brilho 51,4, textura 17,8
#   lente tampada ou parede: textura 0,0
# A textura separa melhor: cai junto com a luz e vai a zero em imagem lisa.
BRILHO_MINIMO = 40.0
TEXTURA_MINIMA = 25.0

# Limitação conhecida: ruído aleatório passa nos dois testes, mas não é um
# modo de falha real de câmera.


def avaliar_qualidade_imagem(bytes_imagem: bytes) -> str | None:
    """Devolve o motivo pelo qual a imagem não serve para diagnóstico, ou
    None quando ela serve. O texto é exibido ao produtor."""
    imagem = Image.open(io.BytesIO(bytes_imagem)).convert("L")
    cinza = np.asarray(imagem, dtype=np.float32)
    brilho = float(cinza.mean())
    textura = float(cinza.std())

    if brilho < BRILHO_MINIMO:
        logger.warning(
            "Imagem reprovada por escuridão: brilho=%.1f (mínimo %.1f)",
            brilho, BRILHO_MINIMO,
        )
        return (
            "A foto está escura demais para análise. Verifique se a "
            "iluminação do dispositivo acendeu no momento da captura."
        )

    if textura < TEXTURA_MINIMA:
        logger.warning(
            "Imagem reprovada por falta de detalhe: textura=%.1f (mínimo %.1f)",
            textura, TEXTURA_MINIMA,
        )
        return (
            "A foto não tem detalhe suficiente para análise. Verifique se "
            "a lente está limpa e desobstruída e se a câmera está apontada "
            "para a folha."
        )

    return None

# Frase acrescentada a toda recomendação de doença ou praga: o sistema dá
# orientação agronômica geral, nunca prescrição de produto ou dose.
_SUFIXO_RECOMENDACAO = " Consulte um engenheiro agrônomo para definir produto e dosagem específicos."

# Catálogo agronômico: classe -> (recomendação, severidade), indexado por
# nome. Cobre as classes de tomateiro do PlantVillage e a classe de
# estresse foliar; o modelo em produção usa só parte delas, na ordem de
# _CLASSES_DO_MODELO.
#
# Severidade "alta": doença sem cura ou com risco de perda total segundo a
# fonte; "media": doença com controle disponível e progressão mais lenta.
_CATALOGO_AGRONOMICO: list[tuple[str, str | None, str | None]] = [
    ("saudavel", None, None),
    # A recomendação não nomeia a causa: identificar uma deficiência
    # específica exigiria conhecer a adubação. A Embrapa chama esse quadro
    # de distúrbio fisiológico (LOPES; REIS, Doenças do tomateiro cultivado
    # em ambiente protegido, Circular Técnica 100, 2. ed., 2011).
    (
        "estresse_foliar",
        "Alteração na folha que não corresponde às doenças que o sistema "
        "reconhece. A Embrapa chama esse quadro de distúrbio fisiológico: "
        "pode vir de falta ou excesso de nutriente, de fitotoxicidez por "
        "agrotóxico ou de luz inadequada. Confira a planta de perto e "
        "verifique também a irrigação."
        # Sem o sufixo padrão: não há produto a recomendar, e sim a causa a
        # confirmar.
        " Consulte um engenheiro agrônomo para confirmar a causa.",
        "media",
    ),
    (
        "requeima",
        "Favorecida por umidade acima de 90% e temperaturas amenas (11-23°C). "
        "Aplique fungicida preventivo quando o clima estiver favorável à doença, "
        "evite molhar a folhagem na irrigação e remova folhas/plantas afetadas."
        + _SUFIXO_RECOMENDACAO,
        "alta",  # Embrapa: pode causar perda de até 100% da produção sem manejo
    ),
    (
        "pinta_preta",
        "Faça pulverização preventiva com fungicida registrado, evite cultivo "
        "próximo a batata/outras solanáceas e prefira irrigação por gotejamento "
        "ou sulco em vez de aspersão, que molha a folhagem."
        + _SUFIXO_RECOMENDACAO,
        "media",
    ),
    (
        "mancha_bacteriana",
        "Não há cura para uma planta já infectada. Use sementes/mudas sadias, "
        "evite molhar a folhagem, rotacione a cultura e considere cultivares "
        "resistentes; bactericida à base de cobre pode reduzir a disseminação."
        + _SUFIXO_RECOMENDACAO,
        "alta",  # sem cura para planta já infectada
    ),
    (
        "mofo_de_folha",
        "Típico de estufa com umidade do ar alta (75-90%). Melhore a ventilação "
        "e o espaçamento das plantas para manter a umidade abaixo de 85%, "
        "estaqueie/pode para aumentar a circulação de ar."
        + _SUFIXO_RECOMENDACAO,
        "media",
    ),
    (
        "septoriose",
        "Mais comum em épocas quentes e chuvosas. Use sementes/mudas sadias, "
        "elimine restos de cultura e plantas voluntárias, evite plantio perto "
        "de lavoura antiga ou infectada."
        + _SUFIXO_RECOMENDACAO,
        "alta",  # Embrapa: perdas de ate 100% e morte da planta em casos graves
    ),
    (
        "acaro_rajado",
        "É uma praga (ácaro), não um fungo. Monitore a face inferior das "
        "folhas; controle biológico com ácaros predadores é indicado a partir "
        "de aproximadamente 5 ácaros por folíolo."
        + _SUFIXO_RECOMENDACAO,
        "media",
    ),
    (
        "mancha_alvo",
        "Favorecida por umidade do ar acima de 80%, temperatura entre 18-21°C "
        "e folha molhada por 12h ou mais. Remova folhas com sintomas e prefira "
        "cultivares resistentes."
        + _SUFIXO_RECOMENDACAO,
        "media",
    ),
    (
        "vira_cabeca",
        "Causada por vírus transmitido pela mosca-branca, sem cura. O "
        "foco é no controle do vetor: mudas em ambiente protegido, eliminar "
        "plantas daninhas hospedeiras, controlar a mosca-branca e remover "
        "plantas infectadas e restos de cultura."
        + _SUFIXO_RECOMENDACAO,
        "alta",  # virus sem cura
    ),
    (
        "mosaico",
        "Vírus transmitido por semente e por contato mecânico (mãos, "
        "ferramentas), sem cura. Priorize cultivares resistentes, use "
        "sementes certificadas e higienize mãos/ferramentas entre plantas."
        + _SUFIXO_RECOMENDACAO,
        "alta",  # virus sem cura
    ),
]


_INFO_POR_CLASSE: dict[str, tuple[str | None, str | None]] = {
    nome: (recomendacao, severidade) for nome, recomendacao, severidade in _CATALOGO_AGRONOMICO
}


# Nome de cada classe para textos gravados, como o título dos alertas,
# sem sublinhados e sem nome científico (que alongaria o título no celular).
_ROTULO_PARA_PRODUTOR: dict[str, str] = {
    "saudavel": "planta sadia",
    "estresse_foliar": "estresse foliar",
    "septoriose": "septoriose",
    "pinta_preta": "pinta preta",
    "requeima": "requeima",
    "mancha_bacteriana": "mancha bacteriana",
    "mofo_de_folha": "mofo de folha",
    "acaro_rajado": "ácaro rajado",
    "mancha_alvo": "mancha alvo",
    "vira_cabeca": "vira-cabeça",
    "mosaico": "mosaico",
}


def rotulo_para_produtor(classe: str) -> str:
    """Nome da classe para texto exibido.

    Uma classe fora da tabela usa o nome técnico com espaços no lugar dos
    sublinhados.
    """
    rotulo = _ROTULO_PARA_PRODUTOR.get(classe)
    if rotulo is not None:
        return rotulo
    return classe.replace("_", " ").strip() or "condição desconhecida"

# Ordem exata das saídas do modelo em produção, definida no treino
# (ml/src/training/ajuste_dominio_proprio.py). Trocar o .tflite sem
# atualizar esta lista atribui a cada predição o nome e a recomendação de
# outra classe, sem erro visível. "septoriose" corresponde à pasta
# "distrator_septoria" do treino.
_CLASSES_DO_MODELO: list[str] = [
    "septoriose",
    "pinta_preta",
    "saudavel",
    "estresse_foliar",
]


def carregar_modelo_tflite(caminho_modelo: str) -> Any | None:
    """Carrega o interpretador TFLite uma vez, na inicialização da API.

    Nunca levanta exceção: sem runtime ou sem modelo, devolve None e a API
    segue com resultado provisório.
    """
    # Runtimes em ordem de preferência: tflite-runtime e ai-edge-litert (o
    # sucessor, com pacotes também para Windows e ARM64). O pacote
    # tensorflow completo não deve ser usado.
    Interpreter = None
    for modulo in ("tflite_runtime.interpreter", "ai_edge_litert.interpreter"):
        try:
            Interpreter = __import__(modulo, fromlist=["Interpreter"]).Interpreter
            break
        except ImportError:
            continue

    if Interpreter is None:
        logger.warning(
            "Nenhum runtime TFLite instalado (tflite-runtime ou ai-edge-litert): "
            "a inferência vai devolver resultado placeholder."
        )
        return None

    if not Path(caminho_modelo).is_file():
        logger.warning(
            "Modelo .tflite não encontrado em %s: a inferência vai devolver "
            "resultado provisório. Confira TFLITE_MODEL_PATH e se o diretório "
            "ml/models/ foi incluído na implantação.",
            caminho_modelo,
        )
        return None

    try:
        interpretador = Interpreter(model_path=caminho_modelo)
        interpretador.allocate_tensors()

        # Confere o número de saídas contra _CLASSES_DO_MODELO: um modelo
        # com menos saídas do que nomes listados não geraria erro, apenas
        # rótulos errados com alta confiança.
        saidas = int(interpretador.get_output_details()[0]["shape"][-1])
        if saidas != len(_CLASSES_DO_MODELO):
            logger.error(
                "Modelo em %s tem %d saídas, mas _CLASSES_DO_MODELO lista %d "
                "nomes (%s). A API sobe com resultado placeholder em vez de "
                "diagnosticar com os nomes trocados. Confira TFLITE_MODEL_PATH "
                "(o .env sobrepõe o padrão do código) e a lista de classes.",
                caminho_modelo, saidas, len(_CLASSES_DO_MODELO),
                _CLASSES_DO_MODELO,
            )
            return None

        return interpretador
    except Exception:
        logger.warning(
            "Falha ao carregar o modelo .tflite em %s: a inferência vai devolver "
            "resultado placeholder.",
            caminho_modelo,
            exc_info=True,
        )
        return None


def preprocessar_imagem(bytes_imagem: bytes) -> np.ndarray:
    """Prepara a imagem para o modelo: 224 × 224, RGB, float32 com pixels
    de 0 a 255, em memória.

    Não dividir por 255 nem aplicar preprocess_input: a normalização faz
    parte do modelo exportado, e normalizar de novo leva quase todas as
    predições a "saudavel". O redimensionamento usa o vizinho mais próximo:
    é o que reproduz as predições do modelo Keras original e, nas imagens
    de campo, deu melhor resultado do que a interpolação bilinear.
    """
    import io

    imagem = Image.open(io.BytesIO(bytes_imagem)).convert("RGB")
    imagem = imagem.resize(TAMANHO_ENTRADA, Image.Resampling.NEAREST)
    array = np.asarray(imagem, dtype=np.float32)
    return np.expand_dims(array, axis=0)  # dimensão de lote


def rodar_inferencia(interpretador: Any | None, imagem_preprocessada: np.ndarray) -> dict:
    """Devolve {'classe', 'confianca', 'recomendacao', 'severidade'}; sem
    modelo carregado, devolve o resultado provisório."""
    if interpretador is None:
        return dict(RESULTADO_INDISPONIVEL)

    detalhes_entrada = interpretador.get_input_details()
    detalhes_saida = interpretador.get_output_details()

    interpretador.set_tensor(detalhes_entrada[0]["index"], imagem_preprocessada)
    interpretador.invoke()
    saida = interpretador.get_tensor(detalhes_saida[0]["index"])[0]

    indice_previsto = int(np.argmax(saida))
    confianca = float(saida[indice_previsto])

    if indice_previsto < len(_CLASSES_DO_MODELO):
        classe = _CLASSES_DO_MODELO[indice_previsto]
        recomendacao, severidade = _INFO_POR_CLASSE.get(classe, (None, None))
    else:
        # Índice além de _CLASSES_DO_MODELO: o .tflite foi trocado sem
        # atualizar a lista. Registra o índice e não emite recomendação.
        logger.error(
            "Modelo devolveu indice %s, fora de _CLASSES_DO_MODELO (%s classes). "
            "O .tflite provavelmente foi trocado sem atualizar a lista.",
            indice_previsto,
            len(_CLASSES_DO_MODELO),
        )
        classe, recomendacao, severidade = f"classe_{indice_previsto}", None, None

    return {
        "classe": classe,
        "confianca": confianca,
        "recomendacao": recomendacao,
        "severidade": severidade,
    }
