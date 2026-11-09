# ml/models

Artefatos exportados para a API.

| Arquivo | Conteúdo |
|---|---|
| `modelo_dominio.tflite` | **Modelo em produção.** MobileNetV2, quatro classes (`septoriose`, `pinta_preta`, `saudavel`, `estresse_foliar`), float32, 8,5 MB. Gerado por `ml/src/training/ajuste_dominio_proprio.py` |
| `modelo.tflite` | Modelo anterior, de três classes (`septoriose`, `pinta_preta`, `saudavel`), ajustado em laboratório e campo. Gerado por `ml/src/training/ajuste_dois_dominios.py`; é a base dos resultados nas bases públicas |
| `referencia_familiaridade.npz` | Vetores de referência usados na extração de janelas para rotulagem (`ml/src/porta/`) |

A API carrega o modelo indicado em `TFLITE_MODEL_PATH`, por padrão
`ml/models/modelo_dominio.tflite`. Os modelos são versionados no
repositório e chegam ao Railway pela implantação; nenhum arquivo é
enviado manualmente ao servidor.

Os modelos Keras de origem, usados para gerar novas versões e os mapas de
ativação, ficam em `ml/training/`.
