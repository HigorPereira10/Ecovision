# "Saudável 93%" sobre um pote vazio

Falha real em produção, 2026-11-03. A planta foi retirada da estufa
para tomar sol e a câmera continuou capturando, enquadrando um pote
plástico verde-azulado, fios e plástico branco.

| captura | diagnóstico | janelas aproveitadas |
|---|---|---|
| `diag167` 11:00 | imagem_inadequada | 0 de 36 |
| `diag168` 13:00 | imagem_inadequada | 0 de 36 |
| `diag169` 15:00 | **saudavel 93%** | 5 de 36 |

As três mostram a MESMA cena. A diferença das 15:00 foi a luz mais
forte: o plástico rendeu 9% a 12% de cobertura "verde", acima do
limiar de 8% que vigorava, e cinco janelas passaram.

## Por que isto é grave

Afirmar que uma planta está saudável é a afirmação mais perigosa que
este sistema pode fazer, e aqui ele a fez sobre uma cena **sem planta
nenhuma**. A guarda de qualidade de imagem (ADR 0016) existe
exatamente para impedir isso, e o caminho por janela herdou o mesmo
objetivo.

## A causa, medida

O teste de "é folha?" era cobertura de verde acima de 8%. Esse número
foi escolhido antes de existir conjunto rotulado. Com as 135 janelas
rotuladas à mão:

| | percentil 5 da cobertura verde |
|---|---|
| janelas de folha saudável | 20,5% |
| janelas de folha com estresse | 25,7% |
| plástico do pote que passou | 9% a 12% |

O limiar estava três vezes abaixo do necessário.

## Correção

Duas mudanças em `cloud/app/core/janelas.py`:

1. `COBERTURA_VERDE_MINIMA` de 0,08 para **0,18**, abaixo de toda
   janela de folha real e bem acima do plástico.
2. `JANELAS_MINIMAS = 6`. A captura das 15:00 diagnosticou com cinco
   janelas de 36: mesmo que fossem folha, 14% do quadro é base fraca, e
   com cinco janelas um voto único vira 20% e cruza sozinho o limiar da
   regra de incidência.

Verificado nos dois sentidos: as três capturas do pote passaram a dar
zero janelas aproveitáveis, e as capturas com planta continuam
aproveitando 28 a 30 de 36.

Três testes de regressão em `cloud/tests/test_janelas.py`, na seção 7.

## Como a falha apareceu

Não foi teste planejado. A planta saiu para o sol e o cron continuou
rodando. Nenhum conjunto de validação montado em mesa teria produzido
este caso, porque ninguém fotografa um pote vazio de propósito.
