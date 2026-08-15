"""
ml/src/training/evaluate.py

Avaliação do modelo treinado (Blueprint v3.0, Fase 3): matriz de
confusão, F1 por classe e F1 weighted (métrica global recomendada para
lidar com a variância alta das classes minoritárias no teste pequeno,
ver ml/README.md).

Responsabilidades quando implementado:
- Calcular F1 no conjunto sintético de teste (meta mínima ≥ 75%, ideal ≥ 82%).
- Calcular F1 nas imagens reais coletadas em campo com o hardware do
  EcoVision (meta mínima ≥ 65%, ideal ≥ 72%), essas imagens NUNCA
  participam do treino.
- Documentar o delta entre F1 sintético e F1 real (meta: < 10 p.p.).

Relação com o resto do sistema:
- Consome o modelo treinado em ml/src/training/train.py.
- O conjunto de imagens reais vem da coleta de campo (ver
  docs/decisions/ e Fase 6 do Plano de Execução do Blueprint).
"""

# def avaliar_conjunto_sintetico(modelo, dataset_teste) -> dict:
#     """Retorna F1 por classe e F1 weighted no conjunto sintético."""
#     raise NotImplementedError

# def avaliar_imagens_reais(modelo, imagens_campo) -> dict:
#     """Retorna F1 weighted nas imagens reais coletadas com o hardware do Pi."""
#     raise NotImplementedError

# def calcular_gap(f1_sintetico: float, f1_real: float) -> float:
#     """Calcula e documenta o delta entre F1 sintético e F1 real."""
#     raise NotImplementedError
