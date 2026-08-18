# Planejamento de Execução e Divisão de Equipe

**Status:** a divisão de equipe está **decidida** — ver
[ADR 0004](../decisions/0004-divisao-equipe-final.md). Este documento
traz o cronograma passo a passo de cada pessoa a partir dessa decisão
(Seção 3), as decisões que ainda seguem pendentes (Seção 1), a
explicação Supabase × Railway (Seção 5), e mantém, como apêndice
histórico ao final, o raciocínio das propostas avaliadas antes da
decisão ser fechada.

Fonte técnica de todas as afirmações abaixo: **Tech Stack Blueprint
Consolidado v3.0** (ver [`docs/architecture/blueprint-reference.md`](../architecture/blueprint-reference.md)
para o índice de seções) e a estrutura de pastas já criada no repositório
(`app/`, `cloud/`, `docs/`, `edge/`, `infra/`, `ml/`, cada uma com seu
próprio README).

> **Nota de revisão:** as versões anteriores deste documento propunham
> Igor como dono de `edge/`, em dupla no backend, ou em variações de
> banco de dados/documentação. O grupo fechou a decisão final: Igor fica
> com a **documentação do projeto** (ver
> [`responsabilidades-documentacao-igor.md`](responsabilidades-documentacao-igor.md)
> para o detalhamento) e, nas primeiras semanas, apoia a Amanda no
> `app/` em tarefas que os dois combinarem diretamente.

---

## 1. Decisões pendentes do projeto, por urgência

### 1.1 — Bloqueiam o início da codificação (resolver na Fase 0, antes da Sprint 1)

| Decisão | Por quê é bloqueante | Onde está documentada |
|---|---|---|
| ~~Framework de frontend~~ | ✅ Resolvido: Expo (React Native) confirmado. | [ADR 0002](../decisions/0002-frontend-framework-pendente.md) |
| ~~Divisão de tarefas da equipe~~ | ✅ Resolvido. | [ADR 0004](../decisions/0004-divisao-equipe-final.md) |
| **Cotação conjunta da lista de compras de hardware** | Itens "Semana 1" do BoM são bloqueadores explícitos do início do trabalho em `edge/`, sem eles comprados (e com compatibilidade elétrica conferida em conjunto), ninguém consegue montar o protótipo físico. | [`lista-compras-hardware.md`](lista-compras-hardware.md) |
| **Schema fino das tabelas do banco** (colunas de `registros_imagem`, `leituras_ambientais`, `diagnosticos`, `alertas`, `usuarios`, `dispositivos`) | Bloqueia a implementação real de `cloud/app/db/models.py`, `infra/supabase/schema.sql` e, por consequência, boa parte do backend. Pode ser decidido em paralelo à ML/frontend, mas precisa fechar cedo. | `infra/supabase/schema.sql`, `cloud/app/db/models.py` |
| **Correção das contradições textuais do TC1** (câmera V2→V3, contagem de classes do dataset, 10, não 11, hospedagem Railway em vez de AWS ECS/Cloud Run, autenticação) | Não bloqueia código, mas é um item explícito da Fase 0 do Plano de Execução do Blueprint, um avaliador pode notar a contradição entre TC1 e este Blueprint se não for corrigida a tempo. Baixo esforço, mas fácil de esquecer. | Blueprint, Plano de Execução, item 2 da Fase 0 |

### 1.2 — Podem esperar (não bloqueiam o início do desenvolvimento)

| Decisão | Quando precisa estar resolvida | Onde está documentada |
|---|---|---|
| **Momento de ativação do trial do Railway** | Deliberadamente adiado, só perto da Sprint 9 (validação em campo). Ver Seção 5 deste documento. | [`infra/railway/README.md`](../../infra/railway/README.md), Blueprint Seção 4.5 |
| **Data da banca / apresentação final** | Depende da coordenação do curso, fora do controle do grupo, mas assim que sair, deve alimentar imediatamente o calendário de sincronização. | [`infra/calendar/sincronizacao.md`](../../infra/calendar/sincronizacao.md) |
| **Configuração do ping automático do UptimeRobot** | Necessário antes de qualquer período de 7+ dias sem uso do sistema, o Blueprint sugere configurar na Sprint 6, não antes. | [`infra/monitoring/uptimerobot.md`](../../infra/monitoring/uptimerobot.md) |
| **Política de leitura de imagens no Supabase Storage** (signed URLs vs. bucket com leitura pública das imagens) | Só importa quando o dashboard for de fato exibir fotos, não bloqueia o desenvolvimento inicial do backend. | [`infra/supabase/storage_policies.md`](../../infra/supabase/storage_policies.md) |
| **Encomenda da placa de solda final e da case impressa em 3D** | Itens de Semana 4-5 do BoM, só depois do layout do circuito estar validado em protoboard. | [`lista-compras-hardware.md`](lista-compras-hardware.md) |
| **Mecanismo de envio de push notifications do lado do servidor** | Só relevante se Expo for a escolha final de frontend; mesmo assim, é um refinamento tardio, não algo que bloqueia o MVP. | `app/src/notifications/pushNotifications.ts` |

---

## 2. Decisão final da equipe

Registrada formalmente em [ADR 0004](../decisions/0004-divisao-equipe-final.md).

| Pessoa | Responsabilidade |
|---|---|
| **João** | `ml/` — pipeline de IA completo (dataset, treino, exportação `.tflite`) |
| **Amanda** | `app/` — frontend/dashboard. Framework confirmado: **Expo (React Native)** ([ADR 0002](../decisions/0002-frontend-framework-pendente.md)) |
| **Higor** | `cloud/` + `infra/` + `edge/` — banco de dados, backend/API, scripts embarcados do Raspberry Pi |
| **Igor** | **Documentação do projeto** (permanente) + **apoio à Amanda no `app/`** (temporário, primeiras semanas) |

