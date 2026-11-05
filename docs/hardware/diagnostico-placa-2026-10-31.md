# Diagnóstico da placa soldada: contaminação, não solda

**Data:** 2026-10-31
**Dispositivo:** `ecovision-pi-01`, Raspberry Pi 3B+ em `192.168.15.17`
**Estado:** causa confirmada em 2026-11-01, conserto pendente
**Atualizado:** 2026-11-01, com a confirmação na protoboard e a falha do DHT22

## Conclusão, antes dos detalhes

A placa tem **caminhos condutivos de 140 Ω a 12 kΩ entre ilhas que deveriam
estar isoladas**. Não é ponte de solda, não é componente queimado, e não é
defeito do Raspberry Pi.

Três sintomas que pareciam problemas separados são o mesmo problema:

| Sintoma | Rede afetada |
|---|---|
| Sensor de solo não responde | SDA e SCL |
| LED pisca em vez de acender firme | GPIO18 |
| DHT22 parou de responder (2026-11-01) | GPIO4 |
| LED aceso fraco em repouso | provavelmente Dreno |

**O defeito avança.** No dia 31/10 o GPIO4 era a única linha de sinal limpa na
varredura. No dia seguinte o DHT22 parou, sem ninguém encostar na placa. São
**4 de 4 redes de sinal comprometidas**, e a degradação progressiva é o que a
hipótese de contaminação prevê: resíduo de fluxo absorve umidade do ar e vai
ficando mais condutivo com o tempo.

**O conserto é limpeza, não ressolda.** Quem for mexer precisa saber disso,
senão vai procurar ponte de solda com o multímetro no modo apito e não vai
achar nada. O modo apito só apita abaixo de uns 50 Ω, e nenhum destes
defeitos está nessa faixa.

---

## Confirmação de 2026-11-01: a placa é a causa única

Os mesmos componentes foram remontados na protoboard, na montagem já validada
(ver seção "Montagem na protoboard"), e **tudo voltou a funcionar**:

| Teste | Na placa soldada | **Na protoboard** |
|---|---|---|
| Varredura dos 24 GPIOs | 3 presos no terra | **nenhum preso** |
| Linhas SDA e SCL | ambas em `lo` | **ambas em `hi`** |
| Varredura I2C | 117 ou 0 endereços | **só o `0x48`** |
| Registro CONFIG do ADS | `0x0000` | **`0x8583`** |
| DHT22 | parou de responder | **3 leituras de 3** |
| Sensor de solo | nenhuma leitura | **canal 1 em 17582, estável** |
| LED | piscando, 30 quedas em 90 | **firme, Lux 5,99 para 11,21** |

Isto é o experimento conclusivo. **Nenhum componente está com defeito.** O
módulo ADS1115, o DHT22, o sensor de solo, o MOSFET, os resistores, o LED e o
Raspberry Pi estão todos bons, e a placa soldada é a causa única dos quatro
sintomas.

Nada precisa ser recomprado.

### Detalhe de configuração que apareceu junto

O `.env` do dispositivo estava com `LED_MOSFET_PIN=26`, alteração feita de
propósito enquanto o LED não funcionava, para ele não disparar durante os
testes. **A fiação usa o GPIO18**, confirmado por medição contra a linha de
base:

```
apagado          Lux  5,99   brilho 60,0
GPIO18 ligado    Lux 10,97   brilho 94,4
GPIO18 ligado    Lux 11,21   brilho 96,4
apagado          Lux  5,78   brilho 58,7
GPIO26 ligado    Lux  6,31   brilho 61,9   <- igual ao apagado
apagado          Lux  6,29   brilho 61,4
```

O valor precisa voltar para 18 antes de qualquer captura em produção, senão o
flash não dispara e ninguém fica sabendo.

---

## A prova que fecha o argumento

Medição com uma ponteira na perna do resistor de gate, faixa 20k:

| Furo | Lido | Deveria ser |
|---|---|---|
| `B6` | **10,14 kΩ** | 10 kΩ, correto (é o resistor de gate) |
| `B7` | 11,88 kΩ | **aberto** |
| `B8` | 10,57 kΩ | **aberto** |
| `B9` | 11,2 kΩ | **aberto** |
| `B10` | aberto | aberto, correto |

