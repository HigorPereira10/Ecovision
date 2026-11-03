# Grad-CAM do modelo de domínio próprio (4 classes)

Gerado em 2026-11-02 sobre a captura da posição F, com
`ml/src/porta/gradcam_dominio.py`.

## Para que serve

O Grad-CAM mostra QUAIS pixels mais pesaram na decisão. É evidência
contra memorização: se o calor cai sobre o tecido alterado, o modelo
aprendeu o sintoma; se cai no fundo, no vaso ou no fio da bancada, ele
aprendeu um atalho e a acurácia alta não significa nada.

NÃO é prova de acerto. Um modelo pode olhar o lugar certo e classificar
errado.

## O que a figura mostra

`gradcam_posicaoF.png`, quatro janelas por classe.

**Estresse foliar:** nas quatro o calor cai sobre folha amarelada e
tecido secando.

**Saudável:** o calor cai no limbo verde em três das quatro. Em
`x672 y672` ele acende sobre o que parece um botão floral.

## COMO AS JANELAS FORAM ESCOLHIDAS, E POR QUE ISSO IMPORTA

Elas NÃO são as de maior confiança. São as de maior **foco em tecido
texturado**, medido pelo gradiente médio ponderado pelo calor.

A primeira versão desta figura escolhia pelas mais confiantes, e o
resultado foi ruim e revelador:

- cinco das seis janelas eram `saudavel`, porque é nelas que o modelo é
  mais confiante;
- em `x1344 y672` o calor caía sobre o **vaso azul e o fundo**, com a
  classe `saudavel` a 95%;
- em duas de quatro janelas de estresse o ponto mais quente era o
  **fruto**, não a folha.

## O VIÉS DE FRUTO É REAL E NÃO ESTÁ CORRIGIDO

Medido na posição D: em `x448 y224` e `x672 y448`, ambas classificadas
como `estresse_foliar`, o calor mais forte está sobre o tomate verde.

A causa provável é correlação no conjunto: o fruto aparece junto da
folha afetada nas janelas, então virou pista. Resolve com enquadramentos
sem fruto, que é dado, não arquitetura.

**Esta figura seleciona exemplos limpos para ilustrar o método, e essa
seleção está declarada aqui.** Apresentá-la sem esta nota, afirmando
que o modelo olha a folha, não se sustenta: basta pedirem outro
exemplo.

## O que melhorou em relação ao modelo anterior

O modelo treinado com quatro enquadramentos acendia sobre o **fio
vermelho da bancada** numa janela e sobre os frutos em outra, e dava
`saudavel` 90% numa janela quase toda preta. O modelo de seis
enquadramentos não acende em fio nenhum nas doze janelas examinadas.

A guarda de qualidade por janela (`cloud/app/core/janelas.py`) recusa 4
das 36 janelas desta captura. Ela pega o caso extremo (fundo sem folha),
não pega vaso com um pedaço de folha no canto.

## Números do modelo

| | |
|---|---|
| teste no enquadramento F, nunca visto | 94,4% (17/18) |
| baseline trivial do mesmo conjunto | 55,6% |
| saudável | 8/8 |
| estresse foliar | 9/10 |
| falso positivo em janelas saudáveis | 0 de 8 |

Ver ADR 0018 para o caminho completo e `../2026-11-02-limite-do-modelo/`
para onde ele ainda confunde folha seca com fungo.