### Igor — documentação (responsabilidade permanente)

Detalhamento completo em
[`responsabilidades-documentacao-igor.md`](responsabilidades-documentacao-igor.md):
manutenção dos ADRs (`docs/decisions/`) e das atas (`docs/atas/`),
organização da pasta do Google Drive (link no README raiz) e do Figma
(protótipos de UI), organização das reuniões do grupo (agendamento,
pautas, registro de decisões), manutenção deste roadmap e do calendário
de sincronização, e coordenação da escrita do TCC.

### Igor — apoio ao `app/` (responsabilidade temporária, primeiras semanas)

Amanda é a responsável técnica pelo `app/` — **é ela quem define o que
o Igor vai fazer** nessa frente, alinhando diretamente com ele antes de
cada tarefa. Não há uma lista de tarefas de frontend pré-atribuída a
ele; a divisão exata (quais telas, quais componentes) é combinada entre
os dois no início do trabalho em `app/`. Quando Amanda considerar que
não precisa mais de apoio direto, Igor passa a dedicar 100% do tempo à
documentação.

### Por que essa divisão

- Backend, infraestrutura e scripts embarcados exigem lógica de
  servidor, autenticação e integração com hardware — Higor concentra
  essas três camadas, como ele mesmo havia cogitado desde o início.
- Igor não se sente confortável com esse tipo de trabalho. Documentação
  do projeto é uma frente que **não tinha dono formal** até esta
  decisão, apesar de já existir estrutura para ela no repositório
  (`docs/decisions/`, `docs/atas/`, `docs/tcc/`) — e o apoio pontual ao
  `app/` nas primeiras semanas evita que ele fique ocioso enquanto essa
  frente ainda não tem volume de trabalho constante (ela cresce
  conforme o projeto se aproxima da banca).

---

## 3. Cronograma por pessoa

Cada lista é sequencial — item N depende, em geral, de itens anteriores
terem sido concluídos (ou pelo menos iniciados) pela mesma pessoa. Itens
marcados com 🔧 dependem de hardware físico já montado/disponível; todos
os demais podem começar imediatamente, em paralelo, assim que a Fase 0
for concluída. Ver também a Seção 4 para a visão consolidada dessa
separação.

### 3.1 — João (`ml/`)

1. Participar da reunião de Fase 0 (decisões da Seção 1.1), mesmo fora
   da sua área.
2. Configurar o ambiente do Google Colab (GPU T4) e credenciais da API
   do Kaggle.
3. Baixar PlantVillage e o Mendeley Tomato Disease Dataset
   (`ml/src/dataset/download.py`).
4. Confirmar com o grupo (e documentar) quais são as 6 classes de baixo
   risco de corrosão de segmentação que vão receber `rembg`.
5. Aplicar `rembg` seletivo nessas 6 classes — executar **uma vez**,
   salvar o resultado no Google Drive (leva 4-8h para ~7k imagens).
6. Compor a estratégia "Frankenstein": folhas recortadas sobre fundos
   reais de estufa, fundido com o Mendeley
   (`ml/src/dataset/frankenstein_compose.py`).
7. Montar o pipeline de data augmentation com Albumentations
   (`ml/src/dataset/augmentation.py`).
8. Fazer o split 70/15/15 e calcular `class_weight`
   (`sklearn.utils.class_weight.compute_class_weight`) para compensar o
   desbalanceamento das classes.
9. Treinar MobileNetV2 via transfer learning (`ml/src/training/train.py`).
10. Avaliar no conjunto sintético: matriz de confusão, F1 por classe, F1
    weighted (`ml/src/training/evaluate.py`) — meta mínima ≥75%, ideal ≥82%.
11. Com o grupo (e com apoio do Igor na redação, ver Seção 6 de
    `responsabilidades-documentacao-igor.md`), redigir a justificativa
    proativa do risco estatístico do split 70/15/15 para a banca.
12. Exportar o modelo para `.tflite`, validar tamanho/latência
    (`ml/src/export/convert_tflite.py`) e commitar em `ml/models/`.
13. Entregar essa primeira versão do `.tflite` para o Higor integrar no
    backend (`cloud/app/core/inference.py`).
14. 🔧 Assim que as primeiras imagens reais forem coletadas em campo
    (Sprint 9), rodar a avaliação real (meta F1 real ≥65%, ideal ≥72%)
    e documentar o gap sintético×real (meta <10 p.p.).
15. Iterar/retreinar se o gap for maior que o aceitável; documentar o
    pipeline completo para o capítulo de metodologia do TCC.

### 3.2 — Higor (`cloud/` + `infra/` + `edge/`)

1. Levar para a reunião de Fase 0 uma proposta de schema fino das
   tabelas, para o grupo fechar junto.
2. Criar o projeto no Supabase (Postgres + Storage) — **pode ser feito
   imediatamente**, é gratuito e não expira (só pausa por inatividade).
3. Modelar as tabelas reais a partir do schema fechado
   (`infra/supabase/schema.sql` → tabelas de fato no Supabase).
4. Configurar o bucket `ecovision-imagens` no Supabase Storage e revisar
   a política de acesso (`infra/supabase/storage_policies.md`).
5. Implementar `cloud/app/config.py`, `cloud/app/db/session.py` e
   `cloud/app/core/security.py` (API Key do dispositivo + JWT/bcrypt).
6. Implementar `cloud/app/api/routes/auth.py`, `cloud/app/storage/supabase_storage.py`
   e `cloud/app/core/inference.py` (com modelo dummy até o João
   entregar o `.tflite` real).