`B7`, `B8` e `B9` **não aparecem em nenhuma das 11 redes da placa**. Não têm
componente, não têm jumper, não têm trilha. Deveriam ler aberto como o `B10`
leu.

Furo vazio conduzindo é contaminação. O `B10` aberto mostra que ela não cobre
a fileira inteira, ela para antes.

---

## As outras medições

| Rede | Medição | Resistência implícita |
|---|---|---|
| SDA (`A2`) | 0,63 V com pull-up de 1,8 kΩ do Pi | ~425 Ω para o terra |
| SCL (`A3`) | 0,24 V com pull-up de 1,8 kΩ do Pi | ~140 Ω para o terra |
| GPIO18 (`B6`) | 30 quedas em 90 amostras, 45 s | intermitente |

Duas confirmações independentes de que **não é curto metálico**:

1. As linhas **sobem quando o Pi força saída em nível alto**. Curto de verdade
   seguraria baixo mesmo forçado.
2. As resistências são de centenas de ohms, não de zero.

---

## O que foi eliminado, e como

Nada aqui é suposição. Cada linha é um teste direto.

| Peça | Como foi eliminada |
|---|---|
| **Raspberry Pi** | Varredura dos 24 GPIOs do conector com pull-up interno: só os 3 que vão para a placa ficaram presos, os outros 21 limpos. Com os jumpers fora, todos sobem |
| **Módulo ADS1115** | Removido. Além de não causar o problema do LED, **remover ele liberou o SDA** |
| **Jumper do SDA** | Trocado por outro, sem mudança |
| **Jumper do GPIO18** | Com ele fora da placa, GPIO18 fica limpo em 10 de 10 leituras |
| **Sensor de solo** | Trocado, sem mudança |
| **LED** | Trocado, continuou piscando |
| **Superfície de apoio** | Placa movida para papelão, sem mudança |
| **Polaridade do LED** | Ele acende, e LED invertido não acende nunca |

### O que funciona

| Peça | Estado |
|---|---|
| Câmera (`imx708`) | captura 4608x2592 normalmente |
| DHT22 (GPIO4) | 3 leituras de 3, 25,6 a 26,1 °C e 63 a 72% |
| MOSFET, resistores, LED, caminho de 5V | validados: o LED acende, então a corrente percorre o circuito inteiro |
| Fonte | `throttled=0x0` o dia todo |

---

## Mapa das redes da placa

Isto não estava versionado em lugar nenhum e é necessário para qualquer
conserto. As 11 redes:

| Rede | Função | Furos |
|---|---|---|
| 1 | 3,3V | `A1`, `C3`, `E11`, `E20`, `N12` |
| 2 | 5V | `B1`, `A20` |
| 3 | **GND** | `A5`, `B3`, `C17`, `D3`, `G3`, `I20`, `N16` |
| 4 | **SDA** | `A2`, `F3` |
| 5 | **SCL** | `A3`, `E3` |
| 6 | dados do DHT22 (GPIO4) | `A4`, `G20`, `I11` |
| 7 | **GPIO18**, antes do 10k | `B6`, `E13` |
| 8 | **Gate** do MOSFET | `A17`, `I13` |
| 9 | catodo do LED | `C20`, `E15` |
| 10 | **Dreno** do MOSFET | `B17`, `K15` |
| 11 | saída analógica do sensor de solo | `I3`, `J3`, `N14` |

### Componentes e onde ficam

| Componente | Entre |
|---|---|
| Resistor 10k de gate | `E13` e `I13` |
| Resistor 6,8 Ω 2W | `E15` e `K15` |
| Resistor 10k pull-up do DHT22 | `E11` e `I11` |
| MOSFET IRLZ44N | `A17` Gate, `B17` Dreno, `C17` Fonte |
| Módulo ADS1115 | coluna 3, de `C3` a `L3` |
| Borne do DHT22 | `E20` VCC, `G20` dados, `I20` GND |
| Borne do sensor de solo | `N12` VCC, `N14` AOUT, `N16` GND |

