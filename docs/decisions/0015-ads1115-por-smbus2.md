# ADR 0015: Leitura do ADS1115 por smbus2, fora da pilha Adafruit

**Status:** Decidido e implementado (2026-10-11). Validado no
dispositivo, com o ciclo completo rodando pelo cron.

## Contexto

O sensor capacitivo de umidade do solo é analógico, e o Raspberry Pi não
tem conversor analógico-digital. Por isso o ADS1115 (ADC I2C de 16 bits)
é obrigatório desde a Fase 1 do Blueprint.

A leitura era feita por `adafruit-circuitpython-ads1x15`, que roda sobre
Adafruit-Blinka, que por sua vez fala com o kernel através de
Adafruit-PureIO. **Essa pilha não funciona neste dispositivo.** Toda
leitura de registrador levanta:

```
OSError: [Errno 5] Input/output error
  .../Adafruit_PureIO/smbus.py, em read_i2c_block_data
  ioctl(self._device.fileno(), I2C_RDWR, request)
```

A causa é que a PureIO 1.1.11 monta a estrutura da chamada `ioctl`
manualmente com `ctypes`, em vez de usar o caminho padrão do kernel.
Essa montagem quebra na combinação em produção: Raspberry Pi 3B+,
Raspberry Pi OS trixie, Python 3.13, kernel 6.18, ARM 64 bits.

O ponto importante é que **o problema não é elétrico**. Medido no mesmo
módulo, com a mesma fiação, no mesmo minuto:

| Caminho | Resultado |
|---|---|
| `adafruit_ads1x15` | **0 sucessos em 3** |
| `smbus2` | **10 sucessos em 10**, registrador de configuração devolvendo `0x8583`, que é o valor de fábrica do chip |

O diagnóstico levou tempo porque o sintoma imita defeito de hardware: o
módulo responde ao reconhecimento de endereço (o scan I2C encontra o
`0x48`) e falha só na leitura de registrador. Isso foi confundido com
solda fria em mais de uma sessão.

## Decisão

`edge/src/sensors/soil_moisture.py` conversa **direto com os
registradores do ADS1115**, usando `smbus2`.

O protocolo justifica a escolha por ser trivial: escreve-se a
configuração desejada no registrador `0x01`, espera-se a conversão e
lê-se o resultado no registrador `0x00`. São cerca de 20 linhas, contra
uma cadeia de quatro bibliotecas.

A configuração usada é `0xC383` para o canal A0 (`0xC383 | MUX` para os
demais): disparo único, fundo de escala de 4,096 V, 128 amostras por
segundo, comparador desligado. O fundo de escala de 4,096 V é o que
torna 3,3 V equivalente ao valor bruto 26400, que é a referência citada
em `edge/src/config.py`.

## Por que não foi consertar a biblioteca

Três razões, em ordem de peso:

1. **Não é a primeira vez.** Esta mesma dependência já quebrou o projeto
   antes, quando as constantes de canal mudaram de `ads1115.P0` para
   `ads1x15.Pin.A0` entre versões. O código passava nos testes e
   quebrava no Pi.
2. **O conserto não estaria nas nossas mãos.** A falha é na PureIO, e
   depender de uma correção upstream num TCC com prazo é risco sem
   contrapartida.
3. **O ganho da abstração não se aplica aqui.** A pilha CircuitPython
   existe para dar portabilidade entre placas. O projeto roda num
   modelo só de Raspberry Pi, decidido no
   [ADR 0004](0004-raspberry-pi-3b-plus.md).

O DHT22 **continua** usando `adafruit-circuitpython-dht`. Ele não é
afetado, porque fala 1-Wire por GPIO e não passa pela camada de I2C que
quebra. Trocar o que funciona seria mudança sem motivo.

## O dublê dos testes passou a ser mais fiel

O mock anterior substituía a conversão inteira, devolvendo um número
pronto. Era justamente por isso que ele não pegou a mudança de API da
Adafruit: os testes ficavam verdes enquanto o dispositivo quebrava.

O novo dublê simula os **dois bytes que o chip devolve**, então a
decodificação roda de verdade nos testes: big-endian e complemento de
dois. Dois casos novos cobrem o que isso protege:

- valor negativo do ADC, que sem a conversão de sinal viraria 65036 em
  vez de -500 e **inverteria a leitura**, mostrando solo seco quando
  está saturado
- canal inexistente, recusado antes de tocar no barramento

A regra que fica: **um dublê que simula mais do que a fronteira de
hardware esconde falha em vez de revelar.**

## Consequência de hardware: o canal passou a ser o A1

Durante a validação, o pino **A0 do módulo físico não faz contato**. Ele
lê como entrada solta mesmo com 3,0 V confirmados por multímetro na
coluna correspondente da protoboard. Os pinos de alimentação e de I2C,
que ficam na outra extremidade do módulo, funcionam.

Como `SOIL_ADS1115_CHANNEL` já era configurável, o contorno foi mudar
para o canal **A1** no `.env` do dispositivo, sem alterar código.

**Isso é remendo de protoboard e não deve ir para a placa soldada.** Na
montagem definitiva o canal volta a ser o A0, ou o defeito é
diagnosticado e corrigido na solda.

## Calibração obtida

Primeira calibração real do sensor, substituindo os valores de
fabricante que estavam no código:

| Condição | Valor bruto | Tensão | Variação em 40 amostras |
|---|---|---|---|
| Seco, suspenso no ar | **17468** | 2,184 V | 102 |
| Submerso até a linha | **7179** | 0,897 V | 11 |

Faixa útil de 10.289 pontos. A variação de 11 na água, que é 0,15%,
indica sinal estável.

Esses valores valem para **este** sensor e **esta** alimentação de
3,3 V. Trocar o sensor exige recalibrar.

## Pendências

- Resolver o pino A0 na placa soldada e voltar `SOIL_ADS1115_CHANNEL`
  para 0, ou registrar o canal definitivo.
- Recalibrar com o sensor enfiado em **terra**, não em água. Água pura
  é o extremo absoluto de saturação e tende a superestimar a faixa; o
  limiar agronômico do [ADR 0005](0005-limiares-ambientais.md) assume
  solo.
- Remover `Adafruit-Blinka` quando e se o DHT22 também sair da pilha. Por
  enquanto ela é necessária, porque fornece o módulo `board`.
