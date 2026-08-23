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

Estado real do projeto nesta rodada: o modelo ainda não existe (ml/ é
esqueleto). Em vez de a API recusar subir, ela sobe normalmente e
qualquer chamada de inferência devolve um resultado placeholder, com
um aviso (warning) no log. Isso acontece em 3 situações, todas
tratadas do mesmo jeito: (a) tflite_runtime não está instalado no
ambiente, (b) o arquivo do modelo não existe no caminho configurado,
(c) o arquivo existe mas falha ao carregar (corrompido ou em formato
inválido). Isso deixa o resto do pipeline (storage + banco) testável e
implantável antes do time de ML entregar o modelo de verdade.

ATENÇÃO: nenhum desses 3 casos derruba a API. Se algo aqui for alterado
no futuro, manter esse comportamento é importante: uma falha no modelo
nunca pode impedir o resto do sistema (upload da imagem, gravação no
banco) de funcionar.

Relação com o resto do sistema:
- Chamado por app/api/routes/diagnostico.py a cada requisição do Pi.
- O modelo consumido aqui é o artefato exportado por ml/src/export/convert_tflite.py.
"""

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
# CUIDADO, MUITO IMPORTANTE: a ORDEM desta lista precisa ser IGUAL ao
# índice de saída do modelo .tflite real quando ml/ entregar o treino.
# Se a ordem das classes usada no treino for diferente desta lista, o
# sistema vai mostrar a recomendação errada para o agricultor (ex.:
# recomendar tratamento de mofo de folha quando na verdade é
# septoriose). Conferir e ajustar essa lista assim que o modelo real
# chegar, antes de colocar em produção.
_CLASSES_PLACEHOLDER: list[tuple[str, str | None, str | None]] = [
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


def carregar_modelo_tflite(caminho_modelo: str) -> Any | None:
    """Carrega o interpretador TFLite uma única vez, no startup da API.

    IMPORTANTE: nunca levanta exceção. Se o runtime não estiver
    instalado ou o modelo não puder ser carregado, retorna None e a API
    continua funcionando normalmente, só que com resultado placeholder.
    """
    try:
        from tflite_runtime.interpreter import Interpreter
    except ImportError:
        logger.warning(
            "tflite_runtime não instalado: a inferência vai devolver resultado "
            "placeholder até o ambiente ter o pacote e um modelo de verdade."
        )
        return None

    if not Path(caminho_modelo).is_file():
        logger.warning(
            "Modelo .tflite não encontrado em %s: a inferência vai devolver "
            "resultado placeholder até o time de ML entregar o modelo.",
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
    """Redimensiona a imagem para 224x224 e normaliza os valores de cor
    para o intervalo [0, 1]. Tudo em memória, sem gravar nada em disco
    (o Pillow já resolve isso internamente ao ler do BytesIO)."""
    import io

    imagem = Image.open(io.BytesIO(bytes_imagem)).convert("RGB")
    imagem = imagem.resize(TAMANHO_ENTRADA)
    array = np.asarray(imagem, dtype=np.float32) / 255.0
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

    if indice_previsto < len(_CLASSES_PLACEHOLDER):
        classe, recomendacao, severidade = _CLASSES_PLACEHOLDER[indice_previsto]
    else:
        classe, recomendacao, severidade = f"classe_{indice_previsto}", None, None

    return {
        "classe": classe,
        "confianca": confianca,
        "recomendacao": recomendacao,
        "severidade": severidade,
    }
