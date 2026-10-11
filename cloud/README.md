# cloud: Backend / API (Railway + Supabase)

Camada de backend do EcoVision. Referência arquitetural completa:
[**Blueprint v4.0**](../docs/architecture/blueprint-v4.md), que
consolida o estado real do sistema e substitui o Blueprint v3.0 como
documento de consulta.

**Em produção:** `https://ecovision-production.up.railway.app`
([ADR 0014](../docs/decisions/0014-deploy-railway-e-gate-de-ci.md)).

## Papel desta camada

- Hospeda a API FastAPI que roda no **Railway** (PaaS: só executa código, não persiste nada).
- Carrega o modelo `.tflite` em memória (TFLite Runtime) e roda a inferência sobre as imagens recebidas do Raspberry Pi.
- Processa tudo em memória via `BytesIO`: **zero gravação em disco no container**.
- Fala com o **Supabase** (Postgres + Storage) para persistir dados estruturados e imagens. O Supabase nunca é acessado diretamente pelo frontend, sempre através desta API.
- Implementa as duas pontas de autenticação:
  - **Credencial por dispositivo** para o Pi, com pareamento por código
    ([ADR 0009](../docs/decisions/0009-credencial-por-dispositivo.md)).
  - **JWT (24h) + refresh token (30 dias) + bcrypt** para o login do
    produtor, com cadastro aberto, confirmação por e-mail e RBAC por
    posse de dispositivo
    ([ADR 0010](../docs/decisions/0010-cadastro-aberto-e-rbac.md)).

## Endpoints

### Caminho do dispositivo

| Rota | O que faz |
|---|---|
| `POST /diagnostico` | Recebe imagem e leituras do Pi, roda inferência, sobe a imagem para o Storage, grava no Postgres e gera alertas. Idempotente por `idempotency_key` |

### Autenticação do produtor

| Rota | O que faz |
|---|---|
| `POST /auth/register` | Cria conta. Cadastro aberto, papel sempre `produtor`, e-mail pendente |
| `POST /auth/verify-email` | Confirma a conta com o código de 6 dígitos |
| `POST /auth/resend-code` | Reenvia o código de uma conta pendente (intervalo mínimo de 60s) |
| `POST /auth/login` | JWT de acesso + refresh token. Recusa conta não confirmada com 403 |
| `POST /auth/forgot-password` | Envia código de redefinição. Resposta idêntica exista ou não a conta |
| `POST /auth/reset-password` | Troca a senha pelo código, com as mesmas regras de força do cadastro |
| `POST /auth/refresh` | Novo access token a partir do refresh token |

### Consulta do dashboard (exigem JWT, filtradas por dono)

| Rota | O que faz |
|---|---|
| `GET /leituras` | Leituras ambientais, filtro opcional `?horas=N` |
| `GET /diagnosticos` | Diagnósticos com `device_id` e signed URL da imagem. `?horas=N` e `?limite=N`: o limite existe porque a rota faz uma chamada ao Supabase **por imagem** |
| `GET /alertas` | Alertas reais mais o item sintético de dispositivo inativo |
| `PATCH /alertas/{id}/lido` | Marca alerta real como lido. 404 em alerta de outro dono |
| `GET /usuarios/me` | Nome, e-mail e papel do produtor logado |
| `GET /dispositivos` | Dispositivos do produtor, com `status` calculado |
| `POST /dispositivos/vincular` | Reivindica um dispositivo pelo código `ECO-XXXX-XXXX` |
| `GET /health` | Sem autenticação, para o UptimeRobot. Responde 503 se o banco falhar, e informa se o modelo de IA está carregado |

## Garantias implementadas que não são óbvias pelo nome da rota

- **Isolamento por dono** em toda consulta
  ([ADR 0010](../docs/decisions/0010-cadastro-aberto-e-rbac.md)): uma
  conta sem dispositivo vinculado vê zero itens, não a tabela toda.
  Confundir "lista vazia" com "sem filtro" entregaria o banco inteiro, e
  há teste para isso (`tests/test_escopo.py`).
- **Anti-enumeração de contas**, inclusive no tempo de resposta
  (`HASH_DESCARTAVEL` em `app/core/security.py`).
- **O código enviado por e-mail nunca aparece em resposta da API** e no
  banco fica só o hash bcrypt dele.
- **Idempotência**: reenvio da mesma captura não duplica linha, devolve
  o diagnóstico existente. Uma corrida entre duas requisições com a
  mesma chave não derruba nenhuma das duas.
- **Alerta ambiental automático** com limiares de fonte citada
  ([ADR 0005](../docs/decisions/0005-limiares-ambientais.md)): nenhum
  número foi inventado no código.
- **Recomendação de manejo por classe**
  ([ADR 0006](../docs/decisions/0006-recomendacoes-por-diagnostico.md)),
  com correlação em texto quando doença e risco ambiental ocorrem no
  mesmo ciclo.
- **Degradação em vez de queda**: sem modelo, a inferência devolve
  placeholder; sem e-mail configurado, a conta nasce verificada. Nos dois
  casos com erro no log.
- Imagem corrompida responde 422, imagem acima de 5MB responde 413, e
  timestamp ou leitura inválidos são recusados **antes** de subir a
  imagem, para não deixar arquivo órfão no bucket.

## Fluxo de dados do `POST /diagnostico`

1. Autentica pela credencial daquele dispositivo (ADR 0009).
2. Se a `idempotency_key` já existe, devolve o diagnóstico existente sem reprocessar.
3. Lê a imagem em memória (`BytesIO`), nunca em disco.
4. Redimensiona para 224x224 com **NEAREST** e roda a inferência TFLite
   com **pixels crus de 0 a 255**. Os dois detalhes são contrato do
   modelo, e errar qualquer um deles produz predição errada **sem erro
   visível** (ver [ADR 0011](../docs/decisions/0011-escopo-de-tres-classes.md)).
