# ADR 0017: Metas de desempenho revistas por domínio

**Status:** Decidido (2026-10-25).

## Contexto

O TC1 fixou oito metas numéricas antes de qualquer medição. Em
2026-10-25 todas foram medidas pela primeira vez, e o resultado expôs
um problema que não era visível no papel: **a meta única de acurácia
ignora que o sistema opera sobre dois domínios de imagem com
dificuldades muito diferentes.**

| Domínio | O que é | Medido |
|---|---|---|
| Laboratório | folha arrancada, fundo uniforme, luz de estúdio | 94,3% |
| Campo | planta na lavoura, fundo heterogêneo, luz variável | 74,1% |

Lida como está, a meta de 85% aprova o laboratório e reprova o campo.
Mas a captura real do Pi fica **entre** os dois domínios, então nenhum
dos dois números sozinho descreve o sistema. A meta não estava errada,
estava mal definida: ela não dizia sobre qual domínio incidia.

Duas outras metas perderam o referente por decisões já registradas:
o "dashboard" virou aplicativo móvel, e o Pi Zero 2 W foi preterido
ainda no projeto ([ADR 0004](0004-raspberry-pi-3b-plus.md)).

## Decisão

Reescrever as metas, declarando a revisão no texto do TCC em vez de
silenciá-la.

| Meta do TC1 | Medido | Decisão |
|---|---|---|
| Acurácia >= 85% | 94,3% lab / 74,1% campo | **Substituída** por 90% em laboratório e 70% em campo |
| F1 >= 0,80 | 0,943 / 0,744 | **Substituída** por 0,90 em laboratório e 0,65 em campo |
| Falso negativo < 10% | 2,5% / 5,3% | **Mantida.** Cumprida nos dois domínios |
| Falso positivo <= 15% | 0,0% / indeterminado | **Mantida**, com o resultado de campo declarado pendente |
| Inferência <= 500 ms | 33,7 ms no p95 | **Mantida.** Cumprida com folga de 466 ms |
| Dashboard < 5 s | não se aplica | **Removida.** Não existe dashboard |
| Uptime do Pi Zero 2 W >= 95% | nunca medida | **Removida.** Hardware preterido |
| Fila offline, retenção de 100% | coberta por teste | **Mantida.** Cumprida |

### Por que 90% e 70%, e não outros números

Não são arredondamentos convenientes do que medimos. São o patamar
abaixo do qual o sistema deixaria de ser útil, escolhidos antes de olhar
para a margem:

- **90% em laboratório** porque o baseline anterior já entregava 90,7%.
  Fixar abaixo disso aceitaria regressão.
- **70% em campo** porque o acaso com três classes é 33,3%, e a
  referência de literatura mais próxima (HO-LAM; NGUYEN, 2026,
  [arXiv:2609.20290](https://arxiv.org/abs/2609.20290)) reporta MobileNetV2
  caindo de 99,77% para **28,57%** no PlantDoc, medido **sem ajuste de
  domínio**, o que torna a comparação indicativa e não direta. Um sistema que
  acerta 7 de 10 em foto de campo é utilizável; abaixo disso o produtor
  passaria a desconfiar de tudo.

### Por que o falso positivo de campo fica "pendente" e não "reprovado"

São 2 erros em 8 imagens. O intervalo de confiança de Wilson a 95% vai
de **7,1% a 59,1%**, e a meta de 15% está dentro dele. Os dados não
sustentam nem aprovação nem reprovação.

Declarar 25% seria tão incorreto quanto declarar que passou. A posição
honesta é dizer que a amostra é insuficiente e apontar o que resolve:
a coleta de campo com planta sadia, que produz dezenas de capturas
exatamente dessa natureza.

## Consequências

**O capítulo de resultados fica defensável.** Escrito contra as metas
antigas, ele documentaria o próprio fracasso em dois critérios que, lidos
corretamente, foram cumpridos.

**O trabalho ganha um argumento de método.** Revisar meta a partir de
medição, declarando a revisão, é o oposto de ajustar a régua depois da
prova. A diferença está em dizer que foi feito e por quê.

**Fica uma dívida explícita:** a meta de campo só poderá ser verificada
com amostra maior. Isso está declarado no texto em vez de escondido.

## Alternativas descartadas

| Alternativa | Por que não |
|---|---|
| Manter as metas e reprovar em dois critérios | Puniria o trabalho por uma meta mal formulada, não por desempenho ruim |
| Reescrever as metas como se sempre tivessem sido assim | A banca compara com o TC1. Seria pego, e aí o problema deixa de ser técnico |
| Reportar só o laboratório | Seria o número bonito sobre o domínio em que o sistema não opera |
| Reportar uma média dos dois domínios | Esconde a limitação central do modelo num número que não descreve situação nenhuma |

## Implementação

- [`docs/tcc/resultados-medidos.md`](../tcc/resultados-medidos.md),
  seções 3, 6 e 9: os números medidos e os intervalos de confiança.
- [`docs/tcc/material-pronto-para-o-tcc.docx`](../tcc/material-pronto-para-o-tcc.docx),
  Parte 7: a tabela de revisão e o parágrafo de justificativa pronto
  para o TCC.
- [`docs/tcc/figuras/`](../tcc/figuras/): figuras 01 a 06.
