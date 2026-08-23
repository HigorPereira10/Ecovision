# cloud/alembic

Migrations do schema Postgres (Supabase), geradas a partir de
`cloud/app/db/models.py`.

**Status:** inicializado. `env.py` lê a URL do banco de
`app.config.settings.DATABASE_URL` (não de `alembic.ini`) e usa a
`MetaData` real de `app/db/models.py`, então `alembic revision
--autogenerate` já funciona a partir daqui.

A migration `0001_schema_inicial.py` foi escrita à mão (sem
`--autogenerate`, sem conexão real com um Postgres disponível no
momento) espelhando `app/db/models.py` — as 6 tabelas do schema
combinado (ver `cloud/README.md`), mas só `registros_imagem`,
`leituras_ambientais` e `diagnosticos` são de fato usadas nesta rodada.

## Como rodar contra um Postgres real

```bash
cd cloud
# com DATABASE_URL configurado (.env ou variável de ambiente)
alembic upgrade head
```

## Como gerar a próxima migration (quando o schema mudar)

```bash
cd cloud
alembic revision --autogenerate -m "descricao da mudanca"
```
