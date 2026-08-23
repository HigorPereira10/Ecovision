# ADR 0004 — Troca de hardware: Raspberry Pi 3 Model B+ (Anatel) no lugar do Pi Zero 2 W

**Status:** Decidido.

> ⚠️ Numeração: nesta branch (`feature/edge-software-de-borda`) este é o
> ADR 0004. Há também um `docs/decisions/0004-divisao-equipe-final.md`
> criado em paralelo na `main` (divisão de equipe, assunto não
> relacionado) — ao fazer o merge das duas branches, um dos dois
> arquivos precisa ser renumerado para 0005 para não colidir.

## Contexto

O Tech Stack Blueprint v3.0 (documento externo, fonte técnica deste
repositório) especifica o Raspberry Pi Zero 2 W como hardware de borda.
O grupo decidiu usar, na prática, o **Raspberry Pi 3 Model B+** (versão
homologada Anatel) em vez do Zero 2 W.

## Decisão

Hardware de borda: **Raspberry Pi 3 Model B+ (Anatel)**, Raspberry Pi OS
Lite **64-bit** (mantém a mesma exigência técnica do Blueprint para
Picamera2/libcamera).

## Motivo

Decisão do grupo — possivelmente disponibilidade/custo do Pi 3B+ frente
ao Zero 2 W, e a exigência de homologação Anatel para o rádio Wi-Fi/BT
embarcado ao usar o hardware no Brasil. (Registrar aqui o motivo
específico do grupo, se for além de disponibilidade.)

## Consequências técnicas

- **Conector de câmera:** o Pi 3B+ usa o conector CSI **padrão de 15
  pinos** (o mesmo do Pi 4), diferente do conector mini de 22 pinos do
  Pi Zero. O cabo que já acompanha a Camera Module 3 deve servir
  diretamente — o item "cabo FFC adaptador" que estava na lista de
  compras por causa do Pi Zero **não é mais necessário**. Ver correção
  em [ADR 0001](0001-camera-module-3.md) e `edge/README.md`.
- **GPIO:** o Pi 3B+ tem o mesmo header físico de 40 pinos, mesma
  numeração BCM — os defaults de `edge/src/config.py`
  (`LED_MOSFET_PIN=18`, `DHT22_PIN=4`) continuam válidos sem alteração.
- **CPU/RAM:** Pi 3B+ (quad-core Cortex-A53 @1.4GHz, 1GB RAM) é mais
  potente que o Zero 2 W (quad-core @1GHz, 512MB RAM) — não muda a
  decisão arquitetural de que **nenhuma inferência de IA roda na
  borda** (Blueprint, Fase 2); a folga extra de RAM/CPU é apenas
  margem de segurança para captura/compressão/fila.
- **Alimentação:** mesmo conector Micro-USB, mesma recomendação de
  fonte 5V/3A do Blueprint (o Pi 3B+ exige oficialmente 5V/2.5A mínimo,
  já coberto).
- **Dissipador/case:** confirmar compatibilidade física do dissipador e
  da case 3D com o formato do Pi 3B+ (dimensões e posição dos
  conectores diferem do Zero 2 W) antes de fechar o design da case
  (Semana 4-5 do BoM).

## Pendências

- Atualizar a lista de compras (`docs/planejamento/lista-compras-hardware.md`,
  presente na `main`) removendo o item do cabo FFC adaptador e
  revisando o item do dissipador/case para o formato do Pi 3B+.
- Confirmar se a versão Anatel do Pi 3B+ tem alguma particularidade de
  firmware/regulatória relevante para o projeto (normalmente não,
  apenas homologação do rádio).