7. Implementar `cloud/app/api/routes/diagnostico.py`, rodando **local**
   via `uvicorn`, apontando para o Supabase na nuvem, e as demais rotas
   (`dispositivos.py`, `alertas.py`, `historico.py`).
8. Escrever testes simulando requisições do Pi (`cloud/tests/`); trocar
   o modelo dummy pelo `.tflite` real assim que o João entregar.
9. Configurar o ping do UptimeRobot na Sprint 6; preparar a configuração
   de deploy, **sem ativar o trial do Railway ainda** (ver Seção 5).
10. 🔧 Assim que as peças da Semana 1 chegarem: estudar Picamera2,
    RPi.GPIO e libs Adafruit; montar em protoboard e validar cada
    sensor isoladamente (DHT22, solo+ADS1115, câmera+LED via MOSFET).
11. 🔧 Implementar `edge/src/capture.py`, `edge/src/compress.py`,
    `edge/src/actuators/led_flash.py`, `edge/src/queue/offline_queue.py`
    e `edge/src/upload/uploader.py`, integrando tudo em
    `edge/src/main.py`.
12. 🔧 Testar a fila offline simulando quedas de rede; validar contra o
    backend local e, depois, contra o Railway.
13. 🔧 Apoiar a montagem final (placa soldada + case 3D); quando a data
    da banca for confirmada, calcular a janela de 30 dias e ativar o
    Railway; fazer o deploy real.
14. 🔧 Instalar o hardware na estufa real e iniciar a coleta das 80-100
    imagens reais o quanto antes (Sprint 9) — maior risco de cronograma
    do projeto.
15. 🔧 Testes end-to-end reais: Pi → API no Railway → Supabase →
    dashboard.

### 3.3 — Amanda (`app/`)

1. Com o framework já definido (Expo/React Native — [ADR 0002](../decisions/0002-frontend-framework-pendente.md)),
   revisar/ajustar o esqueleto já existente em `app/src/` e inicializar
   o projeto Expo real localmente.
2. Alinhar com o Igor, logo no início, quais tarefas ele vai assumir no
   `app/` enquanto estiver dando apoio (ver checklist em
   `responsabilidades-documentacao-igor.md`, Seção 7) — evitar
   sobreposição de trabalho.
3. Implementar `LoginScreen` + a lógica de autenticação
   (`app/src/services/auth.ts`) e o cliente HTTP
   (`app/src/services/api.ts`), consumindo o backend **local** do
   Higor (`uvicorn` rodando na própria máquina) — não depende do Railway.
4. Implementar a tela de Diagnóstico (imagem via URL da API, nunca
   acesso direto ao Supabase) e a tela de Histórico + gráfico
   (`DiagnosticoChart`) — as telas mais complexas ficam sob
   responsabilidade direta dela.
5. Revisar as telas que o Igor for entregando (conforme combinado no
   passo 2 — ex.: Alertas, Financeiro).
6. Implementar push notifications (Expo Notifications).
7. Testar tudo contra dados de diagnóstico simulados/mock enquanto o
   modelo de IA real e o hardware não estiverem prontos.
8. Ajustes finais de UI/UX, usando o Figma mantido pelo Igor como
   referência visual.
9. 🔧 Testes end-to-end reais assim que o Pi físico e a API real
   (Railway) estiverem no ar, próximo da Sprint 9.

### 3.4 — Igor (documentação + apoio inicial ao `app/`)

*(Primeiras semanas — dividido entre as duas frentes):*

1. Participar da reunião de Fase 0. Nela, alinhar com a Amanda a
   primeira tarefa de apoio no `app/` (ver
   `responsabilidades-documentacao-igor.md`, Seção 7).
2. Criar o arquivo Figma do projeto e atualizar o link no README raiz
   (hoje está como placeholder).
3. Organizar a pasta do Google Drive em subpastas (atas, TCC,
   referências, apresentações).
4. Depois da reunião de Fase 0, criar a primeira ata em `docs/atas/`.
5. Implementar, no `app/`, a(s) tarefa(s) combinadas com a Amanda no
   passo 1 (ex.: telas mais simples como Alertas e Financeiro),
   consumindo o backend local do Higor.
6. Corrigir as contradições textuais do TC1 (câmera V2→V3, contagem de
   classes 10, hospedagem Railway, autenticação) — item explícito da
   Fase 0 do Blueprint.

*(A partir daqui — documentação em ritmo crescente, conforme a Amanda
for precisando de menos apoio direto no `app/`):*

7. Manter o ciclo de reuniões a cada sprint: agendar, montar pauta,
   registrar ata.
8. Registrar como ADR novo qualquer decisão de arquitetura/processo que
   o grupo tomar a partir daqui.
9. Preencher `infra/calendar/sincronizacao.md` assim que a data da
   banca for confirmada pela coordenação.
10. Manter `lista-compras-hardware.md` atualizada conforme o grupo cota
    e compra os itens.
11. Coordenar a escrita dos capítulos do TCC (`docs/tcc/`) com quem for
    redigir cada parte, incluindo a justificativa proativa do risco
    estatístico do split 70/15/15 (com o João).
12. 🔧 Documentar o processo de coleta de campo (Sprint 9) e o gap F1
    sintético×real assim que os dados existirem, para uso direto no TCC.
13. 🔧 Garantir que toda a documentação de decisões esteja atualizada
    antes da banca; apoiar os testes end-to-end finais como "segundo
    par de olhos" (QA), sem estar na linha de frente da integração técnica.

---

## 4. O que pode ser feito agora × o que depende do hardware

Esta separação é uma propriedade das tarefas, não da divisão de pessoas
— vale independentemente de quem estiver executando cada uma.

