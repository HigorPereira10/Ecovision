# EcoVision

> **Sistema de Monitoramento IoT e Visão Computacional para o Controle Fitossanitário em Estufas**

Este é o repositório centralizado do projeto EcoVision, um sistema inteligente focado na detecção precoce de pragas e anomalias em culturas protegidas (estufas de tomate) utilizando Inteligência Artificial e Internet das Coisas (IoT).

**Documento técnico de referência:** [**Blueprint v4.0**](docs/architecture/blueprint-v4.md), que consolida o estado real do sistema implantado e é o documento a ler primeiro. Ele substitui o *Tech Stack - Ecovision (revisado)* v3.0 como referência de consulta; o v3.0 continua válido como registro histórico do que foi planejado, e o índice por seção dele está em [`docs/architecture/blueprint-reference.md`](docs/architecture/blueprint-reference.md). Onde os dois divergem, vale o v4.0, e a divergência está explicada lá.

**Estado atual:** API no ar em `https://ecovision-production.up.railway.app`, aplicativo Android instalável com atualização por EAS Update, modelo de IA de 3 classes em produção, 128 testes automatizados no backend.

> ⚠️ O hardware de borda usado na prática é o **Raspberry Pi 3 Model B+ (Anatel)**, não o Pi Zero 2 W especificado no Blueprint; ver [ADR 0004](docs/decisions/0004-raspberry-pi-3b-plus.md).

---

