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

### Resultados que faltam medir

- **Gap entre o F1 do dataset sintético e o desempenho em foto de
  campo.** É a dupla métrica que `ml/README.md` exige e ainda não foi
  medida. Depende do João.
- **Matriz de confusão e F1 por classe** do modelo de 3 classes.
- Grad-CAM antes e depois já existe em `ml/validacao_externa/gradcam/` e
  `gradcam_depois/`: vale ir para o texto como evidência de que o modelo
  olha a lesão, e não o fundo da imagem.

### Correções de contradição entre o TC1 e o que foi construído

Todas as quatro já têm decisão registrada. Falta levar para o texto:

| Contradição no TC1 | O que vale | Onde |
|---|---|---|
| Câmera V2 | Camera Module 3 | [ADR 0001](../decisions/0001-camera-module-3.md) |
| 11 classes | 10 no catálogo agronômico, **3 no modelo em produção** | [ADR 0006](../decisions/0006-recomendacoes-por-diagnostico.md), [ADR 0011](../decisions/0011-escopo-de-tres-classes.md) |
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