### Pode começar imediatamente, em paralelo (não depende de hardware)

- **Todo o pipeline de IA** (`ml/`): download de dataset, `rembg`,
  composição Frankenstein, augmentation, treino, avaliação sintética,
  exportação do `.tflite`. Só a avaliação com **imagens reais** (F1
  real) depende de hardware.
- **Todo o backend** (`cloud/`): schema do banco, Supabase (Postgres +
  Storage), autenticação, todas as rotas, inferência com modelo dummy
  ou real. O backend deve ser desenvolvido e testado **localmente**
  (`uvicorn` local + Supabase na nuvem) durante toda a fase de
  desenvolvimento — ver Seção 5.
- **Boa parte do frontend** (`app/`): decisão de framework, estrutura de
  navegação, autenticação, todas as telas, consumindo o backend local
  com dados mock/simulados. Só o teste **end-to-end com o Pi físico**
  depende de hardware.
- **Escrita da lógica** de `edge/src/queue/offline_queue.py` e
  `edge/src/upload/uploader.py` — podem ser escritos e testados contra
  o backend local com payloads simulados, sem o Pi físico.
- **Documentação e decisões**: correção das contradições do TC1, ADRs,
  justificativa do risco estatístico do split 70/15/15, capítulos do
  TCC que não dependem de resultados de campo.

### Depende do hardware físico ter chegado e sido montado

- Cotação e **compra** da lista de compras (`lista-compras-hardware.md`)
  — pré-requisito de tudo abaixo.
- Montagem e validação em protoboard de cada sensor isoladamente
  (DHT22, sensor de solo + ADS1115, câmera + LED via MOSFET).
- `edge/src/capture.py`, `edge/src/compress.py`,
  `edge/src/actuators/led_flash.py` — dependem da câmera, do LED e do
  MOSFET físicos.
- `edge/src/main.py` rodando o ciclo completo de ponta a ponta no Pi.
- Montagem final (placa soldada + case 3D).
- Instalação na estufa real e **coleta das 80-100 imagens reais** —
  maior risco de cronograma do projeto (Blueprint, Fase 6, item 23):
  não esperar o sistema estar 100% pronto para começar a coletar,
  iniciar assim que o hardware estiver minimamente funcional.
- Avaliação do modelo de IA com **imagens reais** (F1 real, gap
  sintético×real).
- Testes end-to-end completos (Pi → API → banco/storage → dashboard).
- Deploy real no Railway (ver Seção 5 — deliberadamente adiado, mas
  tecnicamente também poderia ser feito antes; a razão de esperar é de
  cronograma de crédito gratuito, não de dependência técnica de
  hardware).

---

## 5. Supabase × Railway — por que a estratégia de ativação é diferente

Registro oficial da decisão de infraestrutura, para não se perder entre
conversas do grupo (ver também [`infra/README.md`](../../infra/README.md)
e [`infra/railway/README.md`](../../infra/railway/README.md)).

### Supabase — configurar e usar desde já

- O free tier do Supabase **não expira** com o tempo. Ele só **pausa**
  após 7 dias corridos de inatividade — e isso é reversível (basta
  reativar o projeto no painel) e mitigável com um ping automático via
  UptimeRobot (a configurar na Sprint 6, não antes).
- Por não ter prazo de expiração, não existe motivo para adiar sua
  criação. **Criar o projeto no Supabase é uma das primeiras tarefas do
  Higor** (responsável por `cloud/` + `infra/` — ver Seção 2), logo
  depois do schema ser fechado.
- Isso significa que o banco de dados e o bucket de imagens existem "de
  verdade" desde o início do projeto — todo mundo já desenvolve contra
  dados reais na nuvem, não contra mocks locais de banco.

### Railway — ativação deliberadamente adiada

- O free trial do Railway dura **30 dias corridos a partir da
  ativação** — não são 30 dias de uso, é o relógio correndo desde o
  primeiro deploy. Depois disso, a API para de responder sem um plano
  pago.
- Se o trial for ativado cedo demais (ex.: já nas primeiras semanas do
  projeto, "só para testar"), ele pode expirar **antes** da data real
  da banca — e nesse momento a demonstração ao vivo simplesmente não
  funcionaria.
- Por isso, a estratégia do grupo deve ser: **não ativar o trial do
  Railway até o grupo ter uma data de banca confirmada** e conseguir
  calcular a janela de 30 dias de forma que ela cubra a Sprint 9
  (validação em campo, 14 dias contínuos) **e** a data da apresentação
  final — ver [`infra/calendar/sincronizacao.md`](../../infra/calendar/sincronizacao.md).

### Como isso se traduz na prática, dia a dia

- **Durante toda a fase de desenvolvimento** (da Fase 0 até pouco antes
  da Sprint 9), o backend roda **localmente** — `uvicorn` na máquina de
  quem estiver desenvolvendo — apontando para o **Supabase na nuvem**
  (que já existe e não expira). É assim que Higor, Amanda e Igor testam
  a integração entre frontend, backend e banco sem gastar um único dia
  da janela de 30 dias do Railway.
- Só **perto da Sprint 9**, com a data da banca confirmada, o grupo
  deve: (1) calcular a janela de 30 dias a partir da data planejada de
  ativação, (2) confirmar que ela cobre a Sprint 9 inteira **e** a data
  da banca, (3) só então ativar o trial e fazer o primeiro deploy real
  no Railway.
- Reservar ~R$30-50 do orçamento do grupo para o plano Hobby do Railway
  (~US$5/mês) como contingência, caso a banca atrase e o trial expire
  antes da apresentação (risco real, já documentado no Blueprint —
  bancas de TCC atrasam com frequência).

---

