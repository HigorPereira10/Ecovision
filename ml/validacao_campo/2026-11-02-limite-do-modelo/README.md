# Onde o modelo de 4 classes ainda confunde seca com fungo

Medido em 2026-11-02, rodando o modelo sobre as 86 janelas rotuladas
como `estresse_foliar`. Destas, **3** ele chama de `pinta_preta`, e são
as três aqui.

| janela | pinta_preta (4 classes) | pinta_preta (3 classes) |
|---|---|---|
| `D__posD__x1344_y0000` | 89% | 100% |
| `D__posD__x1120_y0000` | 69% | 100% |
| `D__posD__x1568_y0000` | 66% | 100% |

## O que elas são

Folhas **secas e enroladas**, marrons por inteiro, com a borda ainda
amarelada. Tecido morto por ressecamento.

Pinta preta é mancha escura com anéis concêntricos DENTRO de folha
verde, com halo amarelo ao redor e a folha viva em volta. Aqui não há
folha viva em volta: a folha inteira morreu.

## Por que isto está guardado

É o limite conhecido do modelo de domínio próprio, e ele é honesto:
nas 86 janelas de estresse a probabilidade mediana de fungo é 6%, e só
estas 3 passam do limiar. O modelo de 3 classes chamaria praticamente
todas de doença.

A comparação mais útil está nas janelas que o modelo novo acerta e o
antigo erra feio:

| janela | 3 classes | 4 classes |
|---|---|---|
| `D__posD__x0896_y0448` | pinta_preta 97% | estresse_foliar |
| `F__posF__x0672_y0448` | pinta_preta 99% | estresse_foliar |
| `E__posE__x1120_y0672` | pinta_preta 98% | estresse_foliar |

São folhas amareladas com a borda secando. O modelo antigo chama
qualquer tecido escurecido de doença fúngica.

Ver ADR 0018 para o contexto completo.
