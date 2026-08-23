# Railway: configuração do serviço

Notas de configuração do deploy do `cloud/` no Railway.app (Blueprint
v3.0, Fase 4). Este diretório documenta a configuração; não contém
segredos nem valores reais.

## O que roda no Railway (Blueprint Seção 4.1)

- FastAPI + Uvicorn com **1 worker apenas** + TFLite Runtime carregado em
  memória.
- Nada de dado de negócio, nenhuma imagem, nenhum log em disco, tudo
  isso fica no Supabase (ver `infra/supabase/`) ou é enviado via `stdout`.

## Configuração (a fazer no painel do Railway)

- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`
  (raiz do serviço apontando para `cloud/`; `$PORT` é injetado pelo
  próprio Railway, não fixar um valor).
- Root directory do serviço: `cloud/` (é onde ficam `app/`,
  `requirements.txt` e `alembic/`).
- Variáveis de ambiente: usar o template `infra/env/cloud.env.example`
  (preencher com os valores reais do Supabase e a `DEVICE_API_KEY`
  gerada — nunca commitar esses valores).
- Migração do banco: rodar `alembic upgrade head` (de dentro de
  `cloud/`) antes de subir uma versão nova, ou como um passo de deploy
  automatizado — as migrations em `cloud/alembic/versions/` já cobrem
  o schema atual (`registros_imagem`, `leituras_ambientais`,
  `diagnosticos`, `alertas`, `usuarios`, `dispositivos`).
- Deploy automático via GitHub Actions a cada push na `main`, ver
  `.github/workflows/deploy-railway.yml` (ainda `workflow_dispatch`
  manual de propósito — ativação adiada para perto da Sprint 9).

## Risco de timing (Blueprint Seção 4.5)

O free trial dura **30 dias corridos a partir da ativação**, não 30 dias
de uso. Ver `infra/calendar/sincronizacao.md` para o calendário que
sincroniza a ativação do trial com a data real da banca, **não ativar
o trial cedo demais**. Reservar ~R$30-50 do orçamento do grupo para o
plano Hobby (~US$5/mês) como contingência caso o trial expire antes da
apresentação.
