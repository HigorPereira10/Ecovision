# ml/notebooks

Notebooks Google Colab ainda não criados. Este README documenta os
notebooks planejados, refletindo o pipeline descrito no Tech Stack
Blueprint v3.0 (Fase 3) e no Plano de Execução (Fase 2, "Dataset e
modelo").

Notebooks planejados (a criar):

1. **`01_preparacao_dataset.ipynb`**
   Download do PlantVillage + Mendeley, aplicação seletiva de `rembg`
   nas 6 classes de baixo risco, composição "Frankenstein" (folhas
   recortadas sobre fundos reais de estufa), fusão com o Mendeley,
   Albumentations. Resultado salvo no Google Drive para reuso (o
   `rembg` leva 4-8h e não deve ser reexecutado a cada treino).

2. **`02_treino_modelo.ipynb`**
   Treino de MobileNetV2 (transfer learning) com `class_weight` para
   compensar o desbalanceamento de classes, split 70/15/15.

3. **`03_avaliacao.ipynb`**
   Matriz de confusão, F1 por classe, F1 weighted (métrica global
   recomendada, ver `ml/README.md`, seção de risco estatístico).
   Comparação do F1 sintético (teste) vs. F1 real (imagens de campo do
   Pi, nunca usadas no treino).

4. **`04_exportacao_tflite.ipynb`**
   Conversão do modelo Keras para `.tflite`, validação de tamanho/latência,
   e versionamento do artefato final em `ml/models/`.

A implementação equivalente em script (para quem preferir rodar fora do
notebook, ou para reuso de funções) vive em `ml/src/`.
