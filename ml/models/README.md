# ml/models

Diretório de destino do artefato final do treino: o modelo `.tflite`
versionado no repositório (Blueprint v3.0, Seção 4.4, regra 1).

- Este é o **único** artefato de IA consumido em produção, é lido por
  `cloud/app/core/inference.py` no startup da API.
- Deve chegar ao Railway via deploy automático (GitHub Actions), nunca
  por upload manual em volume stateful (ver `infra/`).
- `modelo.tflite` (8,9 MB, float32, 3 classes) gerado em 2026-10-10 por
  `ml/src/export/convert_tflite.py` a partir de
  `ml/training/baseline_pinta_preta.keras`.
- **Ordem das classes:** `septoriose`, `pinta_preta`, `saudavel`. Essa
  ordem tem que bater com `_CLASSES_DO_MODELO` em
  `cloud/app/core/inference.py`. Trocar o `.tflite` por um retreino com
  outra quantidade ou ordem de classes sem atualizar aquela lista faz
  cada predição sair com o nome e a recomendação de outra doença, sem
  nenhum erro visível.
- Sem quantização, de propósito: a versão quantizada ocupa 2,5 MB mas
  inverteu 2 de 7 predições nos testes. Ver a justificativa medida no
  topo de `ml/src/export/convert_tflite.py`.
