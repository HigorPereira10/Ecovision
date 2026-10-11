# infra: Automação, Deploy e Configuração de Ambiente

Referência arquitetural: [**Blueprint v4.0**](../docs/architecture/blueprint-v4.md),
seções 4 e 9.

> **ESTADO (2026-10-11):** tudo nesta camada está aplicado e no ar. API
> em `https://ecovision-production.up.railway.app`, plano **Hobby**
> contratado, schema aplicado no Supabase real, monitor do UptimeRobot
> configurado, e deploy publicando só depois de a CI passar
> ([ADR 0014](../docs/decisions/0014-deploy-railway-e-gate-de-ci.md)).

## Papel desta camada

Concentra tudo que configura *como* o sistema é implantado e mantido,
sem conter lógica de aplicação:

- Configuração de deploy do backend no **Railway**.
- Schema e políticas de bucket do **Supabase** (Postgres + Storage).
- Templates de variáveis de ambiente (`.env.example`) para `cloud/` e `edge/`.
- Notas de monitoramento (UptimeRobot, para evitar a pausa por
  inatividade do Supabase).
- Calendário de sincronização com a data da banca. O risco mudou de
  natureza: não é mais a janela de 30 dias do trial, é manter a
  assinatura paga ativa e o Supabase sem pausar
  ([`calendar/sincronizacao.md`](calendar/sincronizacao.md)).

## Estrutura

```
infra/
├── supabase/
│   ├── schema.sql              # esqueleto do schema Postgres (tabelas já citadas no Blueprint)
│   └── storage_policies.md     # notas sobre o bucket "ecovision-imagens"
├── railway/
│   └── README.md               # notas de configuração do serviço no Railway
├── env/
│   ├── cloud.env.example
│   └── edge.env.example
├── monitoring/
│   └── uptimerobot.md
└── calendar/
    └── sincronizacao.md        # riscos de data que ainda importam
```

O workflow de CI/CD (GitHub Actions) precisa, por exigência técnica do
GitHub, morar em `.github/workflows/` na raiz do repositório, não
dentro de `infra/`. Ver `.github/workflows/deploy-railway.yml` (esqueleto)
e a nota em `infra/railway/README.md`.

## Riscos e regras que esta camada precisa refletir

- **Zero gravação em disco no Railway**: restrição de infraestrutura,
  não só de código. O plano não tem volume persistente.
- **Nenhum root directory no serviço do Railway.** Apontar o serviço
  para `cloud/` faria o Railway baixar só aquela pasta, e `ml/models/`
  desapareceria do container: a API subiria sem modelo e devolveria
  placeholder em toda captura, **sem erro visível**. Daí o
  `requirements.txt` na raiz e o start command que entra na pasta certa.
- **Supabase pausa após cerca de 7 dias de inatividade**: mitigado por
  ping periódico do UptimeRobot em `GET /health`. Conferir que o monitor
  está verde antes da banca, não apenas que existe.
- **Portas de SMTP bloqueadas no plano Hobby** (25, 465, 587, 2525):
  e-mail sai pela API HTTP do Brevo, porta 443
  ([ADR 0013](../docs/decisions/0013-email-transacional-brevo.md)).

## Decisões que estavam pendentes e foram fechadas

- ~~signed URL contra bucket público~~: **signed URL**, bucket privado,
  gerada sob demanda e não persistida
  ([`supabase/storage_policies.md`](supabase/storage_policies.md)).
- ~~Ativação do Railway e monitor do UptimeRobot~~: feitos.
- ~~Momento de contratar plano pago~~: Hobby contratado em 2026-10-10.

## Pendências de grupo

- Data da banca, que ainda depende da coordenação do curso. É o único
  campo "A DEFINIR" que sobrou em
  [`calendar/sincronizacao.md`](calendar/sincronizacao.md).
- Conferir a cobrança da assinatura do Railway na semana da
  apresentação: com plano pago, o modo de falhar deixou de ser "o trial
  venceu" e passou a ser "o cartão recusou".

## Planejamento relacionado

A explicação completa da estratégia Supabase × Railway (o que pode ser
feito já vs. o que é deliberadamente adiado) está registrada em
[`docs/planejamento/divisao-equipe-e-roadmap.md`](../docs/planejamento/divisao-equipe-e-roadmap.md#5-supabase--railway--por-que-a-estratégia-de-ativação-é-diferente).
