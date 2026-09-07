# cloud: Backend / API (Railway + Supabase)

Camada de backend do EcoVision. Referência arquitetural completa: **Tech Stack Blueprint Consolidado v3.0, Fase 4 (Nuvem, Backend e Banco de Dados)**.

## Papel desta camada

- Hospeda a API FastAPI que roda no **Railway** (PaaS: só executa código, não persiste nada).
- Carrega o modelo `.tflite` em memória (TFLite Runtime) e roda a inferência sobre as imagens recebidas do Raspberry Pi.
- Processa tudo em memória via `BytesIO`: **zero gravação em disco no container** (Blueprint, Seção 4.4, regras 1-4).
- Fala com o **Supabase** (Postgres + Storage) para persistir dados estruturados e imagens. O Supabase nunca é acessado diretamente pelo frontend, sempre através desta API.
- Implementa as duas pontas de autenticação decididas no Blueprint (Seção 4.3):
  - **API Key estática** para o dispositivo IoT (Raspberry Pi → API): **implementada**.
  - **JWT de curta duração (24h) + refresh token (30 dias) + bcrypt** para o login do produtor no dashboard: **não implementada nesta rodada**, ver "Escopo" abaixo.

## Escopo implementado nesta rodada

Combinado com o grupo: o `app/` (dashboard, Expo/React Native) ainda está no
mesmo estágio de esqueleto que o `cloud/` estava antes desta rodada, só
telas e mocks JSON, sem login nem consumo de API de verdade. Por isso, esta
rodada cobre **só o caminho do dispositivo**:

- ✅ `POST /diagnostico`: recebe imagem + leituras do Pi, roda inferência
  (com fallback se não houver modelo `.tflite` ainda, ver `app/core/inference.py`),
  sobe a imagem pro Supabase Storage e grava no Postgres.
- ✅ Autenticação por API Key do dispositivo.
- ✅ Schema completo do banco (6 tabelas, ver abaixo), já desenhado
  pensando nos campos que os mocks do `app/` esperam, para não exigir
  retrabalho quando o dashboard for implementado. **Já aplicado no
  Supabase real do projeto** (não só nos testes).
- ✅ Idempotência: reenvio da mesma captura (`idempotency_key`, gerado
  pelo `edge/`) não duplica a linha no banco, devolve o diagnóstico já
  existente. Validado contra o Supabase real, não só em teste.
- ✅ Logging estruturado (`stdout`) em todo o fluxo do `/diagnostico`,
  requisito não negociável do Blueprint (regra 3 abaixo).
- ✅ Tratamento de erro de imagem corrompida (400, em vez de 500 cru) e
  de falha no upload pro Storage (502, logado).
- ✅ Geração automática de alerta quando o diagnóstico não é "saudavel"
  nem o placeholder "indisponivel".
- ✅ Alerta ambiental automático (temperatura, umidade do ar, umidade do
  solo fora da faixa): limiares e fontes documentados em
  [ADR 0005](../docs/decisions/0005-limiares-ambientais.md), aplicados
  em `app/core/alertas_ambientais.py`. Temperatura/umidade do ar vêm da
  Embrapa; umidade do solo é uma convenção prática de ponto de partida
  (ver o ADR: sensor de baixo custo não mede nas unidades que a
  literatura científica usa), a recalibrar com o sensor físico.
- ✅ `GET /health`: endpoint leve (sem autenticação) pro UptimeRobot
  pingar e manter Supabase/Railway ativos (`infra/monitoring/uptimerobot.md`).
- ✅ CI (`.github/workflows/tests.yml`) rodando `edge/tests` e
  `cloud/tests` automaticamente a cada push/PR que toque essas pastas.
- ✅ Recomendações de manejo por classe de diagnóstico (10 classes do
  PlantVillage, com fontes citadas em
  [ADR 0006](../docs/decisions/0006-recomendacoes-por-diagnostico.md)),
  incluindo correlação em texto com risco ambiental quando os dois
  ocorrem no mesmo ciclo.
- ✅ Revisão de segurança/robustez: `/health` agora responde 503 (não
  200) quando o banco falha; timestamp/leitura inválidos são recusados
  com 422 antes de subir a imagem pro storage (evita arquivo órfão no
  bucket); imagem acima de 5MB é recusada com 413; e uma corrida entre
  duas requisições com a mesma `idempotency_key` não derruba mais a
  requisição com um erro de chave duplicada.
- ⏳ **Não implementado ainda**: login/JWT/bcrypt do dashboard, RBAC, e as
  rotas `auth`, `dispositivos`, `alertas`, `historico`, ficam para quando
  alguém for implementar o `app/` de verdade.

