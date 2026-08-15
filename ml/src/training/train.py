"""
ml/src/training/train.py

Treino de MobileNetV2 via transfer learning (Blueprint v3.0, Fase 3),
sobre o dataset "Frankenstein Cirúrgico".

Responsabilidades quando implementado:
- Split 70/15/15 (treino/validação/teste).
- Calcular `class_weight` (sklearn.utils.class_weight.compute_class_weight)
  para compensar o desbalanceamento, em especial da classe minoritária
  Mosaic Virus (~299 imagens originais), que fica com ~45 no teste
  (ver ml/README.md, risco estatístico do split).
- Fine-tuning de MobileNetV2 pré-treinada (ImageNet) para as classes do
  EcoVision.

Relação com o resto do sistema:
- Consome a saída de ml/src/dataset/augmentation.py.
- O modelo treinado aqui é avaliado em ml/src/training/evaluate.py e
  exportado em ml/src/export/convert_tflite.py.
"""

# from sklearn.utils.class_weight import compute_class_weight

# def treinar_modelo(dataset_treino, dataset_validacao, class_weight: dict):
#     """Treina MobileNetV2 (transfer learning) e retorna o modelo treinado."""
#     raise NotImplementedError
