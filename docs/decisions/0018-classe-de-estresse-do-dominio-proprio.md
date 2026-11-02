# ADR 0018: Classe de estresse rotulada no domínio próprio

**Status:** Decidido (2026-11-02).

## Contexto

Em 2026-11-01 o sistema afirmou `pinta_preta` com 77,8% de confiança
sobre uma planta com amarelecimento internerval generalizado. A planta
não tem pinta preta.

A literatura agronômica de extensão registra essa confusão como regra,
não exceção: deficiência nutricional e doença fúngica produzem os
mesmos amarelecimento e necrose, e o discriminador clássico de campo é
que o dano biótico tende a ser assimétrico e o abiótico simétrico
([ECHO], [Univ. Delaware]). O modelo não tem como aplicar isso: ele tem
três saídas e um softmax, e distribui toda entrada entre elas.

**Três abordagens foram medidas e falharam antes da que foi adotada.**
Elas estão documentadas aqui para ninguém repetir.

## O que foi tentado e não funcionou

### 1. Trocar softmax por sigmoides independentes

Hipótese: o softmax normaliza, então uma entrada desconhecida pode sair
com 78% só porque as três saídas eram baixas e uma era menos baixa.
Sigmoides independentes devolveriam três valores baixos, que é a
resposta honesta.

Medido sobre os logits, antes de qualquer retreino:

| | logit máximo (mediana) |
|---|---|
| Classes conhecidas (PlantDoc teste) | 1,89 |
| Nossa planta (janelas aprovadas pela porta) | 1,70 |

100% das janelas da nossa planta ficaram acima do percentil 5 das
conhecidas. **O modelo está genuinamente confiante**, não inflado por
normalização. Ele não erra sobre o que *vê*, que é tecido foliar
danificado; erra ao *nomear*, porque os únicos nomes que tem são nomes
de doença. Problema de nome não se corrige na camada de saída.

### 2. Porta de familiaridade (rejeição post-hoc)

A porta (`ml/src/porta/avaliar.py`) recusa 100% das janelas de fundo,
mas não recusa folha estranha. Um benchmark de 2026 de métodos de
rejeição OOD em patologia vegetal ([arXiv 2605.08618]) mede por quê:

| método | AUROC em OOD *próximo* |
|---|---|
| softmax | 0,482 (abaixo do acaso) |
| energia post-hoc | 0,516 |
| sigmoides independentes | 0,751 a 0,844 |
| energia com ajuste fino | 0,938 |

Métodos post-hoc desabam quando o OOD é próximo, e folha de tomate com
deficiência é o OOD mais próximo que existe. A porta continua útil para
o que ela faz bem, que é fundo.

### 3. Quarta classe vinda do OLID I

O [OLID I] (Zenodo 8105154, CC BY 4.0, painel de especialistas) tem 123
imagens de tomate com deficiência de N, K e N+K. Duas rodadas de treino:

| | acerto no OLID | janelas vencidas na nossa planta |
|---|---|---|
| rodada 1 | 37,5% | 0 de 36 |
| rodada 2 (validação balanceada + recorte) | 83,3% | 1 de 36 |

A classe aprendeu dentro do próprio domínio e **não atravessou** para
uma janela de planta na estufa. A rodada 2 ainda disparou o atalho de
origem: 28% das folhas SAUDÁVEIS do OLID passaram a ser chamadas de
deficiência, contra 0 de 300 do PlantVillage e 0 de 27 do PlantDoc.

Uma geometria de lesão (focal contra difuso) também foi medida e
descartada: separa entre fontes (AUC 0,849) e não dentro da mesma fonte
(0,627), e a medida muda com a distância da câmera (22,7 a 20 cm contra
29,9 a 34 cm, mesma planta).

## Decisão

**Rotular o estresse no domínio próprio, com classe descritiva única.**

1. As capturas do dispositivo são recortadas em janelas de 896 px
   (`ml/src/dataset/extrair_janelas.py`), filtradas pela porta de
   familiaridade e pela cobertura de verde, e rotuladas à mão.
2. A classe se chama **`estresse_foliar`**, não "deficiência
   nutricional". Afirmar etiologia a partir de foto exige saber a
   adubação, e o OLID só pôde fazê-lo porque foi ensaio controlado.
   Descritivo é o que se sustenta sem laudo agronômico.
