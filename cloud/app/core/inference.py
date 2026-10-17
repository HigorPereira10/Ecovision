"""
cloud/app/core/inference.py

Carregamento e execução do modelo .tflite via TFLite Runtime, a peça
central da camada de backend (Blueprint v3.0, Fase 4).

Regras não negociáveis (Blueprint Seção 4.4 e Pontos de Atenção):
- Instalar/usar apenas o pacote `tflite-runtime`, NUNCA `tensorflow`
  completo (estoura a RAM de 1GB do Railway).
- O modelo é carregado em memória UMA VEZ (no startup de app/main.py),
  não a cada requisição.
- O modelo .tflite deve estar versionado no repositório (ver ml/models/)
  e chegar ao servidor via deploy do GitHub Actions, nunca por upload
  manual em volume stateful.

Estado em 2026-10-10: o modelo real está em ml/models/modelo.tflite,
com 3 classes (ver _CLASSES_DO_MODELO). Mesmo assim, a API nunca
recusa subir por causa dele: em 3 situações ela sobe normalmente e a
inferência devolve um resultado placeholder, com aviso no log. São
elas: (a) nenhum runtime TFLite instalado, (b) o arquivo do modelo não
existe no caminho configurado, (c) o arquivo existe mas falha ao
carregar. Isso mantém o resto do pipeline (storage + banco) de pé
mesmo com problema no modelo.

ATENÇÃO: nenhum desses 3 casos derruba a API. Se algo aqui for alterado
no futuro, manter esse comportamento é importante: uma falha no modelo
nunca pode impedir o resto do sistema (upload da imagem, gravação no
banco) de funcionar.

Relação com o resto do sistema:
- Chamado por app/api/routes/diagnostico.py a cada requisição do Pi.
- O modelo consumido aqui é o artefato exportado por ml/src/export/convert_tflite.py.
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

# POR QUE ESTA GUARDA EXISTE, com os números que a motivaram.
#
# O modelo tem três saídas e nenhuma delas é "isto não é uma folha".
# Toda entrada é distribuída entre as três classes, e medindo em
# 2026-10-17 descobrimos para onde ele empurra o que não entende:
#
#   imagem preta      -> saudavel  0.93
#   quase preta       -> saudavel  0.97
#   ruído aleatório   -> saudavel  0.94
#   verde liso        -> saudavel  0.90
#
# E, pior, a confiança CRESCE conforme a foto escurece. A mesma imagem
# de folha sadia, escurecida artificialmente:
#
#   100% de luz -> saudavel 0.69
#    50% de luz -> saudavel 0.91
#    25% de luz -> saudavel 0.97
#
# A consequência prática é grave: numa estufa à noite, ou com o Ring LED
# fraco, o sistema afirmaria "saudável" com 95% de confiança mesmo com a
# planta doente. É falso negativo sistemático, o pior erro possível para
# o propósito do projeto, porque o produtor não tem como desconfiar.
#
# Por isso a imagem é avaliada ANTES de classificar. Reprovada, a
# captura é gravada normalmente (foto, leituras, alerta ambiental), mas
# NENHUM diagnóstico de doença é afirmado: o produtor vê a própria foto
# e o motivo, e decide o que fazer. Decisão do grupo em 2026-10-17:
# guardar a foto é o que permite conferir se o aviso estava certo e
# identificar o problema (lente suja, LED queimado, captura noturna)
# olhando a imagem.

# Limiares medidos, não arbitrados. Sobre as 6 fotos reais de
# ml/validacao_externa/, que o modelo classifica de forma utilizável:
#
#   brilho médio:  74,6 a 207,1
#   textura (desvio padrão): 35,2 a 71,4
#
# Contra a mesma foto escurecida e contra imagens sem conteúdo:
#
#   25% de luz          -> brilho  51,4   textura 17,8
#   15% de luz          -> brilho  30,6   textura 10,7
#   parede/lente tampada-> brilho qualquer textura  0,0
#
# A textura separa melhor que o brilho: ela cai junto com a luz e vai a
# zero em imagem lisa. O piso de 25 mantém margem sobre a pior foto boa
# (35,2) sem deixar passar a de 25% de luz.
BRILHO_MINIMO = 40.0
TEXTURA_MINIMA = 25.0

# LIMITAÇÃO CONHECIDA: ruído aleatório puro passa nos dois testes
# (brilho 127, textura 49). Não é um modo de falha de câmera real (uma
# câmera com defeito produz foto escura, borrada ou lisa, não ruído
# uniforme), e inventar um terceiro teste para cobrir um caso que não
# acontece custaria mais do que entrega.


def avaliar_qualidade_imagem(bytes_imagem: bytes) -> str | None:
    """Devolve o motivo pelo qual a imagem não serve para diagnóstico,
    ou None quando ela serve.

    O texto devolvido vai direto para o produtor, então ele diz o que
    fazer, não o que mediu."""
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

# Frase fixa que entra no final de toda recomendação de doença/praga.
# O sistema dá apenas orientação agronômica GERAL (pesquisada, com fonte,
# ver ADR 0006), nunca prescrição de produto ou dosagem: isso exige
# responsabilidade técnica de um engenheiro agrônomo.
_SUFIXO_RECOMENDACAO = " Consulte um engenheiro agrônomo para definir produto e dosagem específicos."

# Mapeamento índice -> (classe, recomendação, severidade). As 10 classes
# são as do dataset PlantVillage (tomate) usado em ml/ ("Frankenstein
# Cirúrgico", ver ml/README.md). As recomendações e a severidade de cada
# classe foram pesquisadas com fontes citadas em
# docs/decisions/0006-recomendacoes-por-diagnostico.md.
#
# Severidade ("alta" | "media"): "alta" é para doenças sem cura (só dá
# pra controlar o vetor ou prevenir) ou com risco de perda total da
# lavoura segundo a fonte citada. "media" é para as demais, que têm
# tratamento ou controle disponível e progressão mais lenta.
#
# Esta lista é o CATÁLOGO agronômico, indexado por NOME, não pela
# saída do modelo. A ordem aqui não tem mais significado: quem define
# qual índice do modelo é qual classe é _CLASSES_DO_MODELO, logo abaixo.
# Separar os dois foi necessário porque o modelo entregue tem 3 classes
# e este catálogo tem 10: enquanto o índice do modelo era lido direto
# aqui, a saída 2 (que no modelo é "saudavel") virava "pinta_preta", e
# o produtor recebia instrução de pulverizar fungicida numa folha sã.
_CATALOGO_AGRONOMICO: list[tuple[str, str | None, str | None]] = [
    ("saudavel", None, None),
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

# Ordem EXATA das saídas do modelo em ml/models/modelo.tflite. Vem do
# treino, onde tf.keras.utils.image_dataset_from_directory ordena os
# diretórios de classe alfabeticamente. Tem que bater com a lista
# CLASSES de ml/src/export/convert_tflite.py.
#
# O índice 0 é "distrator_septoria" no treino do ml/: a pasta nasceu
# com esse nome por ter sido incluída como distrator (evitar que tudo
# vire pinta_preta). Aqui ele é publicado como "septoriose", que é o
# nome da doença no catálogo acima, decisão do grupo em 2026-10-10
# depois de o Carlos validar a classe. Assim o diagnóstico chega ao
# produtor com a recomendação agronômica de septoriose (ADR 0006).
#
# SE O MODELO FOR RETREINADO: trocar o .tflite não basta se a
# quantidade ou a ordem das classes mudar. Esta lista tem que
# acompanhar, senão cada predição sai com o rótulo de outra doença e
# nada falha de forma visível.
_CLASSES_DO_MODELO: list[str] = ["septoriose", "pinta_preta", "saudavel"]


def carregar_modelo_tflite(caminho_modelo: str) -> Any | None:
    """Carrega o interpretador TFLite uma única vez, no startup da API.

    IMPORTANTE: nunca levanta exceção. Se o runtime não estiver
    instalado ou o modelo não puder ser carregado, retorna None e a API
    continua funcionando normalmente, só que com resultado placeholder.
    """
    # Dois runtimes, na ordem de preferência. O `tflite-runtime` é o que
    # o Blueprint cita e o que roda no Linux do Railway. O
    # `ai-edge-litert` é o sucessor oficial do mesmo projeto e existe
    # para Windows e ARM64, plataformas onde o `tflite-runtime` não tem
    # wheel. Sem esse segundo caminho, rodar a API localmente no Windows
    # caía no resultado placeholder EM SILÊNCIO, dando a impressão de
    # que a inferência tinha sido testada quando não tinha.
    #
    # Nenhum dos dois é o pacote `tensorflow` completo, que continua
    # proibido aqui (estoura a RAM de 1GB do Railway).
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
            "resultado placeholder. O modelo DEVERIA estar versionado em "
            "ml/models/modelo.tflite; se a API subiu sem ele, o deploy não "
            "trouxe o diretório ml/ (ver ADR 0014).",
            caminho_modelo,
        )
        return None

    try:
        interpretador = Interpreter(model_path=caminho_modelo)
        interpretador.allocate_tensors()
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
    """Prepara a imagem recebida do Pi para entrar no modelo: 224x224,
    RGB, pixels float32 CRUS de 0 a 255. Tudo em memória, sem gravar
    nada em disco (o Pillow resolve isso lendo do BytesIO).

    NÃO dividir por 255 e NÃO aplicar preprocess_input aqui. O modelo
    exportado por ml/src/export/convert_tflite.py já tem a camada de
    normalização da MobileNetV2 dentro do grafo. Normalizar de novo por
    fora não levanta erro nenhum: as predições simplesmente colapsam
    para "saudavel" com cerca de 90% de confiança em qualquer foto,
    inclusive em folha visivelmente doente.

    O método de redimensionamento também não é detalhe. O treino usou
    tf.keras.utils.load_img, cujo padrão é vizinho mais próximo
    (NEAREST). Medido nas 6 imagens de ml/validacao_externa/: com
    NEAREST a saída bate com o Keras original nas 6, casa decimal por
    casa decimal; com BILINEAR ou BICUBIC (este último é o padrão do
    Pillow, o que estava em uso aqui) nenhuma das 6 bate, e DUAS
    trocam de classe. Ou seja, trocar a interpolação muda diagnóstico.
    """
    import io

    imagem = Image.open(io.BytesIO(bytes_imagem)).convert("RGB")
    imagem = imagem.resize(TAMANHO_ENTRADA, Image.Resampling.NEAREST)
    array = np.asarray(imagem, dtype=np.float32)
    return np.expand_dims(array, axis=0)  # adiciona a dimensão de "lote" (batch) de 1 imagem


def rodar_inferencia(interpretador: Any | None, imagem_preprocessada: np.ndarray) -> dict:
    """Retorna {'classe': str, 'confianca': float, 'recomendacao': str | None,
    'severidade': str | None}. Sem modelo carregado, devolve o placeholder
    em vez de falhar."""
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
        # O modelo devolveu mais saídas do que _CLASSES_DO_MODELO
        # descreve, ou seja, o .tflite foi trocado sem atualizar a
        # lista. Não dá para adivinhar o nome, então registra o índice
        # cru e não emite recomendação: melhor um diagnóstico sem texto
        # do que o texto da doença errada.
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
