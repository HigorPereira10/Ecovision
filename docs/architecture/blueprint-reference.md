# Referência rápida: Tech Stack Blueprint Consolidado v3.0

Este arquivo é um índice de navegação para o documento externo
"EcoVision: Tech Stack Blueprint Consolidado, TC2, v3.0" (mantido na
pasta compartilhada do grupo, ver README raiz). O conteúdo completo NÃO
é duplicado aqui, apenas o mapa de onde encontrar cada decisão.

| Seção do Blueprint | Assunto | Pasta correspondente no repo |
|---|---|---|
| Fase 1: BoM | Lista de compras de hardware, MOSFET, câmera | `docs/decisions/0001-camera-module-3.md` |
| Fase 2: Software de Borda | Captura, sensores, fila offline | `edge/` |
| Fase 3: Pipeline de IA | Frankenstein Cirúrgico, split 70/15/15, metas de F1 | `ml/` |
| Fase 4: Nuvem, Backend e BD | Railway, Supabase, autenticação, regras de código | `cloud/`, `infra/` |
| Fase 4.3 | Autenticação (API Key + JWT/bcrypt) | `docs/decisions/0003-autenticacao-dual.md` |
| Fase 4.6 | Calendário de sincronização Railway × banca | `infra/calendar/sincronizacao.md` |
| Fase 5: Frontend | Framework decidido: Expo (React Native) | `docs/decisions/0002-frontend-framework-pendente.md`, `app/` |
| Plano de Execução | Ordem de fases e sprints | (não replicado, ver documento original) |

## Diagrama de arquitetura

![Diagrama da arquitetura em camadas do EcoVision, com as três camadas físicas de IoT (percepção/borda, rede/nuvem, aplicação) e o detalhamento interno da camada de nuvem em api/routes, core, db e storage](diagramas/arquitetura-em-camadas.png)

Padrão declarado: **Arquitetura em Camadas (Layered)**. A topologia
física segue o modelo de referência de IoT em 3 camadas (percepção/
borda, rede/nuvem, aplicação). Dentro da camada de nuvem (`cloud/`),
`api/routes` é a única camada que conhece as demais: cada rota chama
`core` (regras de negócio puras, sem I/O), `db` e `storage` diretamente
conforme a necessidade, sem passar por uma cadeia fixa. `core` não
depende de `db` nem de `storage`, e nenhuma dessas três camadas conhece
`api/routes` de volta, o que preserva a regra de dependência unidirecional
da Arquitetura em Camadas (checado direto nos imports do código em
2026-09-20, não é só teoria de diagrama).

Padrões como Event-Driven, Space-Based ou CQRS + Event Sourcing (às
vezes recomendados de forma genérica para cenários de IoT) não se
encaixam aqui: o dispositivo não opera em tempo real, captura a cada
intervalo fixo (2h) e manda uma requisição HTTP isolada por vez, sem
volume de eventos concorrentes nem necessidade de replay/auditoria de
eventos que justificasse a complexidade extra desses padrões. Isso foi
conferido contra o material de referência da disciplina:
- [O que é EDA (AWS)](https://aws.amazon.com/pt/what-is/eda/): a própria
  AWS lista como público-alvo da EDA workloads com tráfego variável/em
  picos e processamento sob demanda no lugar de lotes periódicos, o
  oposto do nosso caso (captura em lote a cada 2h).
- [Arquitetura de referência de Data Analytics Serverless (AWS)](https://aws.amazon.com/pt/blogs/aws-brasil/aws-serverless-data-analytics-arquitetura-de-referencia/):
  mesmo a própria AWS descreve seu pipeline de dados de referência como
  "arquitetura em camadas orientada a componentes", não como EDA, mesmo
  tendo gatilhos por evento em uma das camadas.
- [CQRS na AWS com Amazon SQS](https://aws.amazon.com/pt/blogs/aws-brasil/cqrs-na-aws-sincronizando-os-servicos-de-command-e-query-com-o-amazon-sqs/):
  o próprio autor da AWS afirma que separar em dois serviços/bancos "só
  compensa quando precisamos de escalabilidades diferentes ou bancos de
  dados diferentes para atender a comandos e consultas", nenhum dos
  quais é o caso do EcoVision (leitura e escrita de baixo volume, mesmo
  banco).

Fonte editável: `diagramas/arquitetura-em-camadas.svg`.

## Status deste documento

Se o Blueprint for revisado (ex.: v3.1 após decisões de grupo), este
arquivo e os READMEs de cada pasta devem ser atualizados na mesma PR.
