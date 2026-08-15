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
│   ├── 0002-frontend-framework-pendente.md
│   └── 0003-autenticacao-dual.md
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
