# ml — Pipeline de IA (Treino Offline)

Referência arquitetural: **Tech Stack Blueprint Consolidado v3.0, Fase 3 (Pipeline de IA)**.

> Nota: no início desta reestruturação, a pasta `ml/` continha apenas um
> `.gitkeep` — nenhum conteúdo pré-existente foi encontrado ou alterado
> além do que está descrito aqui.

## Papel desta camada

Treino **100% offline**, rodado no Google Colab (GPU T4). Nada desta
camada roda em produção — o artefato final é um único arquivo `.tflite`
versionado no repositório e consumido pelo backend (`cloud/app/core/inference.py`).

Estratégia de dataset — **"Frankenstein Cirúrgico"** (validada nesta
revisão como abordagem recomendada):
- Fusão seletiva de **PlantVillage** (~14k imagens sintéticas, `rembg`
  aplicado apenas nas 6 classes de baixo risco de corrosão de segmentação)
  com o **Mendeley Tomato Disease Dataset** (~4k imagens em ambiente real).
- Mais robusta que um dataset único e é um argumento de originalidade
  acadêmica defensável na banca.

## Metas de desempenho (dupla métrica — Blueprint Seção 3)

| Métrica | Meta mínima (banca) | Meta ideal |
|---|---|---|
| Weighted F1 — validação sintética | ≥ 75% | ≥ 82% |
| Weighted F1 — imagens reais do Pi (campo) | ≥ 65% | ≥ 72% |
| Delta sintético vs. real | Documentar e explicar | < 10 p.p. |

**As imagens reais coletadas com o hardware do EcoVision NUNCA entram no
treino** — são exclusivamente o conjunto de validação do mundo real.

## Risco estatístico do split 70/15/15 (Blueprint Seção 3)

Com esse split, a classe minoritária do PlantVillage (Mosaic Virus, ~299
imagens originais) fica com ~45 imagens no teste — F1 dessa classe tem
variância alta. Mitigação planejada: `class_weight`
(`sklearn.utils.class_weight.compute_class_weight`) no treino, e uso do
F1 ponderado (weighted) global como métrica mais estável para o sistema
como um todo. Essa justificativa deve ser preparada **proativamente**
para a banca (ver `docs/decisions/`).

## Estrutura

```
ml/
├── notebooks/            # notebooks Colab (ver notebooks/README.md para a lista planejada)
├── src/
│   ├── dataset/
│   │   ├── download.py              # download PlantVillage + Mendeley (Kaggle)
│   │   ├── frankenstein_compose.py  # rembg seletivo (6 classes) + composição
│   │   └── augmentation.py          # Albumentations
│   ├── training/
│   │   ├── train.py                 # MobileNetV2 (transfer learning) + class_weight
│   │   └── evaluate.py              # matriz de confusão, F1 por classe, F1 weighted
│   └── export/
│       └── convert_tflite.py        # exportação do modelo final .tflite
├── models/                # artefato .tflite versionado (destino final)
└── requirements.txt
```

## Pontos de atenção herdados do Blueprint

- O pipeline de `rembg` leva 4-8h para ~7k imagens — executar **uma vez**,
  salvar o resultado no Google Drive e reutilizar; não gerar on-the-fly
  a cada treino.
- Contagem de classes do dataset: **10**, não 11 (ponto de correção do TC1
  citado no Plano de Execução, Fase 0).
