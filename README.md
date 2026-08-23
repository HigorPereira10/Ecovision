# EcoVision

> **Sistema de Monitoramento IoT e Visão Computacional para o Controle Fitossanitário em Estufas**

Este é o repositório centralizado do projeto EcoVision, um sistema inteligente focado na detecção precoce de pragas e anomalias em culturas protegidas (estufas de tomate) utilizando Inteligência Artificial e Internet das Coisas (IoT).

**Documento técnico de referência:** *Tech Stack - Ecovision (revisado)* (mantido na pasta compartilhada do grupo). Todas as decisões de arquitetura, hardware e software descritas neste repositório seguem esse documento; ele tem prioridade sobre qualquer divergência no TC1. Um índice de navegação rápida por seção está em [`docs/architecture/blueprint-reference.md`](docs/architecture/blueprint-reference.md).

> ⚠️ O hardware de borda usado na prática é o **Raspberry Pi 3 Model B+ (Anatel)**, não o Pi Zero 2 W especificado no Blueprint — ver [ADR 0004](docs/decisions/0004-raspberry-pi-3b-plus.md).

---

## 📌 Links Úteis do Projeto
* **Quadro de Tarefas (Kanban):** [GitHub Projects](https://github.com/users/HigorPereira10/projects/1)
* **Comunicação da Equipa:** [Servidor do Discord](https://discord.gg/3R8CkSaxx)
* **Documentação de Texto (TCC):** [Pasta Partilhada no Google Drive](https://drive.google.com/drive/folders/1x9B_vlEw8Yn10jC9kYOUhRTUJoWjrQXT?usp=drive_link)

---

## 🏗️ Visão Geral da Arquitetura

O sistema é dividido em cinco camadas, cada uma com um papel isolado,
a mesma separação de responsabilidades que orienta a estrutura de
pastas deste monorepo.

```
┌──────────────┐      HTTPS POST /diagnostico       ┌──────────────────┐
│  edge/       │  (imagem + leituras, API Key)      │  cloud/           │
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
- **Duas autenticações diferentes, deliberadamente**: API Key estática para o dispositivo IoT; JWT + bcrypt para o login do produtor.

---

## 📁 Estrutura de Pastas (Monorepo), Índice

O projeto adota uma arquitetura de *monorepo*. Cada pasta tem um README
próprio, com a justificativa técnica detalhada e a referência à seção
correspondente do Blueprint:

* [`app/`](app/README.md): Dashboard/app do produtor rural. ⚠️ Framework (Expo × PWA × Streamlit) ainda **pendente de decisão do grupo**: ver [ADR 0002](docs/decisions/0002-frontend-framework-pendente.md).
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

1. **A branch `main` é sagrada:** É estritamente proibido realizar commits diretos na branch `main`.
2. **Criação de Branches:** Toda e qualquer tarefa iniciada a partir do quadro Kanban deve possuir uma branch isolada utilizando o padrão de nomenclatura do componente (ex: `feature/edge-camera-capture`, `feature/cloud-fastapi-inference`).
3. **Pull Requests & Code Review:** Ao concluir uma funcionalidade, o desenvolvedor deve abrir um *Pull Request* direcionado à `main`. O merge só será realizado após a revisão e aprovação de, pelo menos, **1 outro integrante da equipa**.

---

## ⚠️ Decisões e riscos em aberto (checar antes da Sprint 1)

- **Framework de frontend** (Expo × PWA × Streamlit): [ADR 0002](docs/decisions/0002-frontend-framework-pendente.md).
- **Signed URL × bucket público** para a leitura das imagens no dashboard: [`infra/supabase/storage_policies.md`](infra/supabase/storage_policies.md), bloqueada até o `app/` existir de verdade.
- **API Key única e global do dispositivo** (`cloud/app/core/security.py`): aceitável com 1 Raspberry Pi físico ([ADR 0003](docs/decisions/0003-autenticacao-dual.md)), precisa virar uma chave por dispositivo antes de qualquer implantação com mais de um Pi.
- **Calendário de sincronização** entre a ativação do trial do Railway, a coleta de campo (Sprint 9) e a data da banca: [`infra/calendar/sincronizacao.md`](infra/calendar/sincronizacao.md), ainda com datas "A DEFINIR".
- **Lista de compras final** (cotação em conjunto, atenção à compatibilidade elétrica): ver Fase 1 do Blueprint.
