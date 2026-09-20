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
borda, rede/nuvem, aplicação), e a camada de nuvem (`cloud/`) por si só
já segue o padrão de camadas internamente: `api/routes` nunca acessa o
banco direto, sempre chama `core`; `core` nunca fala com o Supabase
direto, sempre passa por `db`/`storage`. Cada camada só conhece a
camada logo abaixo dela.

Padrões como Event-Driven, Space-Based ou CQRS + Event Sourcing (às
vezes recomendados de forma genérica para cenários de IoT) não se
encaixam aqui: o dispositivo não opera em tempo real, captura a cada
intervalo fixo (2h) e manda uma requisição HTTP isolada por vez, sem
volume de eventos concorrentes nem necessidade de replay/auditoria de
eventos que justificasse a complexidade extra desses padrões.

Fonte editável: `diagramas/arquitetura-em-camadas.svg`.

## Status deste documento

Se o Blueprint for revisado (ex.: v3.1 após decisões de grupo), este
arquivo e os READMEs de cada pasta devem ser atualizados na mesma PR.