3. `amarelecimento_difuso` e `tecido_seco` foram tentadas separadas e
   **fundidas**, por medição: a fração de tecido seco nas janelas
   chamadas de amarelecimento deu 7,6% contra 7,7% nas chamadas de
   tecido seco. São a mesma coisa pela medida, e a fronteira derivou
   entre sessões de rotulagem. O rótulo fino continua gravado na coluna
   `classe_fina` de `rotulos.csv`, então a separação volta a ser
   possível se um dia houver dado que a sustente.

## Por que isso funciona quando o OLID não funcionou

Primeira rodada com dado próprio, 47 janelas:

| | 3 classes | 5 classes (domínio próprio) |
|---|---|---|
| janelas chamadas de doença fúngica | 34 de 36 | 6 de 36 |
| classes novas vencendo | — | 21 de 36 |
| PlantVillage teste | 95,3% | 97,7% |

O OLID deu zero janelas. O domínio próprio deu 21. A diferença não é
algoritmo, é a distância entre o dado de treino e esta estufa.

## O que isto NÃO resolve

- **É uma planta, num vaso, sob uma luz.** O teste num enquadramento
  reservado mostra que o modelo não decorou o fundo. Não mostra que
  funciona em outra planta.
- **Assimetria de fonte:** `septoriose` e `pinta_preta` vêm só de
  PlantDoc e PlantVillage; `estresse_foliar` vem só da estufa.
  `saudavel` vem das duas, o que atenua. Não tem solução enquanto a
  planta não tiver doença fúngica para fotografar.
- **A rotulagem é do próprio grupo.** A pré-anotação assistida foi
  revisada janela a janela, com 77% de concordância entre a proposta e
  a decisão do revisor em 165 janelas. O número está registrado porque
  é ele que qualifica o conjunto, não a sua existência.

## Regras de rotulagem, e por que cada uma existe

| regra | origem |
|---|---|
| Verde de caule não conta como folha sã | erro de rotulagem em 2026-11-01 |
| Objeto artificial em foco ou atravessando o quadro descarta | estaca e fios viravam sintoma |
| Vence a condição que cobre mais área de limbo | a regra "mais severa vence" inchava `tecido_seco` |
| Desfoque sozinho não descarta, se o sintoma for nítido | janelas úteis estavam sendo perdidas |

## Armadilhas de divisão que custaram retrabalho

**A chave de posição precisa incluir o ENQUADRAMENTO.** Ela era só
`xNNNN_yNNNN`, e com isso duas janelas de enquadramentos diferentes
recebiam a mesma chave. Pior: a contagem de posições distintas ficava
travada em 36 por mais que o vaso mudasse de lugar, fazendo parecer que
mover não adiantava, quando é o que mais adianta.

**A divisão é por enquadramento, nunca aleatória nem por data.**
Capturas de 2 em 2 horas da mesma planta são quase duplicatas: medido,
2,4 imagens por posição e 20% de divergência de rótulo entre capturas
da mesma posição. E em 17 horas o sintoma não progrediu (amarelo de
42,9% para 42,7%), então o que varia entre capturas é luz, não doença.

**O conjunto de teste se escolhe pelo EQUILÍBRIO, antes de treinar.**
A sessão B foi escolhida primeiro com o argumento de ser a mais
desbalanceada, "o teste mais duro". Está errado: com 13 saudáveis e 2
estresses, um chutador que respondesse sempre "saudavel" acertaria
86,7%, e o modelo treinado fez 80%, **pior que o trivial**. Teste duro é
teste equilibrado, não teste torto. A escolha final (C+E, 34 janelas,
baseline 58,8%) foi feita pela contagem de classes, com o critério
declarado antes do treino.

## Critério objetivo de "dado suficiente"

Com 13 posições distintas, a `val_accuracy` ficou travada em 28,6% nas
25 épocas, com a de treino em 97,8%: memorização pura. Com 4
enquadramentos, subiu para 86% e a perda de validação caiu de 0,80 para
0,36.

**O conjunto deixa de ser pequeno demais quando a `val_accuracy` sai do
travamento e sobe junto com a de treino.** Enquanto não sair, o caminho
é mais enquadramento, não mais ajuste de hiperparâmetro.

## Referências

- [ECHO]: https://www.echocommunity.org/en/resources/b5cad3ac-e9e6-42bb-be50-ce43689b87ed
- [Univ. Delaware]: https://www.udel.edu/academics/colleges/canr/cooperative-extension/fact-sheets/identifying-nutrient-deficiencies-in-ornamental-plants/
- [OLID I]: https://zenodo.org/record/8105154
- [arXiv 2605.08618]: https://arxiv.org/html/2605.08618
- Ver também ADR 0011 (escopo de três classes) e ADR 0016 (guarda de
  qualidade de imagem).
