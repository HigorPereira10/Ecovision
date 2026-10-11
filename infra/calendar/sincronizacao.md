# Calendário de sincronização: Railway × Supabase × Banca

> **O risco que este documento existia para controlar DESAPARECEU.**
>
> A versão anterior girava em torno da janela de 30 dias do trial
> gratuito do Railway: a preocupação era que a coleta de campo e a banca
> caíssem dentro dela, senão a API pararia de responder no pior momento.
>
> O trial venceu e o grupo **assinou o plano Hobby** (5 dólares por mês),
> em 2026-10-10. Não existe mais janela de 30 dias para sincronizar, e a
> API fica no ar enquanto a assinatura estiver ativa
> ([ADR 0014](../../docs/decisions/0014-deploy-railway-e-gate-de-ci.md)).

## O que ainda precisa de controle de data

| Marco | Regra | Status |
|---|---|---|
| Assinatura do Railway ativa | Cartão válido e sem falha de cobrança até **depois** da banca | ✅ Ativa. Conferir a cobrança no mês da apresentação |
| Supabase sem pausa por inatividade | O projeto gratuito pausa após cerca de 7 dias sem nenhuma requisição | ✅ Mitigado: UptimeRobot pinga `GET /health` |
| Coleta de campo (validação do modelo com foto real) | Precisa de captura ligada no Pi, hoje desativada pelo ajuste de fiação | ⏳ Depende do hardware |
| Data da banca | Depende da coordenação do curso | ⏳ A DEFINIR |

## Os dois riscos reais que sobraram

**1. Falha de cobrança no Railway.** Com plano pago, o modo de falhar
deixou de ser "o trial venceu" e passou a ser "o cartão recusou". O
efeito é o mesmo: API fora do ar. Conferir o status da assinatura na
semana da banca, não no dia.

**2. Supabase pausado por inatividade.** O projeto gratuito pausa depois
de cerca de 7 dias sem requisição, e reativar leva alguns minutos. Numa
apresentação, alguns minutos são fatais. O UptimeRobot pingando
`GET /health` resolve isso, **desde que esteja configurado e
funcionando**: conferir que o monitor está verde, e não apenas que foi
criado algum dia. Ver
[`infra/monitoring/uptimerobot.md`](../monitoring/uptimerobot.md).

## Recomendação para o dia da banca

Fazer um teste de ponta a ponta na véspera, não na hora: abrir o
aplicativo, entrar, e conferir que as telas carregam. Isso exercita
API, banco e Storage de uma vez, e dá tempo de reagir se algo estiver
pausado ou expirado.
