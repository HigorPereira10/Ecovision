# ADR 0002 — Framework de frontend (Expo × React PWA × Streamlit)

**Status:** ⚠️ **PENDENTE — decisão oficial do grupo ainda não tomada.**

## Contexto (Tech Stack Blueprint v3.0, Fase 5)

Esta é a decisão de maior risco de cronograma do projeto, porque pode
envolver trocar de linguagem de programação (Python → JavaScript/TypeScript)
sob prazo fixo. O Blueprint não fecha uma escolha única, define o
critério de decisão e exige que ela seja tomada **antes da Sprint 1**.


### Comparativo (resumo: ver Blueprint Seção 5 para a tabela completa)

| Critério | Expo (RN) | React PWA | Streamlit |
|---|---|---|---|
| Linguagem | JS/TS | JS/TS | Python |
| Resultado | App mobile real | Site responsivo | Painel web |
| Push notifications nativas | Sim | Não | Não |
| Risco técnico | Médio-Alto se time não conhece RN | Baixo | Muito baixo |

## Decisão de scaffolding tomada NESTA reestruturação de repositório

Por instrução explícita do responsável pelo repositório, a pasta `app/`
foi estruturada **como se Expo (React Native) já tivesse sido escolhido**
— isso é uma conveniência de andaime (scaffolding) para não deixar a
pasta vazia, **não é a decisão final do grupo**. Todo arquivo dentro de
`app/` traz esse aviso no cabeçalho. Se o grupo decidir por PWA ou
Streamlit, a estrutura interna de `app/src/` deve ser refeita, a
decisão continua em aberto.

## Consequências se a decisão não for tomada a tempo

Início do frontend atrasa ou, pior, começa em Expo e precisa ser
refeito do zero em outra stack já dentro do cronograma apertado da
Sprint 7, sem tempo de recuperação (Blueprint, Pontos de Atenção).