O módulo ADS1115 entra com o **`VDD` voltado para as fileiras A e B**, na
ordem VDD, GND, SCL, SDA, ADDR, ALRT, A0, A1, A2, A3.

Note que `I3` e `J3` estão na mesma rede: as entradas A0 e A1 do ADS estão
ligadas juntas. É o contorno para o pino A0 do módulo não fazer contato
(ver [ADR 0015](../decisions/0015-ads1115-por-smbus2.md)).

### Jumpers da placa para o Pi

| Furo | Pino do Pi | Cor | Função |
|---|---|---|---|
| `A1` | 1 | laranja | 3,3V |
| `B1` | 2 | branco | 5V |
| `A2` | 3 | azul | SDA |
| `A3` | 5 | preto | SCL |
| `B3` | 6 | vermelho | GND |
| `A4` | 7 | amarelo | dados do DHT22 |
| `A5` | 9 | marrom | GND |
| `B6` | 12 | roxo | gate do MOSFET |

Na placa, a fileira A liga nos pinos ímpares e a fileira B nos pares, igual
ao conector do Pi. No Pi, a fileira par é a da **borda**, confirmado pelo
furo quadrado do pino 1 estar na fileira de dentro, do lado do HDMI.

**Cuidado ao recolocar o jumper do GPIO18:** o `B1` da mesma fileira é 5V.
Se o jumper do GPIO18 cair lá, manda 5V num pino de 3,3V e danifica o Pi.

---

## O conserto

1. **Álcool isopropílico**, de preferência 99%. O de 70% tem 30% de água e
   exige secagem muito mais longa
2. Escova de dente velha ou cotonete, esfregando **os dois lados** da placa
3. Foco em duas regiões:
   - **Fileiras A e B, colunas 1 a 9**, onde estão SDA, SCL e GPIO18
   - **Coluna 3, de `C3` a `G3`**, onde SCL, SDA e GND ficam lado a lado
4. **A cola quente precisa sair** de onde cobre essas regiões: ela prende
   resíduo e umidade contra o cobre
5. **Secar completamente** antes de energizar, meia hora no mínimo
6. Não ressoldar antes de limpar: ressolda sem limpeza só acrescenta fluxo
   novo em cima do problema

### Por que contaminação, e não outra coisa

O resíduo de fluxo de solda é levemente condutivo e **absorve umidade do ar**.
Isso explica o perfil inteiro:

- Funcionou quando foi soldado, degradou depois
- Varia sozinho (o SCL estava em `hi` e virou `lo` entre duas medições)
- Atinge redes vizinhas com resistências diferentes
- Dá centenas de ohms, não curto franco
- Piora onde há cola quente prendendo umidade

---

## Como verificar depois da limpeza

No Pi, a varredura que mostra todos os pinos de uma vez:

```bash
for g in 2 3 4 5 6 7 8 9 10 11 12 13 16 17 18 19 20 21 22 23 24 25 26 27; do
  pinctrl set $g ip pu
done
sleep 1
for g in 2 3 4 5 6 7 8 9 10 11 12 13 16 17 18 19 20 21 22 23 24 25 26 27; do
  n=$(pinctrl get $g | grep -o '| *\(hi\|lo\)' | tr -d '| ')
  [ "$n" = lo ] && echo "GPIO$g PRESO NO TERRA"
done
```

Sem nenhuma saída, está tudo limpo. Com o defeito presente, aparecem
`GPIO2`, `GPIO3` e `GPIO18`.

Para medir a intermitência do GPIO18:

```bash
pinctrl set 18 op dh
hi=0; lo=0
for i in $(seq 1 90); do
  n=$(pinctrl get 18 | grep -o '| *\(hi\|lo\)' | tr -d '| ')
  if [ "$n" = hi ]; then hi=$((hi+1)); else lo=$((lo+1)); fi
  sleep 0.5
done
echo "alto $hi   baixo $lo"
pinctrl set 18 ip
```

Com o defeito, deu 60 alto e 30 baixo. Limpo, deve dar 90 e 0.