5. Sobe a imagem para o Supabase Storage e recebe o caminho.
6. Persiste em `registros_imagem`, `leituras_ambientais`, `diagnosticos` e `alertas`.
7. Descarta o buffer da imagem da RAM.

## Schema do banco (8 tabelas)

Fonte de verdade: `app/db/models.py` (Python) e `infra/supabase/schema.sql`
(mesma coisa em SQL puro, para revisão em grupo). IDs são inteiros
autoincremento, portáveis entre o Postgres real e o SQLite dos testes.

| Tabela | Escrita por | Lida por |
|---|---|---|
| `registros_imagem` | `POST /diagnostico` | consultas do dashboard |
| `leituras_ambientais` | `POST /diagnostico` | `GET /leituras` |
| `diagnosticos` | `POST /diagnostico` | `GET /diagnosticos` |
| `alertas` | `POST /diagnostico` | `GET`/`PATCH /alertas` |
| `usuarios` | `POST /auth/register` | login e `GET /usuarios/me` |
| `dispositivos` | `scripts/provisionar_dispositivo.py` e `POST /dispositivos/vincular` | `GET /dispositivos` e **todo o filtro por dono** |
| `tentativas_login` | login e recuperação | trava de força bruta |
| `codigos_email` | cadastro, reenvio e recuperação | confirmação e redefinição |

`registros_imagem.caminho_arquivo` guarda só o **caminho** dentro do
bucket, não a URL. A escolha entre signed URL e bucket público
(`infra/supabase/storage_policies.md`) foi decidida por **signed URL**,
gerada sob demanda por `GET /diagnosticos`: não é persistida porque
expira.

## Estrutura

```
cloud/
├── app/
│   ├── main.py              # entrypoint FastAPI + Uvicorn (1 worker)
│   ├── config.py            # variáveis de ambiente / settings
│   ├── api/
│   │   ├── escopo.py        # QUEM vê O QUE (filtro por dono)
│   │   ├── dispositivo_auth.py  # credencial do Pi (ADR 0009)
│   │   └── routes/          # endpoints HTTP
│   ├── core/                # JWT/bcrypt, inferência TFLite, regras de
│   │                        # alerta, envio de e-mail
│   ├── db/                  # SQLAlchemy async, modelos, schemas Pydantic
│   └── storage/             # Supabase Storage (upload + signed URL)
├── alembic/                 # migrations do schema Postgres
├── scripts/
│   ├── provisionar_dispositivo.py  # credencial + código de pareamento
│   ├── seed_usuario_teste.py       # conta de teste
│   └── seed_dispositivo_teste.py   # vínculo de dispositivo em teste
├── tests/                   # 121 testes (ver cloud/tests/README.md)
└── requirements.txt
```

`app/api/escopo.py` e `app/api/dispositivo_auth.py` moram em `app/api/`
e não em `app/core/` porque precisam consultar o banco, e **`app/core/`
nunca importa `app/db/`**. Essa camada é intencional: as regras puras
(limiar ambiental, força de senha, decisão de inatividade) são testáveis
sem banco nenhum.

## Regras obrigatórias (não negociáveis)

1. Modelo `.tflite` versionado no GitHub, nunca salvo em volume do Railway.
2. Processamento de imagem 100% em memória: nenhum `open()` de escrita no pipeline de inferência.
3. Logs via `stdout`, nunca em disco.
4. Imagem é sempre gravada no Supabase Storage antes de ser descartada da memória.
5. Instalar apenas `tflite-runtime` ou `ai-edge-litert` em produção,
   **nunca** o pacote `tensorflow` completo (estoura a RAM do Railway).
6. **1 único worker.** O interpretador TFLite é carregado por processo, e
   um segundo worker dobraria o consumo de memória.

## Como rodar localmente

```bash
cd cloud
pip install -r requirements.txt
cp ../infra/env/cloud.env.example .env   # preencher com credenciais reais ou de teste
alembic upgrade head                      # cria o schema no Postgres/DATABASE_URL configurado
python -m scripts.seed_usuario_teste      # conta de teste do produtor
python -m scripts.provisionar_dispositivo pi-estufa-01 "Estufa 1"  # credencial + código
uvicorn app.main:app --reload
```

Sem um `.tflite` em `TFLITE_MODEL_PATH`, a API sobe normalmente e
`/diagnostico` devolve resultado placeholder (ver `app/core/inference.py`).

Rodar os testes: `pytest -q` dentro de `cloud/`. A suíte **nunca envia
e-mail de verdade**: `tests/conftest.py` força as variáveis de e-mail
como vazias antes de qualquer teste
([ADR 0013](../docs/decisions/0013-email-transacional-brevo.md)).

## Pendências

- Remover o ramo de transição da chave global em
  `app/api/dispositivo_auth.py` depois que todos os Pis estiverem
  provisionados. Os avisos no log dizem se ainda falta algum.
- Push de servidor não existe, por decisão registrada
  ([ADR 0012](../docs/decisions/0012-notificacao-local-sem-push.md)).
- Recalibrar o limiar de umidade do solo
  (`app/core/alertas_ambientais.py`) assim que o sensor físico estiver
  calibrado de verdade, ver
  [ADR 0005](../docs/decisions/0005-limiares-ambientais.md).
- O fluxo de pareamento nunca foi exercitado por uma pessoa de verdade
  no app, só por teste automatizado.
