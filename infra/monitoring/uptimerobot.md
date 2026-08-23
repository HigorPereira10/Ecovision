# UptimeRobot: ping de manutenção do Supabase

O free tier do Supabase pausa automaticamente o projeto após 7 dias de
inatividade (Blueprint v3.0, Seção 4.5). Mitigação: ping periódico via
UptimeRobot, já previsto desde o Blueprint v2.0.

## TODO de configuração

- `GET /health` já está implementado em `cloud/app/main.py` — faz um
  `SELECT 1` no banco (Supabase) e devolve `200 {"status": "ok", "banco": "ok"}`
  ou `503 {"status": "erro", "banco": "indisponivel"}` se a consulta
  falhar. Não exige API Key.
- Criar um monitor HTTP(S) no UptimeRobot apontando para
  `https://<host-do-railway>/health`, com intervalo bem menor que 7
  dias (ex.: a cada 5-30 minutos) — só dá pra configurar de verdade
  depois que o serviço estiver no ar no Railway (pendência ligada à
  ativação do trial, ver `infra/calendar/sincronizacao.md`).
- Configurar assim que o deploy subir, não deixar para depois
  (Blueprint, Pontos de Atenção).
- Isso mantém tanto o Railway quanto, indiretamente (via chamadas da
  API ao banco), o Supabase ativos.