## Fluxo de dados que esta camada implementa (Blueprint, Seção 4.2)

1. Recebe `POST /diagnostico` do Pi (imagem + leituras de sensores), autenticado via API Key.
2. Roda a inferência TFLite em memória (resize 224×224, normalização) e devolve um resultado placeholder (`classe: "indisponivel"`) se o modelo `.tflite` ainda não existir, em vez de falhar (situação atual: `ml/` ainda não entregou um modelo treinado).
3. Grava a imagem no **Supabase Storage** (bucket `ecovision-imagens`) e recebe o caminho salvo.
4. Grava caminho + diagnóstico + leituras nas tabelas do **Supabase Postgres**.
5. Descarta o buffer da imagem da RAM.
6. Serve o dashboard/app através de endpoints autenticados via JWT, pendente, ver "Escopo" acima.

## Schema do banco (6 tabelas)

Ver `cloud/app/db/models.py` (fonte de verdade em Python) e
`infra/supabase/schema.sql` (mesma coisa em SQL puro, pra revisão fácil em
grupo). IDs são inteiros autoincremento (portável entre o Postgres real e
o SQLite usado nos testes).

- **`registros_imagem`**, **`leituras_ambientais`**, **`diagnosticos`**:
  gravadas de verdade por `POST /diagnostico` nesta rodada.
- **`alertas`**, **`usuarios`**, **`dispositivos`**: schema pronto, ainda
  não populadas (dashboard).

Decisão de design: `registros_imagem.caminho_arquivo` guarda só o
**caminho** dentro do bucket, não a URL resolvida: a escolha entre signed
URL e bucket público (`infra/supabase/storage_policies.md`, ainda em
aberto) fica pro código que **lê** a imagem depois, sem acoplar essa
decisão ao schema.

## Estrutura

```
cloud/
├── app/
│   ├── main.py              # entrypoint FastAPI + Uvicorn (1 worker)
│   ├── config.py            # variáveis de ambiente / settings
│   ├── api/routes/          # endpoints HTTP (só diagnostico.py implementado)
│   ├── core/                # segurança (API Key) e inferência TFLite
│   ├── db/                  # SQLAlchemy async, modelos, schemas Pydantic
│   └── storage/             # integração com Supabase Storage
├── alembic/                 # migrations do schema Postgres (inicializado)
├── tests/                   # testes automatizados (ver cloud/tests/README.md)
└── requirements.txt
```

## Regras obrigatórias (não negociáveis, Blueprint Seção 4.4)

1. Modelo `.tflite` versionado no GitHub, nunca salvo em volume do Railway.
2. Processamento de imagem 100% em memória: nenhum `open()` de escrita no pipeline de inferência.
3. Logs via `stdout`, nunca em disco.
4. Imagem é sempre gravada no Supabase Storage antes de ser descartada da memória.
5. Instalar apenas `tflite-runtime` em produção, **nunca** o pacote `tensorflow` completo (estoura a RAM do Railway).

## Como rodar localmente

```bash
cd cloud
pip install -r requirements.txt
cp ../infra/env/cloud.env.example .env   # preencher com credenciais reais ou de teste
alembic upgrade head                      # cria o schema no Postgres/DATABASE_URL configurado
uvicorn app.main:app --reload
```

Sem um `.tflite` real em `TFLITE_MODEL_PATH`, a API sobe normalmente e
`/diagnostico` devolve um resultado placeholder (ver `app/core/inference.py`).

## Pendências de grupo

- Login/JWT do dashboard + rotas de auth/dispositivos/alertas/histórico,
  quando `app/` for implementado de verdade.
- Decidir signed URL vs bucket público para leitura de imagens no
  dashboard (`infra/supabase/storage_policies.md`).
- **Chave de API única e global** (`app/core/security.py`): `device_id`
  não é validado contra nenhum cadastro, aceitável com 1 dispositivo
  físico (ADR 0003), mas precisa virar chave por dispositivo antes de
  qualquer deploy com mais de um Pi em campo.
- Substituir o resultado placeholder de inferência assim que `ml/` entregar
  um `.tflite` treinado (o mapeamento classe→recomendação em
  `app/core/inference.py` também é placeholder até lá).
- Recalibrar o limiar de umidade do solo (`app/core/alertas_ambientais.py`)
  assim que o sensor físico estiver calibrado de verdade, ver
  [ADR 0005](../docs/decisions/0005-limiares-ambientais.md).
