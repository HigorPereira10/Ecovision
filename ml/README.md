# ml

Treinamento, avaliação e exportação do classificador de folhas de
tomateiro. Nada desta pasta roda em produção: o resultado é um arquivo
`.tflite` em `models/`, carregado pela API (`cloud/app/core/inference.py`).

## Modelo em produção

`models/modelo_dominio.tflite`: MobileNetV2 com transferência de
aprendizado, em ponto flutuante de 32 bits, com quatro saídas, na ordem
`septoriose`, `pinta_preta`, `saudavel` e `estresse_foliar`
(`_CLASSES_DO_MODELO` em `cloud/app/core/inference.py`).

O modelo foi construído em três etapas:

| Etapa | Script ou notebook | Resultado |
|---|---|---|
| 1. Modelo base, só com imagens de laboratório (PlantVillage) | `training/baseline_hibrida.ipynb` | `training/baseline_pinta_preta.keras` |
| 2. Ajuste simultâneo com laboratório e campo (PlantDoc), três classes | `src/training/ajuste_dois_dominios.py` | `training/modelo_hibrido_lab_campo.keras` e `models/modelo.tflite` |
| 3. Quarta classe, estresse foliar, com janelas rotuladas no próprio dispositivo | `src/training/ajuste_dominio_proprio.py` | `training/modelo_dominio_proprio.keras` e `models/modelo_dominio.tflite` |

Configuração de treino (Google Colab, GPU T4):

- **Etapa 1:** base congelada, dropout de 0,2, Adam com taxa de 0,001,
  lotes de 32, parada antecipada com paciência de 5 épocas; aumento de
  dados por espelhamento, rotação de até 72 graus e ampliação de até 20%.
- **Etapas 2 e 3:** 30 últimas camadas da base descongeladas, exceto as de
  normalização em lote, taxa de 0,00001, lotes de 16, pesos por classe e
  por domínio (cerca de 12 imagens de laboratório para cada imagem de
  campo).

## Dados

| Conjunto | Uso | Onde está |
|---|---|---|
| PlantVillage, 1.100 imagens por classe | Laboratório: 1.000 de treino e 100 de teste por classe | `data_prep/02_split_doenca.ipynb` monta a divisão |
| PlantDoc, 276 imagens de tomateiro | Campo: 249 de treino e 27 de teste | `data/plantdoc_tomate_divisao.csv` |
| Janelas do próprio dispositivo, 193 rotuladas (135 úteis) | Classe de estresse foliar | `data/estufa_rotulada/rotulos.csv` e `manifesto.csv` |

As imagens não ficam no repositório. As capturas do dispositivo, as
janelas rotuladas e a divisão do PlantDoc estão publicadas no Zenodo
([10.5281/zenodo.23646357](https://doi.org/10.5281/zenodo.23646357)).

As janelas são extraídas das capturas por
`src/dataset/extrair_janelas.py`, que descarta recortes com pouca
cobertura verde ou pouca semelhança com as imagens de treino
(`src/porta/`, com a referência em `models/referencia_familiaridade.npz`).
A divisão entre treino e teste é feita por enquadramento, e não por
janela, porque janelas da mesma captura se sobrepõem.

## Resultados

| Avaliação | Acurácia |
|---|---|
| Três classes, laboratório (300 imagens de teste) | 94,3% (IC 95%: 91,1% a 96,4%) |
| Três classes, campo (27 imagens de teste) | 74,1% (IC 95%: 55,3% a 86,8%) |
| Validação cruzada de 5 dobras, laboratório: modelo base → ajuste em dois domínios | 90,7% → 95,3% |
| Validação cruzada de 5 dobras, campo: modelo base → ajuste em dois domínios | 57,0% → 74,0% |
| Modelo em produção, enquadramento retido do próprio dispositivo (18 janelas) | 94,4%, contra 55,6% da baseline trivial |

A avaliação do modelo em produção é reproduzida por
`src/training/avaliar_dominio_proprio.py`, sobre o enquadramento F, que não
participou do treino. Os mapas de ativação são gerados por
`src/porta/gradcam_dominio.py`.

## Contrato do modelo com a API

Três pontos precisam ser respeitados ao trocar o modelo, e os erros não
geram exceção, apenas predições erradas:

1. **Ordem das classes:** `_CLASSES_DO_MODELO` em
   `cloud/app/core/inference.py` deve seguir a ordem das saídas do modelo:
   as três classes da etapa 2 e, por último, a acrescentada na etapa 3. Trocar o
   `.tflite` sem atualizar a lista atribui a cada predição o nome e a
   recomendação de outra classe. A API recusa carregar um modelo cujo
   número de saídas difira da lista.
2. **Pixels de 0 a 255:** a normalização faz parte do modelo exportado.
   Dividir os pixels por 255 antes da inferência leva quase tudo para
   `saudavel`.
3. **Redimensionamento pelo vizinho mais próximo:** com ele, as predições
   coincidem com as do modelo Keras original; com interpolação bilinear ou
   bicúbica, não.

A exportação não usa quantização. Ao reativar uma classe no aplicativo,
ajuste também `app/src/domain/doencas.ts`.

## Dependências

O treino roda no Google Colab, que já traz TensorFlow, NumPy, Pillow e
Matplotlib. Para executar os scripts localmente, instale
`ml/requirements.txt`.
