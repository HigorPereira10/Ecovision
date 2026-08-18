# infra: Automação, Deploy e Configuração de Ambiente

Referência arquitetural: **Tech Stack Blueprint Consolidado v3.0, Fase 4
(Nuvem, Backend e Banco de Dados)**, especialmente as Seções 4.4 (regras
obrigatórias do Railway), 4.5 (risco de timing dos trials) e 4.6
(calendário de sincronização).

## Papel desta camada

Concentra tudo que configura *como* o sistema é implantado e mantido,
sem conter lógica de aplicação:

- Configuração de deploy do backend no **Railway**.
- Schema e políticas de bucket do **Supabase** (Postgres + Storage).
- Templates de variáveis de ambiente (`.env.example`) para `cloud/` e `edge/`.
- Notas de monitoramento (UptimeRobot, para evitar a pausa por
  inatividade do Supabase).
- Calendário de sincronização entre a ativação do trial do Railway e a
  data real da banca (Blueprint Seção 4.6).

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
    └── sincronizacao.md        # espelho da tabela da Seção 4.6, a preencher com datas reais
```

O workflow de CI/CD (GitHub Actions) precisa, por exigência técnica do
GitHub, morar em `.github/workflows/` na raiz do repositório, não
dentro de `infra/`. Ver `.github/workflows/deploy-railway.yml` (esqueleto)
e a nota em `infra/railway/README.md`.

## Riscos e regras que esta camada precisa refletir (Blueprint)

- **Zero gravação em disco no Railway**: reforçado aqui como restrição
  de infraestrutura, não só de código (Seção 4.4).
- **Trial do Railway expira 30 dias corridos após ativação** — não são
  30 dias de uso. Sincronizar com a data real da banca (Seção 4.5/4.6).
  Reservar ~R$30-50 para o plano Hobby como contingência.
- **Supabase pausa após 7 dias de inatividade** — mitigar com ping
  periódico via UptimeRobot, configurado já na Sprint 6.

## Pendências de grupo

- Datas reais do calendário de sincronização (`infra/calendar/sincronizacao.md`)
  — dependem da data da banca, ainda não confirmada pela coordenação.
- Schema fino das tabelas em `infra/supabase/schema.sql` (mesma pendência
  de `cloud/app/db/models.py`).

## Planejamento relacionado

A explicação completa da estratégia Supabase × Railway (o que pode ser
feito já vs. o que é deliberadamente adiado) está registrada em
[`docs/planejamento/divisao-equipe-e-roadmap.md`](../docs/planejamento/divisao-equipe-e-roadmap.md#5-supabase--railway--por-que-a-estratégia-de-ativação-é-diferente).
