# app — Frontend / Aplicativo

> ⚠️ **DECISÃO DE FRAMEWORK AINDA PENDENTE.**
> Ainda não foi definido entre (React Native), React PWA ou Streamlit
>
> Esta pasta foi estruturada **pensando que Expo/React Native foi a decisão
> escolhido**, por decisão explícita de scaffolding (não é a decisão
> final do grupo, ver `docs/decisions/0002-frontend-framework-pendente.md`).
> Se o grupo optar por React PWA ou Streamlit, toda a estrutura abaixo
> precisa ser refeita antes de qualquer implementação real.

## Papel desta camada (independente do framework escolhido)

Referência: **Tech Stack Blueprint v3.0, Fase 5**.

- Dashboard/app usado pelo produtor rural: alertas, diagnóstico (com a
  imagem vinda do Supabase Storage via API), histórico, financeiro (mock).
- Autenticação do produtor via JWT (login) + refresh token, consumindo
  os endpoints do FastAPI (`cloud/app/api/routes/auth.py`).
- **Nunca** acessa o Supabase diretamente, sempre via API no Railway
  (Blueprint Seção 4.2, passo 5). Trocar o framework de UI não deve
  exigir mudanças no backend.

## Estrutura (esqueleto Expo/React Native — ver aviso acima)

```
app/
└── src/
    ├── screens/          # Alertas, Diagnóstico, Histórico, Financeiro (mock), Login
    ├── navigation/        # React Navigation
    ├── services/          # cliente HTTP (JWT) e lógica de autenticação
    ├── components/charts/ # Victory Native (gráficos)
    └── notifications/     # Expo Notifications (push nativo)
```
