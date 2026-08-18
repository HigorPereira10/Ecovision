# docs — Documentação Técnica e Acadêmica

Centraliza a documentação que não é código: referência arquitetural,
decisões registradas, atas de reunião e a escrita acadêmica do TCC.

## Estrutura

```
docs/
├── architecture/
│   └── blueprint-reference.md   # ponteiro para o Tech Stack Blueprint v3.0 (fonte única de verdade técnica)
├── decisions/                   # ADRs: Architecture Decision Records
│   ├── 0001-camera-module-3.md
│   ├── 0002-frontend-framework-pendente.md  # decisão final: Expo (React Native)
│   ├── 0003-autenticacao-dual.md
│   └── 0004-divisao-equipe-final.md
├── planejamento/                # divisão de equipe, roadmap, lista de compras
│   ├── divisao-equipe-e-roadmap.md
│   ├── lista-compras-hardware.md
│   └── responsabilidades-documentacao-igor.md
├── atas/                        # atas de reunião do grupo
└── tcc/                         # capítulos da escrita acadêmica do TCC
```

## Sobre o Tech Stack Blueprint

O documento **"EcoVision — Tech Stack Blueprint Consolidado, TC2, v3.0"**
é a fonte única de verdade arquitetural do projeto (substitui o TC1 em
decisões técnicas). Ele não foi duplicado neste repositório, mantém-se
na pasta compartilhada do grupo (Google Drive, ver link no README raiz).
`docs/architecture/blueprint-reference.md` traz um resumo de navegação
por seção, para uso rápido durante o desenvolvimento.

## ADRs (`docs/decisions/`)

Registram decisões arquiteturais que já foram tomadas, com o motivo,
incluindo as que ainda estão **pendentes** de fechamento pelo grupo,
para que fiquem visíveis e não se percam entre conversas.

## Planejamento (`docs/planejamento/`)

A divisão de equipe final está registrada em
[ADR 0004](decisions/0004-divisao-equipe-final.md): João em `ml/`,
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
