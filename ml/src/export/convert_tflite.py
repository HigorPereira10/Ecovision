"""
ml/src/export/convert_tflite.py

Exportação do modelo treinado (Keras) para o formato `.tflite`
(Blueprint v3.0, Fase 3), o único artefato de IA que efetivamente vai
para produção.

Regras obrigatórias (Blueprint Seção 4.4):
- O `.tflite` resultante deve ser salvo em ml/models/ e versionado no
  repositório GitHub, nunca enviado manualmente para o Railway.
- O deploy do modelo até o backend acontece via GitHub Actions (ver
  infra/ e .github/workflows/), não por upload manual.

POR QUE SEM QUANTIZAÇÃO: a conversão com tf.lite.Optimize.DEFAULT
derruba o arquivo de 8,90 MB para 2,53 MB, o que é tentador. Medido
no conjunto de validação externa (ml/validacao_externa/), porém, a
versão quantizada INVERTEU 2 de 7 predições, com diferença de até 29
pontos percentuais de confiança. A float32 divergiu no máximo 0,0004
ponto percentual do modelo Keras original. Economizar 6 MB não paga
mudar diagnóstico, ainda mais com a RAM sobrando (o interpretador
inteiro ocupa cerca de 14 MB).

ATENÇÃO, ARMADILHA DE INTEGRAÇÃO: este modelo NORMALIZA POR DENTRO
(a camada de preprocess_input da MobileNetV2 faz parte do grafo
exportado). Ou seja, quem chama precisa passar pixels CRUS de 0 a 255.
Aplicar preprocess_input por fora antes de enviar faz todas as
predições colapsarem para "saudavel" com cerca de 90% de confiança,
sem erro nenhum, o que é muito difícil de perceber. Ver
cloud/app/core/inference.py, que respeita isso.

Como rodar (precisa de TensorFlow, que NÃO entra em cloud/requirements.txt
por causa do limite de RAM do Railway; usar um venv separado):

    python ml/src/export/convert_tflite.py

Relação com o resto do sistema:
- Consome o modelo treinado em ml/src/training/train.py.
- O artefato gerado é consumido por cloud/app/core/inference.py.
"""

import os

import tensorflow as tf

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELO_KERAS = os.path.join(RAIZ, "training", "baseline_pinta_preta.keras")
SAIDA = os.path.join(RAIZ, "models", "modelo.tflite")

# Ordem das classes na saída do modelo. Vem de
# tf.keras.utils.image_dataset_from_directory, que ordena os diretórios
# ALFABETICAMENTE. Esta lista precisa bater exatamente com a de
# cloud/app/core/inference.py: se divergir, cada predição sai com o
# rótulo (e a recomendação agronômica) de outra doença, sem erro visível.
CLASSES = ["distrator_septoria", "pinta_preta", "saudavel", "estresse_foliar"]


def converter_para_tflite(caminho_keras: str, caminho_saida: str) -> None:
    """Converte o modelo Keras treinado para .tflite e salva em ml/models/."""
    modelo = tf.keras.models.load_model(caminho_keras)

    saidas = modelo.output_shape[-1]
    if saidas != len(CLASSES):
        raise SystemExit(
            f"O modelo tem {saidas} saidas, mas CLASSES lista {len(CLASSES)} nomes. "
            "Atualize CLASSES aqui e a lista em cloud/app/core/inference.py."
        )

    conversor = tf.lite.TFLiteConverter.from_keras_model(modelo)
    # Sem conversor.optimizations: ver a nota sobre quantizacao no topo.
    conteudo = conversor.convert()

    os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)
    with open(caminho_saida, "wb") as arquivo:
        arquivo.write(conteudo)

    print(f"Entrada esperada : {modelo.input_shape} (pixels crus 0-255)")
    print(f"Classes, em ordem: {CLASSES}")
    print(f"Gravado em       : {caminho_saida}  ({len(conteudo) / 1e6:.2f} MB)")


if __name__ == "__main__":
    converter_para_tflite(MODELO_KERAS, SAIDA)
