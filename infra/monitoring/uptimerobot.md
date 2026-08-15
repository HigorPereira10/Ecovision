# UptimeRobot: ping de manutenção do Supabase

O free tier do Supabase pausa automaticamente o projeto após 7 dias de
inatividade (Blueprint v3.0, Seção 4.5). Mitigação: ping periódico via
UptimeRobot, já previsto desde o Blueprint v2.0.

## TODO de configuração

- Criar um monitor HTTP(S) apontando para um endpoint leve da API
  (ex.: um `GET /health` a implementar em `cloud/app/main.py`), com
  intervalo bem menor que 7 dias (ex.: a cada poucas horas).
- Configurar **na Sprint 6**, não deixar para depois (Blueprint, Pontos
  de Atenção).
- Isso mantém tanto o Railway quanto, indiretamente (via chamadas da
  API ao banco), o Supabase ativos.
