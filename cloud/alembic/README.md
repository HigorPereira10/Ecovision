# cloud/alembic

Diretório reservado para as migrations do schema Postgres (Supabase),
geradas a partir dos modelos em `cloud/app/db/models.py`.

Ainda não inicializado (`alembic init`) porque o schema fino das tabelas
(colunas, tipos, relacionamentos) depende de decisão de grupo, ver os
`TODO`s em `cloud/app/db/models.py` e o esqueleto espelho em
`infra/supabase/schema.sql`.

Quando o schema for fechado:
1. Rodar `alembic init alembic` (ou equivalente) neste diretório.
2. Apontar `sqlalchemy.url` para `DATABASE_URL` (`cloud/app/config.py`).
3. Gerar a migration inicial a partir de `cloud/app/db/models.py`.
