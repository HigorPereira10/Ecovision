"""
ml/src/dataset/augmentation.py

Data augmentation via Albumentations (Blueprint v3.0, Fase 3), aplicado
sobre o dataset já composto pela estratégia "Frankenstein Cirúrgico"
(ml/src/dataset/frankenstein_compose.py).

Relação com o resto do sistema:
- Consome a saída de frankenstein_compose.py.
- Alimenta diretamente ml/src/training/train.py.
"""

# import albumentations as A

# def construir_pipeline_augmentation() -> "A.Compose":
#     """Define o pipeline de augmentation usado no treino."""
#     raise NotImplementedError
