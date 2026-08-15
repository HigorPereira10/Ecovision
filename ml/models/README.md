# ml/models

Diretório de destino do artefato final do treino: o modelo `.tflite`
versionado no repositório (Blueprint v3.0, Seção 4.4, regra 1).

- Este é o **único** artefato de IA consumido em produção, é lido por
  `cloud/app/core/inference.py` no startup da API.
- Deve chegar ao Railway via deploy automático (GitHub Actions), nunca
  por upload manual em volume stateful (ver `infra/`).
- Ainda vazio: será populado após `ml/src/export/convert_tflite.py`
  gerar o primeiro modelo treinado e validado (metas de F1 em `ml/README.md`).
