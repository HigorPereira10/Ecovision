# cloud — Backend / API (Railway + Supabase)

Camada de backend do EcoVision. Referência arquitetural completa: **Tech Stack Blueprint Consolidado v3.0, Fase 4 (Nuvem, Backend e Banco de Dados)**.

## Papel desta camada

- Hospeda a API FastAPI que roda no **Railway** (PaaS — só executa código, não persiste nada).
- Carrega o modelo `.tflite` em memória (TFLite Runtime) e roda a inferência sobre as imagens recebidas do Raspberry Pi.
- Processa tudo em memória via `BytesIO` — **zero gravação em disco no container** (Blueprint, Seção 4.4, regras 1-4).
- Fala com o **Supabase** (Postgres + Storage) para persistir dados estruturados e imagens. O Supabase nunca é acessado diretamente pelo frontend — sempre através desta API.
- Implementa as duas pontas de autenticação decididas no Blueprint (Seção 4.3):
  - **API Key estática** para o dispositivo IoT (Raspberry Pi → API).
  - **JWT de curta duração (24h) + refresh token (30 dias) + bcrypt** para o login do produtor no dashboard.

## Fluxo de dados que esta camada implementa (Blueprint, Seção 4.2)

1. Recebe `POST /diagnostico` do Pi (imagem + leituras de sensores), autenticado via API Key.
2. Roda a inferência TFLite em memória (resize 224×224, normalização).
3. Grava a imagem no **Supabase Storage** (bucket `ecovision-imagens`) e recebe a URL.
4. Grava URL + diagnóstico + leituras nas tabelas do **Supabase Postgres**.
5. Descarta o buffer da imagem da RAM.
6. Serve o dashboard/app através de endpoints autenticados via JWT, nunca expondo o Supabase diretamente.

## Estrutura

```
cloud/
├── app/
│   ├── main.py              # entrypoint FastAPI + Uvicorn (1 worker)
│   ├── config.py            # variáveis de ambiente / settings
│   ├── api/routes/          # endpoints HTTP
│   ├── core/                # segurança (API Key, JWT, bcrypt) e inferência TFLite
│   ├── db/                  # SQLAlchemy async, modelos, schemas Pydantic
│   └── storage/             # integração com Supabase Storage
├── alembic/                 # migrations do schema Postgres
├── tests/
└── requirements.txt
```

## Regras obrigatórias (não negociáveis — Blueprint Seção 4.4)

1. Modelo `.tflite` versionado no GitHub, nunca salvo em volume do Railway.
2. Processamento de imagem 100% em memória — nenhum `open()` de escrita no pipeline de inferência.
3. Logs via `stdout` — nunca em disco.
4. Imagem é sempre gravada no Supabase Storage antes de ser descartada da memória.
5. Instalar apenas `tflite-runtime` em produção — **nunca** o pacote `tensorflow` completo (estoura a RAM do Railway).

## Pendências de grupo

- Schema exato das tabelas (`registros_imagem`, `leituras_ambientais`, `diagnosticos`, `alertas`, e as de usuário/dispositivo/RBAC) ainda precisa de definição fina de colunas — ver `infra/supabase/schema.sql`, que traz um esqueleto com os nomes já citados no Blueprint e `TODO`s para o restante.