## 6. Próximos passos imediatos

1. Reunião de Fase 0: usar o cronograma da Seção 3 para cada pessoa
   arrancar suas primeiras tarefas, e fechar o schema fino do banco
   junto com o Higor.
2. Cotar em conjunto a lista de compras (`lista-compras-hardware.md`) e
   comprar os itens de Semana 1.
3. Igor: seguir o checklist de início rápido em
   [`responsabilidades-documentacao-igor.md`](responsabilidades-documentacao-igor.md)
   (Figma, Drive, primeira reunião e ata).
4. Criar as issues correspondentes no GitHub Projects, já com o
   componente (`edge`, `cloud`, `app`, `ml` ou `docs`) e o responsável
   de cada uma.

---

## Apêndice A — Propostas avaliadas antes da decisão final

Este apêndice preserva o raciocínio usado para chegar à decisão da
Seção 2. As três propostas abaixo **não estão mais em aberto** — ficam
aqui como registro de por que a divisão final foi escolhida em vez de
outras alternativas razoáveis (útil para justificar a escolha na banca,
se perguntado).

### A.1 — Propostas consideradas

Três propostas foram comparadas, cada uma seguindo uma lógica de
agrupamento diferente. A decisão final (Seção 2) não é idêntica a
nenhuma delas — ficou mais próxima da Proposta B, mas com o banco de
dados permanecendo com o Higor em vez de ir para o Igor. As listas
cronológicas completas de cada pessoa, em cada proposta, estão na
Seção A.2 deste apêndice.

### Proposta A — Igor em dupla com Amanda no `app/`

| Pessoa | Foco |
|---|---|
| João | `ml/` — pipeline de IA completo |
| Higor | `cloud/` + `infra/` + `edge/` — backend, banco de dados, deploy e scripts do Pi (volta a cobrir tudo que ele mesmo tinha cogitado inicialmente) |
| Amanda | `app/` — lidera a decisão de framework e a arquitetura (navegação, autenticação, integração com a API) e as telas mais complexas (Diagnóstico com imagem, Histórico com gráficos) |
| **Igor** | **`app/` — em dupla com Amanda: telas mais simples (Alertas, Financeiro mock), testes manuais de UI/UX, dados mock para testar contra o backend, e apoio na comparação de frameworks (Fase 0)** |

**Raciocínio:** tira o Igor de qualquer trabalho de backend/API e o
coloca como par de Amanda em `app/`, que é essencialmente
frontend/UI, uma frente mais visual e menos dependente de lógica de
servidor. Amanda mantém a liderança técnica da camada (decisão de
framework, arquitetura), enquanto Igor assume partes mais isoladas e
de menor risco técnico, o que também dá a ele uma primeira experiência
prática de frontend sem travar a Amanda.

**Risco identificado:** Higor absorve três camadas (`cloud/`, `infra/`,
`edge/`) sozinho — volume de trabalho alto e nenhum backup se ele
travar em algo. Se isso pesar demais, considerar migrar para a
Proposta B, que tira a modelagem do banco de cima do Higor.

### Proposta B — Igor dono do banco de dados + documentação

| Pessoa | Foco |
|---|---|
| João | `ml/` — pipeline de IA completo |
| Amanda | `app/` — frontend/dashboard, sozinha |
| Higor | `cloud/` (lógica da API: rotas, autenticação, inferência) + `edge/` (scripts do Pi) |
| **Igor** | **Banco de dados (Supabase: criação do projeto, modelagem das tabelas a partir do schema fechado pelo grupo, bucket de Storage e políticas de acesso) + toda a documentação do projeto (ADRs, atas, `docs/tcc/`, manutenção deste roadmap) + apoio a testes/QA manual do backend e do app** |

**Raciocínio:** separa "desenhar e manter o banco" de "escrever a
lógica de negócio da API" — são habilidades diferentes. Modelar tabelas
no Supabase (via painel/SQL) e escrever documentação técnica exigem
menos código de aplicação do que implementar rotas FastAPI com
autenticação e inferência, o que se encaixa melhor no perfil do Igor.
Isso também resolve, de quebra, uma lacuna real do projeto: a
documentação (ADRs, atas, escrita do TCC) precisa de dono, e hoje
ninguém está formalmente responsável por ela.

**Risco identificado:** Igor e Higor precisam alinhar bem o contrato do
schema (nomes de tabela, colunas, tipos) antes de Higor escrever
`cloud/app/db/models.py` contra ele — se o schema mudar depois que o
Higor já implementou, gera retrabalho. Mitigação: fechar o schema em
conjunto logo na Fase 0 (já é uma decisão bloqueante, ver Seção 1.1) e
tratar qualquer mudança posterior como uma conversa explícita entre os
dois, não um ajuste silencioso de um lado só.

### Proposta C — Híbrida: Igor circula entre `app/` e banco/documentação

| Pessoa | Foco |
|---|---|
| João | `ml/` — pipeline de IA completo |
| Higor | `cloud/` + `edge/` — API e scripts do Pi |
| Amanda | `app/` — dona da camada, com apoio pontual do Igor no início |
| **Igor** | **Fase inicial: apoio a Amanda em telas simples do `app/` + modelagem do banco junto com Higor. Fase intermediária em diante: migra para documentação (ADRs, atas, TCC) e QA/testes de integração em tempo integral** |

**Raciocínio:** em vez de fixar o Igor em uma única frente desde o
início (quando ainda não está claro onde ele rende mais), esta proposta
deixa ele **circular** pelas duas frentes sugeridas — ajudando a
Amanda a arrancar mais rápido nas primeiras semanas de `app/` e, em
paralelo, participando da modelagem do banco (menos código, mais
estrutura, ao lado do Higor) — e só se fixa integralmente em
documentação e QA na segunda metade do projeto, quando essa frente
fica mais crítica (preparação da defesa, justificativas para a banca,
testes de integração antes da Sprint 9). É a proposta mais flexível,
útil se o grupo ainda não tem certeza de qual das duas frentes (app ou
banco/documentação) é o melhor encaixe definitivo para o Igor.

