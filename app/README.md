# app — Frontend / Aplicativo

> ✅ **Framework definido: Expo (React Native).** Decisão confirmada
> pelo grupo — ver [ADR 0002](../docs/decisions/0002-frontend-framework-pendente.md).
> A estrutura abaixo, que já existia como scaffolding desde a
> reestruturação inicial do repositório, é agora a definitiva.
>
> **Responsável pela camada:** Amanda. **Apoio nas primeiras semanas:**
> Igor, em tarefas combinadas diretamente com ela (ver
> [`docs/planejamento/divisao-equipe-e-roadmap.md`](../docs/planejamento/divisao-equipe-e-roadmap.md)).

## Papel desta camada

Referência: **Tech Stack Blueprint v3.0, Fase 5**.

- Dashboard/app usado pelo produtor rural: alertas, diagnóstico (com a
  imagem vinda do Supabase Storage via API), histórico, financeiro (mock).
- Autenticação do produtor via JWT (login) + refresh token, consumindo
  os endpoints do FastAPI (`cloud/app/api/routes/auth.py`).
- **Nunca** acessa o Supabase diretamente, sempre via API no Railway
  (Blueprint Seção 4.2, passo 5).

## Estrutura (Expo/React Native)

```
app/
└── src/
    ├── screens/          # Alertas, Diagnóstico, Histórico, Financeiro (mock), Login
    ├── navigation/        # React Navigation
    ├── services/          # cliente HTTP (JWT) e lógica de autenticação
    ├── components/charts/ # Victory Native (gráficos)
    └── notifications/     # Expo Notifications (push nativo)
```

> Nota: os cabeçalhos dos arquivos em `app/src/` ainda podem trazer o
> aviso "decisão de framework pendente" escrito antes desta confirmação
> — está desatualizado, a decisão é Expo/React Native (ver ADR 0002).
