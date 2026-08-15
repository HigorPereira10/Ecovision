"""
ml/src/dataset/download.py

Download programático dos datasets fonte (Blueprint v3.0, Fase 3):
- PlantVillage (~14k imagens sintéticas, via Kaggle Datasets)
- Mendeley Tomato Disease Dataset (~4k imagens em ambiente real)

Responsabilidades quando implementado:
- Autenticar com a API do Kaggle.
- Baixar e extrair os dois datasets para um diretório local (Colab:
  tipicamente montado no Google Drive para persistir entre sessões).

Relação com o resto do sistema:
- Primeira etapa do pipeline; alimenta
  ml/src/dataset/frankenstein_compose.py.
"""

# def baixar_plantvillage(destino: str) -> None:
#     """Baixa o dataset PlantVillage via Kaggle Datasets."""
#     raise NotImplementedError

# def baixar_mendeley(destino: str) -> None:
#     """Baixa o Mendeley Tomato Disease Dataset."""
#     raise NotImplementedError
