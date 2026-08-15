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

Responsabilidades quando implementado:
- carregar_modelo_tflite(caminho): instancia o interpretador TFLite.
- preprocessar_imagem(bytes_imagem): resize 224x224 + normalização,
  operando inteiramente em memória (BytesIO/NumPy), sem escrita em disco.
- rodar_inferencia(interpretador, imagem_preprocessada): retorna a classe
  prevista e a confiança.

Relação com o resto do sistema:
- Chamado por app/api/routes/diagnostico.py a cada requisição do Pi.
- O modelo consumido aqui é o artefato exportado por ml/src/export/convert_tflite.py.
"""

# import numpy as np
# from PIL import Image

# def carregar_modelo_tflite(caminho_modelo: str):
#     """Carrega o interpretador TFLite uma única vez, no startup da API."""
#     raise NotImplementedError

# def preprocessar_imagem(bytes_imagem: bytes) -> "np.ndarray":
#     """Resize 224x224 + normalização, 100% em memória."""
#     raise NotImplementedError

# def rodar_inferencia(interpretador, imagem_preprocessada) -> dict:
#     """Retorna {'classe': str, 'confianca': float}."""
#     raise NotImplementedError
