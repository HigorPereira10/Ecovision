# docs/tcc

Espelho local dos capítulos da escrita acadêmica do TCC. O documento
"oficial" fica na pasta compartilhada do Google Drive do grupo (link no
README raiz). Esta pasta serve para versionar rascunhos técnicos que
citam diretamente arquivos deste repositório (trechos de código,
resultados de avaliação do modelo).

**Antes de escrever qualquer seção técnica, leia
[`docs/architecture/blueprint-v4.md`](../architecture/blueprint-v4.md).**
Ele descreve o sistema como ele é hoje, e a seção 10.3 dele já traz as
três perguntas difíceis da banca com as respostas.

## Comece por aqui

| Arquivo | Para que serve |
|---|---|
| [`material-pronto-para-o-tcc.docx`](material-pronto-para-o-tcc.docx) | **Material pronto para inserir no TCC**: figuras, quadros, textos e referências, com a indicação de onde cada um entra. É o ponto de partida de quem está escrevendo |
| [`resultados-medidos.md`](resultados-medidos.md) | Todas as métricas em tabela, com o método de medição de cada uma |
| [`figuras/`](figuras/) | As 9 figuras em PNG de 300 dpi e SVG, com o índice dizendo em que capítulo cada uma entra |
| [`zenodo-deposito.md`](zenodo-deposito.md) | Metadados e passo a passo do depósito do conjunto de dados, exigido pelo Manual do Conjunto Prototipado |

O `.docx` é o documento de passagem para quem escreve; os outros dois
são a fonte dos números e das imagens que ele manda usar.

## O que precisa virar texto de TCC

### Pontos de argumentação (valem nota)

- **Estratégia "Frankenstein Cirúrgico"** (`ml/README.md`) como
  argumento de originalidade acadêmica: fusão seletiva de PlantVillage
  com o dataset Mendeley.
- **Risco estatístico do split 70/15/15** e o uso de `class_weight` e F1
  ponderado, explicado **proativamente**, antes de a banca perguntar.
- **Por que o recorte de três classes é uma decisão e não uma limitação**
  ([ADR 0011](../decisions/0011-escopo-de-tres-classes.md)): três
  classes validadas por agrônomo valem mais que dez chutando, e o
  limite está declarado dentro do aplicativo.
- **Por que uma premissa de arquitetura foi revista por evidência**
  ([ADR 0003](../decisions/0003-autenticacao-dual.md) superado pelo
  [0009](../decisions/0009-credencial-por-dispositivo.md)): a decisão
  original não estava errada, a premissa dela mudou. Isso é
  engenharia, e o rastro está versionado.
- **Degradação em vez de queda** como princípio de projeto (seção 4.3 do
  Blueprint v4.0), incluindo o preço que ele cobrou uma vez: a API subiu
  sem modelo, em silêncio.