**Sempre devolver o pino para entrada (`pinctrl set 18 ip`) ao terminar.**
Deixar o driver de saída empurrando contra um curto danifica o GPIO.

---

## Montagem na protoboard

A montagem de contingência, validada ponta a ponta e novamente em 2026-11-01.
Estava registrada só num arquivo fora do repositório, o que era arriscado agora
que ela é a montagem que funciona.

### Conexões ao Raspberry Pi

| Pino do Pi | Função | Coluna | Cor registrada |
|---|---|---|---|
| 1 | 3,3V | 20 (DHT22 VCC) | vermelho |
| 2 | 5V | 2 | azul |
| 3 | GPIO2 / SDA | 37 (ADS SDA) | branco |
| 5 | GPIO3 / SCL | 38 (ADS SCL) | roxo |
| 6 | GND | `b11` (Fonte do MOSFET) | amarelo |
| 7 | GPIO4 | 21 (DHT22 DATA) | marrom |
| 9 | GND | 23 (DHT22 GND) | laranja |
| 12 | GPIO18 | `d13` (gate via 10k) | verde |
| 17 | 3,3V | 40 (ADS VDD) | azul |
| 20 | GND | 39 (ADS GND) | preto |

As cores já foram remanejadas várias vezes. **Conferir pela posição.**

### Componentes

| Componente | Posição |
|---|---|
| LED positivo | `b2` |
| LED negativo | `a6` |
| Resistor 6,8 Ω 2W | coluna 6 ↔ coluna 10 |
| MOSFET Gate / Dreno / Fonte | `a9` / `a10` / `a11` |
| Resistor de gate 10k | `e9` ↔ `e13` |
| DHT22 | colunas 20 a 23, pino 3 não usado |
| Resistor pull-up 10k do DHT22 | entre as colunas 20 e 21 |
| ADS1115 | linha `e`, VDD na coluna 40 descendo até A3 na 31 |
| Jumper do ADDR | coluna 36 até a coluna 39 |
| Sensor de solo | VCC coluna 40, GND coluna 39, AOUT coluna 33 |

O MOSFET se identifica com a face escrita voltada para quem olha e as pernas
para baixo: Gate, Dreno e Fonte da esquerda para a direita. A aba metálica das
costas é o Dreno, o que serve de conferência por continuidade.

O sensor de solo entra nas linhas `a` a `d`, do mesmo lado do canal central que
os pinos do ADS, que ficam na linha `e`. Nas linhas `f` a `j` não conectaria, e
o sintoma seria idêntico a sensor queimado.

### Dois pontos que já custaram sessões de diagnóstico

**O jumper do ADDR não é opcional.** É ele que fixa o endereço I2C em `0x48`.
Solto, o endereço fica indefinido e o módulo some do barramento.

**O sensor de solo é alimentado com 3,3V, não 5V.** A plaquinha do ADS traz
impresso `Max AIN: VDD`: a tensão de sinal nunca pode passar da alimentação do
ADC. Alimentar os dois do mesmo trilho garante isso por construção.

---

## Pendências que este diagnóstico deixa

- **Limpar e reverificar.** Se os três defeitos sumirem juntos, a hipótese
  está confirmada
- **LED aceso fraco em repouso** continua sem explicação medida. A hipótese
  é vazamento entre o Dreno (`B17`/`K15`) e o GND (`C17`), contornando o
  MOSFET. A limpeza testa isso de graça
- **Falta pull-down de gate.** A placa tem três resistores (10k de gate,
  6,8 Ω do LED, 10k do DHT22) e nenhum pull-down de gate para o terra. Sem
  ele o gate flutua sempre que o GPIO18 não está acionado. Paliativo por
  software: `gpio=18=op,dl` no `/boot/firmware/config.txt`
- **Regime contínuo do LED nunca foi testado.** O Blueprint assume flash de
  segundos a cada 2 horas, e o medido foi 5,6 s a 27 s. No preview ele ficou
  8 minutos aceso, agora colado com fita dupla face, que é isolante térmico
- **Reservar o IP do Pi no roteador.** Ele mudou de `192.168.15.12` para
  `192.168.15.17` por DHCP no meio da sessão
