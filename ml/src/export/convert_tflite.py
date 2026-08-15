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

Relação com o resto do sistema:
- Consome o modelo treinado em ml/src/training/train.py, já validado
  por ml/src/training/evaluate.py.
- O artefato gerado é consumido por cloud/app/core/inference.py.
"""

# import tensorflow as tf

# def converter_para_tflite(modelo_keras, caminho_saida: str) -> None:
#     """Converte o modelo Keras treinado para .tflite e salva em ml/models/."""
#     raise NotImplementedError