- **Por que não é Event-Driven nem CQRS**
  ([`blueprint-reference.md`](../architecture/blueprint-reference.md#diagrama-de-arquitetura)),
  com as fontes da AWS conferidas.

### Resultados já medidos, prontos para o texto

Todos em [ADR 0011](../decisions/0011-escopo-de-tres-classes.md) e
`ml/models/README.md`.

- **Desempenho nos dois domínios**, por validação cruzada de 5 dobras
  sobre 3577 imagens, com comparação pareada: 95,3% em laboratório e
  74,0% em foto de campo, contra 90,7% e 57,0% do modelo anterior.
  Venceu em 10 de 10 comparações.
- **Matriz de confusão e F1 por classe** nos dois domínios.
- **O delta entre domínios**: 21,3 pontos, com a referência da
  literatura que mostra quedas muito piores
  (HO-LAM; NGUYEN, 2026 reportam MobileNetV2 caindo de 99,77% para 28,57%
  no PlantDoc, **sem ajuste de domínio**, então a comparação é indicativa,
  não direta).
- **Uma tentativa que não funcionou**, e por quê: ajustar só com foto de
  campo trocava um domínio pelo outro. Vale mais na escrita que um
  resultado limpo, porque mostra método.
- **Uma lição de amostragem**: numa amostra de 6 imagens a conclusão
  sobre interpolação foi errada, e só com 277 ficou clara.

### O que ainda falta medir

- **Desempenho em foto tirada pelo Raspberry Pi**, na estufa. Nenhum
  conjunto usado até aqui é isso: PlantVillage é folha arrancada em
  fundo uniforme, PlantDoc é foto de web, e a captura real fica entre os
  dois. Depende da coleta de campo.
- **Falso positivo em campo com amostra suficiente.** Hoje são 2 erros
  em 8 imagens, com intervalo de confiança de 7,1% a 59,1%. A meta de
  15% está dentro do intervalo, então o resultado é indeterminado, não
  reprovado. A coleta de 48 horas com planta sadia é exatamente a
  amostra que falta.
- **Tempo de carregamento das telas** com volume real de dados. A tela
  de Histórico gera uma URL assinada por imagem, e essa é a única
  latência que o produtor sente de fato.

### Medições concluídas em 2026-10-25

Todas em [`resultados-medidos.md`](resultados-medidos.md), com figura
correspondente em [`figuras/`](figuras/).

- Latência: 33,7 ms de inferência no p95 e 1,58 s ponta a ponta no
  Railway, contra meta de 500 ms e timeout de 30 s do dispositivo.
- Falso positivo e falso negativo, por domínio, com intervalo de
  confiança de Wilson.
- Matrizes de confusão nos dois domínios, sobre os testes retidos.
- **Grad-CAM regerado para o modelo atual.** Os mapas antigos continuam
  em `ml/validacao_externa/gradcam/` e `gradcam_depois/` como
  comparação histórica, mas a evidência válida hoje é a figura 06.
- Teste de memorização por quase-duplicata: a acurácia de laboratório
  fica em 94,2% mesmo removendo as 26 imagens mais parecidas com o
  treino.

### Correções de contradição entre o TC1 e o que foi construído

Todas as quatro já têm decisão registrada. Falta levar para o texto:

| Contradição no TC1 | O que vale | Onde |
|---|---|---|
| Câmera V2 | Camera Module 3 | [ADR 0001](../decisions/0001-camera-module-3.md) |
| 11 classes | 10 no catálogo agronômico, **3 no modelo em produção** | [ADR 0006](../decisions/0006-recomendacoes-por-diagnostico.md), [ADR 0011](../decisions/0011-escopo-de-tres-classes.md) |
| Métricas de desempenho do TC1 | Medidas de novo em 2026-10-24, com validação cruzada | [ADR 0011](../decisions/0011-escopo-de-tres-classes.md) |
| Hospedagem em AWS ECS / Cloud Run | Railway, plano Hobby | [ADR 0014](../decisions/0014-deploy-railway-e-gate-de-ci.md) |
| Autenticação por API Key única | Credencial por dispositivo + JWT com RBAC por posse | [ADR 0009](../decisions/0009-credencial-por-dispositivo.md), [ADR 0010](../decisions/0010-cadastro-aberto-e-rbac.md) |
| Pi Zero 2 W | Raspberry Pi 3 Model B+ | [ADR 0004](../decisions/0004-raspberry-pi-3b-plus.md) |

### Limitações a declarar (melhor declarar que ser pego)

- Notificação só funciona com o aplicativo aberto
  ([ADR 0012](../decisions/0012-notificacao-local-sem-push.md)).
- Não existe build de iOS: a demonstração é Android mais Expo Go.
- O limiar de umidade do solo é convenção prática, não fonte
  agronômica, e precisa de recalibração com o sensor físico
  ([ADR 0005](../decisions/0005-limiares-ambientais.md)).
- A tela Financeira guarda dados apenas no aparelho, por decisão de
  escopo: controle de gastos nunca fez parte do monitoramento
  fitossanitário.
- O modelo nunca viu as sete doenças restantes do catálogo, então uma
  folha com requeima será classificada dentro das três classes que ele
  conhece. É por isso que o escopo aparece escrito na tela.

### Trabalhos futuros (seção que já tem conteúdo pronto)

- Push de servidor, com os quatro requisitos listados no
  [ADR 0012](../decisions/0012-notificacao-local-sem-push.md).
- Reativação das classes restantes, com o procedimento de três passos do
  [ADR 0011](../decisions/0011-escopo-de-tres-classes.md).
- Remoção do ramo de transição da chave global de dispositivo
  ([ADR 0009](../decisions/0009-credencial-por-dispositivo.md)).
- Calibração do sensor de umidade do solo e revisão dos limiares.
