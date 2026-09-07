# ADR 0002: Framework de frontend: Expo (React Native)

**Status:** ✅ **Decidido.** O grupo confirmou Expo (React Native) como
framework do `app/`. React PWA e Streamlit não serão usados.

> Nota: o nome do arquivo manteve o sufixo `-pendente` para não quebrar
> os links já existentes no repositório (README raiz, outros READMEs,
> cabeçalhos dos arquivos em `app/src/`). O conteúdo abaixo reflete a
> decisão final, não mais uma pendência.

## Contexto (Tech Stack Blueprint v3.0, Fase 5)

Esta era a decisão de maior risco de cronograma do projeto, porque
poderia envolver trocar de linguagem de programação (Python →
JavaScript/TypeScript) sob prazo fixo. O Blueprint não fechava uma
escolha única: definia o critério de decisão (a pergunta de confiança
em Expo/React Native) e exigia que o grupo decidisse antes da Sprint 1.

### Comparativo que embasou a decisão (ver Blueprint Seção 5 para a tabela completa)

| Critério | Expo (RN) | React PWA | Streamlit |
|---|---|---|---|
| Linguagem | JS/TS | JS/TS | Python |
| Resultado | App mobile real | Site responsivo | Painel web |
| Push notifications nativas | Sim | Não | Não |
| Risco técnico | Médio-Alto se time não conhece RN | Baixo | Muito baixo |

## Decisão

O grupo confirmou **Expo (React Native)**. A pasta `app/` já estava
estruturada dessa forma desde a reestruturação inicial do repositório
(como scaffolding, na época sem decisão fechada), e essa estrutura
**passa a ser definitiva**, não mais um placeholder.

Amanda é a responsável técnica pela camada `app/`; Igor a apoia nas
primeiras semanas em tarefas de frontend combinadas diretamente com ela
(ver [`docs/planejamento/divisao-equipe-e-roadmap.md`](../planejamento/divisao-equipe-e-roadmap.md)
para a divisão de equipe completa).

## Consequências

- Os avisos de "decisão pendente" nos cabeçalhos de `app/src/*` e em
  `app/README.md` estão desatualizados e devem ser lidos como
  históricos: a estrutura Expo é a definitiva.
- Push notifications nativas (Expo Notifications) seguem viáveis como
  planejado no Blueprint, já que PWA/Streamlit (que não as suportam)
  foram descartados.
- Nenhum retrabalho de framework é esperado a partir de agora: o app
  segue em JavaScript/TypeScript, com Victory Native para gráficos e
  React Navigation.
