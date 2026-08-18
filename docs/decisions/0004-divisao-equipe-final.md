# ADR 0004 — Divisão de equipe final

**Status:** ✅ **Decidido.**

## Contexto

O grupo avaliou três propostas de divisão de trabalho (registradas como
material de apoio em [`docs/planejamento/divisao-equipe-e-roadmap.md`](../planejamento/divisao-equipe-e-roadmap.md),
Seção 2) e fechou a divisão abaixo, incorporando o fato de que Igor não
se sente confortável com trabalho de backend.

## Decisão

| Pessoa | Responsabilidade |
|---|---|
| **João** | `ml/` — pipeline de IA completo (dataset, treino, exportação `.tflite`) |
| **Amanda** | `app/` — frontend/dashboard. Framework confirmado: **Expo (React Native)** (ver [ADR 0002](0002-frontend-framework-pendente.md)) |
| **Higor** | `cloud/` + `infra/` + `edge/` — banco de dados, backend/API, scripts embarcados do Raspberry Pi |
| **Igor** | **Documentação do projeto** (ver detalhamento abaixo) + apoio à Amanda no `app/` nas primeiras semanas |

### Igor — documentação (responsabilidade permanente)

Detalhamento completo das regras e do escopo em
[`docs/planejamento/responsabilidades-documentacao-igor.md`](../planejamento/responsabilidades-documentacao-igor.md).
Resumo: manutenção dos ADRs (`docs/decisions/`), das atas de reunião
(`docs/atas/`), organização da pasta compartilhada do Google Drive e do
Figma, e organização das reuniões do grupo (agendamento, pautas,
registro de decisões).

### Igor — apoio ao `app/` (responsabilidade temporária, primeiras semanas)

Enquanto o `app/` estiver em suas fases iniciais, Igor auxilia a
Amanda no desenvolvimento — mas como ela é a responsável técnica pela
camada, **é ela quem define o que o Igor vai fazer**. Não há uma lista
de tarefas de frontend pré-atribuída ao Igor neste ADR: a divisão exata
(quais telas, quais componentes) deve ser combinada diretamente entre
os dois, no início do trabalho em `app/`.

## Motivo

- Backend (`cloud/`), infraestrutura (`infra/`) e scripts embarcados
  (`edge/`) exigem lógica de servidor, autenticação e integração com
  hardware — Higor topou concentrar essas três camadas.
- Igor não se sente confortável com esse tipo de trabalho. Documentação
  e apoio pontual ao frontend são frentes que existem, têm valor real
  para o projeto (nenhuma tinha dono formal até este ADR) e exigem um
  perfil diferente do de backend.
- O apoio ao `app/` nas primeiras semanas evita que o Igor fique ocioso
  enquanto a frente de documentação ainda não tem volume de trabalho
  constante (ela cresce conforme o projeto se aproxima da banca).

## Consequências

- Este ADR **substitui** as três propostas registradas em
  `docs/planejamento/divisao-equipe-e-roadmap.md` como material de
  decisão — aquele documento permanece no repositório como registro do
  raciocínio, mas a divisão vigente é a desta página.
- A documentação do projeto (ADRs, atas, Drive, Figma) passa a ter dono
  formal (Igor), o que deve reduzir o risco de decisões se perderem
  entre conversas do grupo.
- Cronograma detalhado por pessoa em
  [`docs/planejamento/divisao-equipe-e-roadmap.md`](../planejamento/divisao-equipe-e-roadmap.md)
  deve ser atualizado para refletir esta divisão final (ver nota no
  topo daquele documento).