**Risco identificado:** exige mais coordenação — Igor reporta a duas
frentes diferentes na primeira metade do projeto (Amanda e Higor) e
precisa de um ponto de corte claro (sugestão: a partir da conclusão do
schema do banco e da entrega das primeiras telas do app) para migrar
de vez para documentação/QA, sob risco de nunca "aterrissar" numa
responsabilidade fixa.

### Comparação rápida

| Critério | A — Igor no app | B — Igor no banco + docs | C — Híbrida |
|---|---|---|---|
| Evita trabalho de backend para o Igor | Sim | Sim | Sim |
| Carga sobre o Higor | Alta (cloud+infra+edge sozinho) | Média (cloud+edge, sem modelar banco) | Média (cloud+edge, sem modelar banco) |
| Documentação do projeto tem dono claro | Não (ninguém formalmente) | Sim (Igor) | Sim (Igor, a partir da fase intermediária) |
| Risco de ociosidade do Igor no início | Baixo (app tem tarefa desde já) | Baixo (banco pode começar já) | Baixo (as duas frentes começam já) |
| Precisa de ponto de corte/transição explícito | Não | Não | Sim (quando Igor migra para docs/QA) |
| Mudança em relação à ideia original do grupo | Pequena (Igor some do backend, some para Amanda) | Média (Higor perde a parte de banco) | Média (parecida com B, mas com fase inicial em app) |

---

### A.2 — Cronogramas por pessoa, em cada proposta

Cada lista é sequencial — item N depende, em geral, de itens anteriores
terem sido concluídos (ou pelo menos iniciados) pela mesma pessoa. Itens
marcados com 🔧 dependem de hardware físico já montado/disponível; todos
os demais podem começar imediatamente, em paralelo, assim que a Fase 0
for concluída. Ver também a Seção 4 para a visão consolidada dessa
separação.

A lista do **João** é a mesma nas três propostas (`ml/` é sempre solo) —
está descrita uma única vez na Seção 3.1 e referenciada nas demais.

### 3.1 — João (`ml/`) — igual nas três propostas

1. Participar da reunião de Fase 0 (decisões da Seção 1.1), mesmo fora
   da sua área.
2. Configurar o ambiente do Google Colab (GPU T4) e credenciais da API
   do Kaggle.
3. Baixar PlantVillage e o Mendeley Tomato Disease Dataset
   (`ml/src/dataset/download.py`).
4. Confirmar com o grupo (e documentar) quais são as 6 classes de baixo
   risco de corrosão de segmentação que vão receber `rembg`.
5. Aplicar `rembg` seletivo nessas 6 classes — executar **uma vez**,
   salvar o resultado no Google Drive (leva 4-8h para ~7k imagens).
6. Compor a estratégia "Frankenstein": folhas recortadas sobre fundos
   reais de estufa, fundido com o Mendeley
   (`ml/src/dataset/frankenstein_compose.py`).
7. Montar o pipeline de data augmentation com Albumentations
   (`ml/src/dataset/augmentation.py`).
8. Fazer o split 70/15/15 e calcular `class_weight`
   (`sklearn.utils.class_weight.compute_class_weight`) para compensar o
   desbalanceamento das classes.
9. Treinar MobileNetV2 via transfer learning (`ml/src/training/train.py`).
10. Avaliar no conjunto sintético: matriz de confusão, F1 por classe, F1
    weighted (`ml/src/training/evaluate.py`) — meta mínima ≥75%, ideal ≥82%.
11. Com o grupo, redigir a justificativa proativa do risco estatístico
    do split 70/15/15 para a banca (ver `docs/tcc/`).
12. Exportar o modelo para `.tflite`, validar tamanho/latência
    (`ml/src/export/convert_tflite.py`) e commitar em `ml/models/`.
13. Entregar essa primeira versão do `.tflite` para o Higor integrar no
    backend (`cloud/app/core/inference.py`).
14. 🔧 Assim que as primeiras imagens reais forem coletadas em campo
    (Sprint 9), rodar a avaliação real (meta F1 real ≥65%, ideal ≥72%)
    e documentar o gap sintético×real (meta <10 p.p.).
15. Iterar/retreinar se o gap for maior que o aceitável; documentar o
    pipeline completo para o capítulo de metodologia do TCC.

---

### 3.2 — Proposta A (Igor em dupla com Amanda no `app/`)

#### Higor — `cloud/` + `infra/` + `edge/`

1. Levar para a reunião de Fase 0 uma proposta de schema fino das
   tabelas, para o grupo fechar junto.
2. Criar o projeto no Supabase (Postgres + Storage) — **pode ser feito
   imediatamente**, é gratuito e não expira (só pausa por inatividade).
3. Modelar as tabelas reais a partir do schema fechado
   (`infra/supabase/schema.sql` → tabelas de fato no Supabase).
4. Configurar o bucket `ecovision-imagens` no Supabase Storage e revisar
   a política de acesso (`infra/supabase/storage_policies.md`).
5. Implementar `cloud/app/config.py`, `cloud/app/db/session.py` e
   `cloud/app/core/security.py` (API Key do dispositivo + JWT/bcrypt).
6. Implementar `cloud/app/api/routes/auth.py`, `cloud/app/storage/supabase_storage.py`
   e `cloud/app/core/inference.py` (com modelo dummy até o João
   entregar o `.tflite` real).
