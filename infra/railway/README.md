# Railway: configuração do serviço

Notas de configuração do deploy do `cloud/` no Railway.app (Blueprint
v3.0, Fase 4). Este diretório documenta a configuração; não contém
segredos nem valores reais.

## O que roda no Railway (Blueprint Seção 4.1)

- FastAPI + Uvicorn com **1 worker apenas** + TFLite Runtime carregado em
  memória.
- Nada de dado de negócio, nenhuma imagem, nenhum log em disco, tudo
  isso fica no Supabase (ver `infra/supabase/`) ou é enviado via `stdout`.

## TODO de configuração (a fazer no painel do Railway)

- Start command: TODO (ex.: `uvicorn app.main:app --workers 1 ...`,
  definir junto com `cloud/app/main.py`).
- Variáveis de ambiente: usar o template `infra/env/cloud.env.example`.
- Deploy automático via GitHub Actions a cada push na `main`, ver
  `.github/workflows/deploy-railway.yml`.

## Risco de timing (Blueprint Seção 4.5)

O free trial dura **30 dias corridos a partir da ativação**, não 30 dias
de uso. Ver `infra/calendar/sincronizacao.md` para o calendário que
sincroniza a ativação do trial com a data real da banca, **não ativar
o trial cedo demais**. Reservar ~R$30-50 do orçamento do grupo para o
plano Hobby (~US$5/mês) como contingência caso o trial expire antes da
apresentação.
