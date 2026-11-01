# docs: Documentação Técnica e Acadêmica

Centraliza a documentação que não é código: referência arquitetural,
decisões registradas, atas de reunião e a escrita acadêmica do TCC.

## Estrutura

```
docs/
├── architecture/
│   ├── blueprint-v4.md          # DOCUMENTO PRINCIPAL: o sistema como ele é
│   ├── blueprint-reference.md   # índice do Blueprint v3.0 (histórico) + diagrama
│   └── diagramas/               # arquitetura em camadas (png + svg editável)
├── decisions/                   # ADRs, 17 decisões (ver decisions/README.md)
├── planejamento/                # divisão de equipe, roadmap, lista de compras
└── tcc/                         # capítulos da escrita acadêmica do TCC
```

## Qual documento ler

**[`architecture/blueprint-v4.md`](architecture/blueprint-v4.md)** é o
documento de consulta do projeto. Ele descreve o sistema **como ele é**,
implantado, e vive dentro do repositório justamente para envelhecer
junto com o código.

O **"Tech Stack Blueprint Consolidado, TC2, v3.0"** continua na pasta
compartilhada do grupo e descreve o sistema **como foi planejado**. Ele
segue valendo como registro histórico e como referência das fases de
execução. Três premissas dele caíram em contato com a realidade, e a
seção 0 do v4.0 lista quais, por quê, e em qual ADR cada queda está
registrada.

Onde os dois divergirem, vale o v4.0.

## ADRs (`docs/decisions/`)

Registram decisões arquiteturais com o motivo e o que foi descartado.
Índice organizado por tema em
[`decisions/README.md`](decisions/README.md).

Regra que vale para esta pasta: **decisão superada não é apagada.** Ela
recebe nota de status apontando para a substituta. O
[ADR 0003](decisions/0003-autenticacao-dual.md) é o exemplo, e o motivo
de ele ter caducado é em si um bom argumento de banca, porque mostra uma
premissa sendo revista por evidência.

## Planejamento (`docs/planejamento/`)

A divisão de equipe final está registrada em
[ADR 0007](decisions/0007-divisao-equipe-final.md): João em `ml/`,
Amanda em `app/`, Higor em `cloud/`+`infra/`+`edge/`, Igor na
documentação do projeto (+ apoio à Amanda no `app/` nas primeiras
semanas).

- [`divisao-equipe-e-roadmap.md`](planejamento/divisao-equipe-e-roadmap.md):
  decisões pendentes por urgência, o raciocínio por trás da divisão
  final (histórico das propostas avaliadas), cronograma passo a passo
  por pessoa, e a explicação da estratégia Supabase × Railway.
- [`lista-compras-hardware.md`](planejamento/lista-compras-hardware.md):
  espelho local da tabela de compras (BoM) do Blueprint, para o grupo
  cotar e marcar status.
- [`responsabilidades-documentacao-igor.md`](planejamento/responsabilidades-documentacao-igor.md):
  detalhamento prático do papel de documentação (Drive, Figma, atas,
  ADRs, reuniões).