7. Implementar `cloud/app/api/routes/diagnostico.py`, rodando **local**
   via `uvicorn`, apontando para o Supabase na nuvem, e as demais rotas
   (`dispositivos.py`, `alertas.py`, `historico.py`).
8. Escrever testes simulando requisições do Pi (`cloud/tests/`); trocar
   o modelo dummy pelo `.tflite` real assim que o João entregar.
9. Configurar o ping do UptimeRobot na Sprint 6; preparar a configuração
   de deploy, **sem ativar o trial do Railway ainda** (ver Seção 5).
10. 🔧 Assim que as peças da Semana 1 chegarem: estudar Picamera2,
    RPi.GPIO e libs Adafruit; montar em protoboard e validar cada
    sensor isoladamente (DHT22, solo+ADS1115, câmera+LED via MOSFET).
11. 🔧 Implementar `edge/src/capture.py`, `edge/src/compress.py`,
    `edge/src/actuators/led_flash.py`, `edge/src/queue/offline_queue.py`
    e `edge/src/upload/uploader.py`, integrando tudo em
    `edge/src/main.py`.
12. 🔧 Testar a fila offline simulando quedas de rede; validar contra o
    backend local e, depois, contra o Railway.
13. 🔧 Apoiar a montagem final (placa soldada + case 3D); quando a data
    da banca for confirmada, calcular a janela de 30 dias e ativar o
    Railway; fazer o deploy real.
14. 🔧 Instalar o hardware na estufa real e iniciar a coleta das 80-100
    imagens reais o quanto antes (Sprint 9) — maior risco de cronograma
    do projeto.
15. 🔧 Testes end-to-end reais: Pi → API no Railway → Supabase →
    dashboard.

#### Amanda — `app/` (líder da camada)

1. Responder, com dados se possível, a pergunta de confiança em
   Expo/React Native do Blueprint (Fase 5) — decisão de Fase 0, com
   apoio do Igor na avaliação (ver lista dele).
2. Se Expo: inicializar o projeto e revisar/ajustar o esqueleto já
   existente em `app/src/`. Se PWA/Streamlit: montar a estrutura
   equivalente do zero (o esqueleto atual está em Expo — ver
   [ADR 0002](../decisions/0002-frontend-framework-pendente.md)).
3. Implementar `LoginScreen` + a lógica de autenticação
   (`app/src/services/auth.ts`) e o cliente HTTP
   (`app/src/services/api.ts`), consumindo o backend **local** do
   Higor.
4. Implementar a tela de Diagnóstico (imagem via URL da API, nunca
   acesso direto ao Supabase) e a tela de Histórico + gráfico
   (`DiagnosticoChart`) — as duas telas mais complexas.
5. Definir com o Igor a divisão exata das telas restantes (Alertas,
   Financeiro) e revisar o que ele for entregando.
6. (Se Expo) Implementar push notifications.
7. Ajustes finais de UI/UX com o grupo.
8. 🔧 Testes end-to-end reais assim que o Pi físico e a API real
   (Railway) estiverem no ar, próximo da Sprint 9.

#### Igor — `app/`, em dupla com Amanda

1. Nos primeiros dias da Fase 0, ajudar a comparar Expo × PWA ×
   Streamlit na prática (ex.: montar uma tela simples em duas opções)
   para embasar a decisão da Amanda com dados, não só opinião.
2. Depois da decisão tomada, implementar a tela de Alertas, consumindo
   `cloud/app/api/routes/alertas.py` contra o backend local do Higor.
3. Implementar a tela Financeira (mock, sem integração real).
4. Testar as telas com dados de diagnóstico simulados/mock (o modelo de
   IA real e o hardware ainda não estarão prontos nesta fase).
5. Fazer QA manual de todo o app conforme a Amanda for entregando as
   telas mais complexas — clicar em tudo, achar bugs de fluxo/UX antes
   do grupo, reportar como issues no GitHub Projects.
6. Ajudar a documentar a decisão final de framework no
   [ADR 0002](../decisions/0002-frontend-framework-pendente.md).
7. 🔧 Apoiar os testes end-to-end reais próximo da Sprint 9, junto com
   Amanda e Higor.

---

### 3.3 — Proposta B (Igor dono do banco de dados + documentação)

#### Higor — `cloud/` + `edge/` (sem a modelagem do banco)

1. Participar da reunião de Fase 0 e alinhar com o Igor o schema fino
   das tabelas (colunas, tipos) — Higor implementa contra o schema que
   os dois fecharem juntos, mas não é ele quem modela/mantém o banco.
2. Implementar `cloud/app/config.py`, `cloud/app/db/session.py`
   (conexão contra o banco que o Igor for configurando) e
   `cloud/app/core/security.py`.
3. Implementar `cloud/app/api/routes/auth.py`,
   `cloud/app/storage/supabase_storage.py` e `cloud/app/core/inference.py`
   (com modelo dummy até o João entregar o `.tflite` real).
4. Implementar `cloud/app/api/routes/diagnostico.py`, rodando **local**
   via `uvicorn`, e as demais rotas (`dispositivos.py`, `alertas.py`,
   `historico.py`).
5. Escrever testes (`cloud/tests/`), com apoio do Igor no QA manual
   (ver lista dele); trocar o modelo dummy pelo `.tflite` real do João.
6. 🔧 Assim que as peças da Semana 1 chegarem: montar em protoboard,
   validar sensores e implementar `edge/src/` (capture, compress,
   led_flash, offline_queue, uploader, main.py).
7. 🔧 Integrar e testar o ciclo completo do Pi contra o backend local.
8. Configurar o ping do UptimeRobot na Sprint 6; preparar a configuração
   de deploy, sem ativar o trial do Railway ainda.