## 📌 Links Úteis do Projeto
* **Quadro de Tarefas (Kanban):** [GitHub Projects](https://github.com/users/HigorPereira10/projects/1)
* **Comunicação da Equipa:** [Servidor do Discord](https://discord.gg/3R8CkSaxx)
* **Documentação de Texto (TCC):** [Pasta Partilhada no Google Drive](https://drive.google.com/drive/folders/1x9B_vlEw8Yn10jC9kYOUhRTUJoWjrQXT?usp=drive_link)
* **Protótipos de UI (Figma):** *(link a preencher; Igor é responsável por organizar e manter este link atualizado)*

---

## 🏗️ Visão Geral da Arquitetura

O sistema é dividido em cinco camadas, cada uma com um papel isolado,
a mesma separação de responsabilidades que orienta a estrutura de
pastas deste monorepo. Padrão de arquitetura declarado: **Arquitetura
em Camadas (Layered)**, ver o diagrama completo e a justificativa em
[`docs/architecture/blueprint-reference.md`](docs/architecture/blueprint-reference.md#diagrama-de-arquitetura).

```
┌──────────────┐      HTTPS POST /diagnostico       ┌──────────────────┐
│  edge/       │ (imagem + leituras, credencial)    │  cloud/           │
│  Raspberry   │ ──────────────────────────────────▶│  FastAPI          │
│  Pi 3 B+     │                                     │  no Railway       │
│              │                                     │  (TFLite Runtime  │
│  captura,    │                                     │   em memória,     │
│  compressão, │                                     │   sem gravação    │
│  fila        │                                     │   em disco)       │
│  offline     │                                     └─────────┬─────────┘
└──────────────┘                                               │
                                                    grava imagem + dados
                                                                │
                                                                ▼
                                                     ┌────────────────────┐
                                                     │  Supabase          │
                                                     │  Postgres (dados)  │
                                                     │  + Storage         │
                                                     │  (imagens)         │
                                                     └─────────┬──────────┘
                                                                │
                                                    consultado apenas
                                                    através da API
                                                                │
                                                                ▼
                                                     ┌────────────────────┐
                                                     │  app/              │
                                                     │  Dashboard/App     │
                                                     │  (produtor rural)  │
                                                     │  JWT + refresh     │
                                                     └────────────────────┘
```

O modelo de IA usado pela API (`.tflite`) é treinado **offline**, fora
deste fluxo em tempo real, na camada `ml/` (Google Colab), e chega ao
Railway versionado no Git via deploy automático (GitHub Actions), nunca
por upload manual.

Regras que atravessam todas as camadas (ver Blueprint, Seção 4.4):
- **Zero gravação em disco no Railway**: tudo em memória (`BytesIO`) até ser persistido no Supabase.
- **O frontend nunca fala diretamente com o Supabase**: sempre através da API.
- **Duas autenticações diferentes, deliberadamente**: credencial por dispositivo para o IoT ([ADR 0009](docs/decisions/0009-credencial-por-dispositivo.md)); JWT + bcrypt para o login do produtor ([ADR 0010](docs/decisions/0010-cadastro-aberto-e-rbac.md)).
- **Todo dado de consulta é filtrado por dono**: uma conta só vê os dispositivos que ela vinculou, e vincular exige o código de pareamento que vem colado no aparelho.

---

## 📁 Estrutura de Pastas (Monorepo), Índice

O projeto adota uma arquitetura de *monorepo*. Cada pasta tem um README
próprio, com a justificativa técnica detalhada e a referência à seção
correspondente do Blueprint:

* [`app/`](app/README.md): Dashboard/app do produtor rural. Framework: **Expo (React Native), decisão confirmada**: ver [ADR 0002](docs/decisions/0002-frontend-framework-pendente.md).
* [`cloud/`](cloud/README.md): Backend FastAPI no Railway, integração com Supabase (Postgres + Storage), autenticação.
* [`docs/`](docs/README.md): Documentação técnica (ADRs, atas) e escrita acadêmica do TCC.
* [`edge/`](edge/README.md): Software do Raspberry Pi 3 Model B+: captura, sensores, fila offline.
* [`infra/`](infra/README.md): Deploy (Railway), schema/políticas do Supabase, variáveis de ambiente, calendário de sincronização.
* [`ml/`](ml/README.md): Pipeline de treino de IA (Google Colab), dataset "Frankenstein Cirúrgico", exportação `.tflite`.

Decisões arquiteturais relevantes, incluindo as ainda em aberto, estão
registradas como ADRs em [`docs/decisions/`](docs/decisions/README.md).

---

## 🛠️ Metodologia de Trabalho & Gestão

O desenvolvimento é guiado por um framework ágil baseado num Scrum Simplificado, estruturado em sprints de 2 semanas.

### GitHub Projects
Toda a distribuição de atividades é centralizada no **GitHub Projects** através de um quadro Kanban composto por três esteiras principais:
1. **Todo (A Fazer):** Lista de tarefas priorizadas para a sprint atual.
2. **In Progress (Em Progresso):** Atividades ativas sendo desenvolvidas por um membro da equipa.
3. **Done (Concluído):** Tarefas finalizadas e validadas.

Cada atividade é mapeada como uma *Issue* e deve obrigatoriamente conter um responsável (*Assignee*) e uma etiqueta (*Label*) correspondente ao seu componente (`edge`, `cloud`, `app`, `ml` ou `docs`).

---

## 🌿 Fluxo de Desenvolvimento (Branch Policy)

Para garantir a estabilidade do sistema e evitar conflitos no código principal, adotamos uma política rigorosa de branches ("Acordo de Cavalheiros"):

1. **A branch `main` é sagrada:** É estritamente proibido realizar commits diretos na branch `main`. **Exceção acordada:** o líder do grupo (Higor) pode publicar direto na `main`, porque o gate de CI cumpre a função de barreira automática (ver [ADR 0014](docs/decisions/0014-deploy-railway-e-gate-de-ci.md)): código com teste quebrado não chega a produção, com ou sem revisor.
2. **Criação de Branches:** Toda e qualquer tarefa iniciada a partir do quadro Kanban deve possuir uma branch isolada utilizando o padrão de nomenclatura do componente (ex: `feature/edge-camera-capture`, `feature/cloud-fastapi-inference`).
3. **Pull Requests & Code Review:** Ao concluir uma funcionalidade, o desenvolvedor deve abrir um *Pull Request* direcionado à `main`. O merge só será realizado após a revisão e aprovação de, pelo menos, **1 outro integrante da equipa**.

---

## 👥 Equipe

| Pessoa | Responsabilidade |
|---|---|
| João | `ml/`: pipeline de IA completo |
| Amanda | `app/`: frontend/dashboard (Expo/React Native, decisão confirmada) |
| Higor | `cloud/` + `infra/` + `edge/`: banco de dados, backend/API, scripts do Raspberry Pi |
| Igor | Documentação do projeto (ADRs, atas, organização do Drive e do Figma, pautas/decisões de reunião); nas primeiras semanas, também apoia a Amanda no `app/`, alinhando diretamente com ela |

Detalhes e cronograma passo a passo em
[`docs/planejamento/divisao-equipe-e-roadmap.md`](docs/planejamento/divisao-equipe-e-roadmap.md).

## ✅ Decisões que estavam em aberto e foram fechadas

- ~~**Signed URL × bucket público**~~: decidido por **signed URL**, bucket privado, URL gerada sob demanda por `GET /diagnosticos`. Ver [`infra/supabase/storage_policies.md`](infra/supabase/storage_policies.md).
- ~~**API Key única e global do dispositivo**~~: substituída por **credencial por dispositivo** com pareamento por código, ver [ADR 0009](docs/decisions/0009-credencial-por-dispositivo.md).
- ~~**Hospedagem**~~: Railway no plano Hobby, com gate de CI, ver [ADR 0014](docs/decisions/0014-deploy-railway-e-gate-de-ci.md).
- ~~**Quantas classes o modelo reconhece**~~: três, com o limite declarado dentro do app, ver [ADR 0011](docs/decisions/0011-escopo-de-tres-classes.md).

## ⚠️ Riscos e pendências que seguem abertos

- **O IoT está na estufa com os fios sendo ajustados**, e a captura
  automática está desativada. Enquanto isso, as telas de diagnóstico
  aparecem vazias, que é o comportamento correto.
- **Limiar de umidade do solo** é convenção prática, não fonte
  agronômica, e precisa de recalibração com o sensor físico ([ADR 0005](docs/decisions/0005-limiares-ambientais.md)).
- **Gap entre o F1 do dataset e o desempenho em foto de campo** ainda
  não medido nem documentado ([ADR 0011](docs/decisions/0011-escopo-de-tres-classes.md)).
- **Notificação só funciona com o app aberto**, por decisão registrada ([ADR 0012](docs/decisions/0012-notificacao-local-sem-push.md)).
- **Calendário de sincronização** entre coleta de campo e data da banca: [`infra/calendar/sincronizacao.md`](infra/calendar/sincronizacao.md), ainda com datas "A DEFINIR".
- **Lista de compras final** (cotação em conjunto, atenção à compatibilidade elétrica): ver [`docs/planejamento/lista-compras-hardware.md`](docs/planejamento/lista-compras-hardware.md).
