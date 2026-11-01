# ml: Pipeline de IA (Treino Offline)

Referência arquitetural: [**Blueprint v4.0**](../docs/architecture/blueprint-v4.md),
seção 5. O Blueprint v3.0, Fase 3, segue valendo para o planejamento do
pipeline.

> **ESTADO EM PRODUÇÃO (2026-10-24):** `ml/models/modelo.tflite`,
> MobileNetV2 com **ajuste fino de dois domínios**, float32, 8,5 MB,
> **3 classes** na ordem `septoriose`, `pinta_preta`, `saudavel`.
> Medido por validação cruzada de 5 dobras em 3577 imagens: **95,3% em
> laboratório e 74,0% em foto de campo**, contra 90,7% e 57,0% do
> baseline anterior, vencendo em 10 de 10 comparações pareadas. Gerado
> por `src/training/ajuste_dois_dominios.py`, ver `models/README.md`. O recorte de três classes é uma decisão
> registrada, com o motivo e o procedimento para reativar as outras, em
> [ADR 0011](../docs/decisions/0011-escopo-de-tres-classes.md). O
> aplicativo declara esse limite ao produtor na tela de Diagnóstico, em
> vez de dar a entender que reconhece qualquer doença de tomate.

## Papel desta camada

Treino **100% offline**, rodado no Google Colab (GPU T4). Nada desta
camada roda em produção: o artefato final é um único arquivo `.tflite`
versionado no repositório e consumido pelo backend (`cloud/app/core/inference.py`).

Estratégia de dataset: **"Frankenstein Cirúrgico"** (validada nesta
revisão como abordagem recomendada):
- Fusão seletiva de **PlantVillage** (~14k imagens sintéticas, `rembg`
  aplicado apenas nas 6 classes de baixo risco de corrosão de segmentação)
  com o **Mendeley Tomato Disease Dataset** (~4k imagens em ambiente real).
- Mais robusta que um dataset único e é um argumento de originalidade
  acadêmica defensável na banca.

## Metas de desempenho (dupla métrica, Blueprint Seção 3)

| Métrica | Meta mínima | Meta ideal | Medido |
|---|---|---|---|
| Weighted F1, validação sintética (laboratório) | >= 75% | >= 82% | **95,3%** |
| Weighted F1, imagens reais do Pi (estufa) | >= 65% | >= 72% | **ainda não existe** |
| Delta sintético contra real | documentar | < 10 p.p. | **ver abaixo** |

**Atenção ao ler a tabela acima.** A segunda linha fala de fotos tiradas
pelo hardware do EcoVision, na estufa, e essas fotos ainda não existem.
O que foi medido é um terceiro conjunto, o **PlantDoc** (foto de campo de
outro grupo): **74,0%**. Ele é um intermediário pessimista, porque é foto
de web com enquadramento aleatório, enquanto a captura do Pi é de perto e
com iluminação controlada.

O delta entre laboratório e PlantDoc é de **21,3 pontos**, acima dos 10
desejados. Isso é esperado e tem respaldo na literatura: a queda entre
datasets é severa nesse problema, e um MobileNetV2 treinado em
PlantVillage cai de 99,77% para 28,57% no PlantDoc, sem ajuste de domínio,
([TinyCNN, arXiv 2609.20290](https://arxiv.org/pdf/2609.20290)). O
ajuste de dois domínios reduziu esse delta de 33,7 para 21,3 pontos.

**As imagens reais coletadas com o hardware do EcoVision NUNCA entram no
treino**: são exclusivamente o conjunto de validação do mundo real.

## Como o modelo em produção é gerado

`src/training/ajuste_dois_dominios.py`, a partir de
`training/baseline_pinta_preta.keras`, treinando com imagem de
laboratório e de campo ao mesmo tempo. O cabeçalho do arquivo registra as
três decisões que fazem o ajuste funcionar (descongelamento parcial, taxa
de aprendizado baixa, peso por classe e por domínio) e o que acontece
quando cada uma falta.

A tentativa anterior, que ajustou só com foto de campo, está documentada
no [ADR 0011](../docs/decisions/0011-escopo-de-tres-classes.md): ela
ganhava 19 pontos em campo e perdia 12 em laboratório, ou seja, trocava
um domínio pelo outro em vez de melhorar.

## Risco estatístico do split 70/15/15 (Blueprint Seção 3)

Com esse split, a classe minoritária do PlantVillage (Mosaic Virus, ~299
imagens originais) fica com ~45 imagens no teste, e o F1 dessa classe tem
variância alta. Mitigação planejada: `class_weight`
(`sklearn.utils.class_weight.compute_class_weight`) no treino, e uso do
F1 ponderado (weighted) global como métrica mais estável para o sistema
como um todo. Essa justificativa deve ser preparada **proativamente**
para a banca (ver `docs/decisions/`).

## Estrutura

```
ml/
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

- O pipeline de `rembg` leva 4-8h para ~7k imagens: executar **uma vez**,
  salvar o resultado no Google Drive e reutilizar; não gerar on-the-fly
  a cada treino.
- Contagem de classes **do dataset**: 10, não 11 (ponto de correção do
  TC1). Atenção para não confundir dois números diferentes: o catálogo
  agronômico tem 10 classes, com recomendação e fonte para cada uma
  ([ADR 0006](../docs/decisions/0006-recomendacoes-por-diagnostico.md)),
  e o **modelo em produção reconhece 3**
  ([ADR 0011](../docs/decisions/0011-escopo-de-tres-classes.md)). As
  outras 7 estão no catálogo esperando dado de treino.

## Se o modelo for retreinado, leia isto antes

Três lugares têm que concordar, e o segundo falha **em silêncio**:

1. Exportar com `ml/src/export/convert_tflite.py` (sem quantização, ver
   a justificativa medida no topo do arquivo).
2. `_CLASSES_DO_MODELO` em `cloud/app/core/inference.py`, na **ordem
   exata** das saídas do modelo. A ordem vem do treino, onde
   `image_dataset_from_directory` ordena os diretórios alfabeticamente.
   Trocar o `.tflite` sem atualizar essa lista faz cada predição sair
   com o nome e a recomendação de **outra doença**, sem erro nenhum.
3. `ativa: true` na classe correspondente em
   `app/src/domain/doencas.ts`.

E duas armadilhas de contrato do modelo, as duas medidas:

- O modelo **normaliza por dentro** (a camada `preprocess_input` faz
  parte do grafo exportado), então quem chama passa **pixels crus de 0 a
  255**. Dividir por 255 antes faz tudo colapsar para "saudavel" com
  cerca de 90% de confiança.
- O redimensionamento tem que ser **NEAREST**. Com NEAREST, 6 de 6
  predições batem com o Keras original; com BILINEAR ou BICUBIC, 0 de 6,
  e duas classes mudam.