9. 🔧 Quando a data da banca for confirmada, ativar o Railway e fazer o
   deploy real; apoiar a montagem final do hardware.
10. 🔧 Testes end-to-end reais: Pi → API no Railway → Supabase →
    dashboard.

#### Amanda — `app/` (sozinha)

1. Responder a pergunta de confiança em Expo/React Native (Fase 0).
2. Inicializar/ajustar a estrutura do projeto conforme a decisão de
   framework (ver [ADR 0002](../decisions/0002-frontend-framework-pendente.md)).
3. Implementar autenticação (`auth.ts`) e cliente HTTP (`api.ts`),
   contra o backend local do Higor.
4. Implementar as telas: Alertas, Diagnóstico, Histórico + gráfico,
   Financeiro (mock).
5. (Se Expo) Implementar push notifications.
6. Testar tudo com dados mock; ajustes finais de UI/UX.
7. 🔧 Testes end-to-end reais próximo da Sprint 9.

#### Igor — banco de dados + documentação

1. Participar da reunião de Fase 0 e propor, junto com Higor, o schema
   fino das tabelas (`registros_imagem`, `leituras_ambientais`,
   `diagnosticos`, `alertas`, `usuarios`, `dispositivos`).
2. Criar o projeto no Supabase (Postgres + Storage) — **pode ser feito
   imediatamente**, não expira, só pausa por inatividade.
3. Modelar as tabelas reais no Supabase a partir do schema fechado
   (atualizar `infra/supabase/schema.sql` como documentação viva desse
   schema).
4. Configurar o bucket `ecovision-imagens` e a política de acesso
   (`infra/supabase/storage_policies.md`), decidindo com o grupo entre
   signed URLs e leitura pública.
5. Corrigir as contradições textuais do TC1 (câmera V2→V3, contagem de
   classes 10, hospedagem, autenticação) — item explícito da Fase 0 do
   Blueprint.
6. Assumir a manutenção contínua dos ADRs em `docs/decisions/` e das
   atas de reunião em `docs/atas/`, garantindo que toda decisão nova do
   grupo fique registrada.
7. Preencher o calendário de sincronização
   (`infra/calendar/sincronizacao.md`) assim que a data da banca sair.
8. Fazer QA manual do backend (testar endpoints com `curl`/Postman
   contra o `uvicorn` local do Higor) e do app (clicar em tudo, reportar
   bugs de fluxo como issues).
9. Começar a redigir, com o João, a justificativa proativa do risco
   estatístico do split 70/15/15 para o capítulo de metodologia do TCC
   (`docs/tcc/`).
10. 🔧 Documentar o processo de coleta de campo (Sprint 9) e o gap
    F1 sintético×real assim que os dados existirem, para uso direto no
    TCC.
11. 🔧 Apoiar os testes end-to-end finais como "segundo par de olhos"
    (QA), sem estar na linha de frente da integração técnica.

---

### 3.4 — Proposta C (híbrida: `app/` no início, banco + documentação depois)

#### Higor — `cloud/` + `edge/`

Mesma lista da Proposta B (Seção 3.3), com uma diferença: nos passos 1
e 6-7 (schema e montagem do banco), o parceiro de alinhamento passa a
ser o Igor **apenas durante a fase inicial** (primeiras semanas) — a
partir do momento em que Igor migra para documentação/QA (ver lista
dele), Higor segue sozinho em qualquer ajuste fino do banco que ainda
for necessário.

#### Amanda — `app/` (dona da camada, com apoio pontual do Igor)

Mesma lista da Proposta A (Seção 3.2), exceto pelo passo 5: a divisão
de telas com o Igor vale apenas para as primeiras semanas — depois que
ele migrar para documentação/QA (por volta da entrega das telas de
Alertas/Financeiro), Amanda assume sozinha o restante do polimento e os
testes end-to-end finais.

#### Igor — fase 1 em `app/` + banco, fase 2 em documentação/QA

*(Fase inicial, semanas 1-3, dividido entre as duas frentes):*
1. Participar da reunião de Fase 0: ajudar a comparar frameworks de
   frontend com a Amanda (mesmo passo 1 da Proposta A) **e** ajudar o
   Higor a propor o schema fino das tabelas (mesmo passo 1 da
   Proposta B).
2. Implementar a tela de Alertas no `app/`, consumindo o backend local.
3. Em paralelo, criar o projeto no Supabase e modelar as tabelas reais
   a partir do schema fechado (mesmos passos 2-3 da Proposta B).
4. Implementar a tela Financeira (mock) no `app/`.
5. Configurar o bucket `ecovision-imagens` e revisar a política de
   acesso, junto com o Higor.

*(Ponto de corte: assim que as telas de Alertas/Financeiro estiverem
entregues e o schema modelado no Supabase, Igor migra integralmente
para a frente abaixo.)*

*(Fase 2, em diante — documentação e QA em tempo integral):*
6. Corrigir as contradições textuais do TC1 (câmera, contagem de
   classes, hospedagem, autenticação).
7. Assumir a manutenção dos ADRs (`docs/decisions/`) e das atas
   (`docs/atas/`).
8. Preencher o calendário de sincronização assim que a data da banca
   sair.
9. Fazer QA manual do backend e do app conforme forem evoluindo,
   reportando bugs como issues.
10. Redigir, com o João, a justificativa do risco estatístico do split
    70/15/15 para o TCC.
11. 🔧 Documentar a coleta de campo (Sprint 9) e o gap F1 sintético×real.
12. 🔧 Coordenar (não necessariamente executar) os testes end-to-end
    finais, checando que toda a documentação de decisões está
    atualizada antes da banca.

