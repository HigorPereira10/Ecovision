# ml/models

Diretório de destino do artefato final do treino: o modelo `.tflite`
versionado no repositório.

- Este é o **único** artefato de IA consumido em produção, lido por
  `cloud/app/core/inference.py` no startup da API.
- Chega ao Railway pelo deploy automático, nunca por upload manual em
  volume stateful.

## `modelo.tflite` (em produção desde 2026-10-24)

| | |
|---|---|
| Arquitetura | MobileNetV2, ajuste fino de dois domínios |
| Tamanho | 8,47 MB, float32 |
| Classes | 3, nesta ordem: `septoriose`, `pinta_preta`, `saudavel` |
| Gerado por | `ml/src/training/ajuste_dois_dominios.py` |
| A partir de | `ml/training/baseline_pinta_preta.keras` |
| Fonte Keras | `ml/training/modelo_hibrido_lab_campo.keras` |

### Desempenho medido

Validação cruzada de 5 dobras sobre 3577 imagens (3300 de laboratório,
277 de campo), cada imagem testada exatamente uma vez por um modelo que
nunca a viu. Comparação **pareada** contra o baseline anterior, nas
mesmas imagens de cada dobra.

| Domínio | Baseline anterior | **Em produção** | Ganho |
|---|---|---|---|
| Laboratório (PlantVillage) | 90,7% ± 0,2 | **95,3% ± 0,8** | +4,5 p.p. |
| Campo (PlantDoc) | 57,0% ± 4,7 | **74,0% ± 2,3** | +17,0 p.p. |

Venceu nas 5 dobras dos dois domínios: 10 comparações pareadas, 10
vitórias. Em campo também ficou mais estável, com metade do desvio.

Nas 6 imagens de `ml/validacao_externa/`, que não entraram em treino
nenhum: **6 de 6**, contra 4 de 6 do baseline.

### Avaliação direta do artefato, sobre os testes retidos

A validação cruzada mede o **método**. Esta mede o **arquivo que está no
ar**, sobre as partições `test/` que o ajuste nunca viu (2026-10-25):

| Domínio | Imagens | Acurácia | F1 ponderado | Falso negativo |
|---|---|---|---|---|
| Laboratório | 300 | 94,3% | 0,943 | 2,5% |
| Campo | 27 | 74,1% | 0,744 | 5,3% |

Os dois métodos concordam (95,3% e 74,0% por validação cruzada, contra
94,3% e 74,1% aqui), o que reforça os dois.

**Teste de memorização.** Para cada imagem de teste foi medida a
distância de Hamming do dHash até a imagem de treino mais parecida, e a
acurácia recalculada sem as mais próximas. Removendo as 26 imagens de
laboratório a 10 bits ou menos, 8,7% da partição, o resultado foi de
94,3% para **94,2%**. A acurácia não depende do que daria para decorar.

Tabelas completas, intervalos de confiança e os gráficos estão em
[`docs/tcc/resultados-medidos.md`](../../docs/tcc/resultados-medidos.md)
e [`docs/tcc/figuras/`](../../docs/tcc/figuras/).

A medição completa, incluindo a tentativa anterior que trocava
desempenho de um domínio pelo outro, está em
[ADR 0011](../../docs/decisions/0011-escopo-de-tres-classes.md).

### Quatro regras que continuam valendo

**Ordem das classes:** `septoriose`, `pinta_preta`, `saudavel`. Tem que
bater com `_CLASSES_DO_MODELO` em `cloud/app/core/inference.py`. Trocar o
`.tflite` por um retreino com outra quantidade ou ordem sem atualizar
aquela lista faz cada predição sair com o nome e a recomendação de outra
doença, **sem nenhum erro visível**.

**Pixels crus de 0 a 255.** O modelo normaliza por dentro (a camada
`preprocess_input` faz parte do grafo). Dividir por 255 antes faz tudo
colapsar para "saudavel" com cerca de 90% de confiança.

**Sem quantização.** A versão quantizada ocupa 2,5 MB em vez de 8,5 MB,
mas no baseline inverteu 2 de 7 predições, com diferença de até 29 pontos
de confiança. Economizar 6 MB não paga mudar diagnóstico.

**O `preprocess_input` está no grafo, mas NÃO aparece em
`model.layers`.** Isso só morde quem trabalha com o `.keras` e
reimplementa o caminho de inferência a mão, como o Grad-CAM exige: no
Keras 3 aquele passo vira operação do grafo funcional sem virar camada
nomeada, então percorrer `model.layers` em sequência pula a
normalização sem erro nenhum.

O sintoma é idêntico ao de dividir por 255: tudo sai como `saudavel`
com cerca de 90% de confiança. Medido em 2026-10-25, com
`septoria_01.jpg`:

| Caminho | Resultado |
|---|---|
| `modelo(cru)`, o modelo inteiro | septoriose 0,977 |
| camadas percorridas a mão, sem `preprocess_input` | **saudavel 0,909** |
| camadas a mão, com `preprocess_input` aplicado | septoriose 0,977 |

Quem chama o modelo inteiro (`modelo(x)` ou `predict`) continua
passando pixels crus e não precisa fazer nada. Quem desmonta o modelo
precisa aplicar
`keras.applications.mobilenet_v2.preprocess_input` entre o aumento de
dados e a base.

### O que este modelo NÃO resolve

O viés do escuro continua: foto subexposta sai como "saudavel" com
confiança alta, porque o modelo tem três saídas e nenhuma delas é "isto
não é uma folha". **A guarda de qualidade de imagem
(`avaliar_qualidade_imagem` em `cloud/app/core/inference.py`) segue
obrigatória.**

E nenhum dos conjuntos de teste é foto tirada pelo Raspberry Pi. O
PlantVillage é folha arrancada em fundo uniforme, o PlantDoc é foto de
campo achada na web, e a captura real fica entre os dois. Os números
acima comparam modelos de forma justa, mas o desempenho em produção só
será conhecido depois da coleta na estufa.

## Histórico

- **`modelo.tflite` anterior** (2026-10-10 a 2026-10-24): MobileNetV2
  treinado apenas com imagem de laboratório. 90,7% em laboratório e
  57,0% em campo. Continua recuperável pelo histórico do git, e o
  `.keras` dele (`baseline_pinta_preta.keras`) segue versionado porque é
  o ponto de partida do ajuste atual.
