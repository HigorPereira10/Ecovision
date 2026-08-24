# ADR 0001 — Camera Module 3 (não V2)

**Status:** Decidido e confirmado (Tech Stack Blueprint v3.0, Fase 1).

## Contexto

O TC1 original especificava a Camera Module V2 (8MP, foco fixo ~1m).

## Decisão

Usar a **Camera Module 3** (IMX708, 12MP, autofoco PDAF de 5cm ao infinito).

## Motivo

A distância de operação do EcoVision é de ~15cm (câmera + flash
dominante). Com foco fixo em 1m, as folhas ficariam sistematicamente
fora de foco, blur não é corrigível por data augmentation depois. Isso
inutilizaria as imagens reais coletadas em campo, que são o principal
diferencial acadêmico do trabalho (validação com dados reais do Pi).

## Consequências

- ~~Requer cabo FFC específico para o conector CSI de 22 pinos do Pi
  Zero (a Camera V3 vem com cabo para Pi 4, adaptador necessário).~~
  **Atualizado (ver [ADR 0004](0004-raspberry-pi-3b-plus.md)):** o
  hardware de borda passou a ser o Raspberry Pi 3 Model B+, que usa o
  conector CSI padrão de 15 pinos (mesmo do Pi 4) — o cabo que já
  acompanha a Camera Module 3 serve diretamente, sem adaptador.
- **Ação pendente:** revisar o texto do TC1 (Tabela 2 e Seção 5.3.1) para
  remover toda menção à V2/8MP.
