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

## Status deste documento

Se o Blueprint for revisado (ex.: v3.1 após decisões de grupo), este
arquivo e os READMEs de cada pasta devem ser atualizados na mesma PR.
