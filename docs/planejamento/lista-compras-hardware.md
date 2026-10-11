# Lista de Compras: Hardware IoT (BoM)

Espelho local da tabela de compras do **Tech Stack Blueprint Consolidado
v3.0, Fase 1**, para o grupo cotar, marcar status e registrar links/lojas
escolhidas. É a mesma lista que bloqueia o início do trabalho de hardware
(`edge/`): os itens "Semana 1" são bloqueadores de desenvolvimento
daquela camada.

> **Regra do Blueprint:** a coluna de preço é uma estimativa de partida.
> Cotar todos os itens **em conjunto**, com atenção especial à
> compatibilidade elétrica entre eles (tensão, corrente e protocolo de
> cada peça precisam ser conferidos em conjunto, não isoladamente, ex.:
> a tensão/corrente do Ring LED escolhido define qual MOSFET serve, e
> isso define se o resistor de gate precisa mudar).

## Tabela de compras

Preencher a coluna **Status** (`A cotar` / `Cotado` / `Comprado`) e
**Loja/link** conforme o grupo avança. Nada deve ser comprado antes de
uma sessão conjunta de cotação (ver pendência na seção final).

| Componente | Qtd | Compra | Status | Loja/link | Justificativa técnica (resumo) |
|---|---|---|---|---|---|
| **Raspberry Pi 3 Model B+** | 1 | Semana 1 | **Comprado** | — | Processador central da borda. Não roda inferência de IA. **Substituiu o Pi Zero 2 W** previsto originalmente, por disponibilidade e homologação Anatel (ver [ADR 0004](../decisions/0004-raspberry-pi-3b-plus.md)). |
| Raspberry Pi Camera Module 3 | 1 | Semana 1 | **Comprado** | — | Autofoco PDAF 5cm–infinito, essencial a 15cm de distância. V2 descartada por foco fixo (ver [ADR 0001](../decisions/0001-camera-module-3.md)). Detectada no dispositivo como `imx708`, capturando 4608x2592. |
| Cabo FFC da câmera | 1 | Semana 1 | **Comprado** | — | **O cabo adaptador não foi necessário.** A previsão original supunha o Pi Zero, cujo conector CSI é estreito, de 22 pinos. O Pi 3B+ usa o conector largo de 15 pinos, que é o cabo que já vem na caixa da Camera Module 3. |
| MicroSD 32GB Classe 10 (A1/A2) | 1 | Semana 1 | **Comprado** | — | OS + cache offline. A1/A2 evitam corrupção silenciosa por IOPS insuficiente. |
| Fonte 5V/3A, conector Micro-USB | 1 | Semana 1 | **Comprado** | — | Carregador de celular comum causa brownout e corrupção do SD. Verificado no dispositivo com `vcgencmd get_throttled`, que devolveu `0x0` após 1h27 de uso incluindo os 265mA do LED: nenhum evento de subtensão. |
| Dissipador de alumínio + thermal pad | 1 | Semana 1 | A cotar | — | Reduz temperatura do SoC em 10-15°C; throttling inicia a 80°C. Medição atual sem dissipador: 44,5°C em repouso. |
| LED de potência branco 5V | 1 | Semana 1 | **Comprado** | — | Flash dominante a 15cm. **O "0,5s" previsto aqui estava errado:** medido no dispositivo, o LED fica aceso de 5,6s a 27s, porque quem domina o tempo é o autofoco (Blueprint v4, seção 3.2). |
| MOSFET canal N (nível lógico 3.3V), **IRLZ44N** | 1 | Semana 1 | **Comprado** | — | Chave digital entre GPIO (máx. 16mA) e o LED (~265mA); item que faltava no Blueprint v2.0. |
| Resistor de gate **10kΩ** (para o MOSFET) | 1 | Semana 1 | **Comprado** | — | **Validado com 10kΩ, não com os 220-330Ω previstos.** O gate é capacitivo e quase não consome corrente, então o valor só altera a velocidade de chaveamento: 100µs de transição num flash de segundos é irrelevante, e 10kΩ ainda reduz o pico no GPIO de 15mA para 0,33mA. |
| **Resistor 6,8Ω 2W (série com o LED)** | 1 | Semana 1 | **Comprado** | — | **Faltava nesta lista, apesar de obrigatório.** Limita a corrente do LED em (5V − 3,2V)/6,8Ω = 265mA. **Precisa ser de 2W:** dissipa 0,48W, o que destruiria um resistor de 1/4W, que é o padrão dos kits. |
| Sensor DHT22 | 2 | Semana 1 | **Comprado** | — | Temperatura/umidade do ar. 1 sobressalente incluído. Validado no dispositivo. |
| Sensor Capacitivo de Umidade do Solo | 2 | Semana 1 | **Comprado** | — | Capacitivo evita corrosão por eletrólise. Sinal analógico, requer ADS1115. **O sobressalente foi usado:** ter comprado 2 permitiu isolar sensor de módulo durante o diagnóstico, e valeu a pena. |
| Módulo ADC ADS1115 | 1 | Semana 1 | **Comprado** | — | O Raspberry Pi não tem ADC nativo; obrigatório para o sensor de solo. Lido por `smbus2`, não pela lib da Adafruit (ver [ADR 0015](../decisions/0015-ads1115-por-smbus2.md)). **Vale comprar um sobressalente:** o módulo vem sem a barra de pinos soldada, e dessoldar para corrigir um erro de solda aquece demais o chip. |
| Jumpers, resistores (10kΩ), protoboard kit | kit | Semana 1 | **Comprado** | — | Prototipagem e pull-up do DHT22. Não soldar nada antes de validar o circuito completo. |
| Multímetro digital | 1 | Semana 1 | **Comprado** | — | **Não constava da lista original, e sem ele vários problemas desta fase seriam indiagnosticáveis.** Foi o que separou "LED queimado" de "polaridade invertida", "resistor errado" de "chave na faixa errada", e "módulo com defeito" de "mau contato". Um DT-830D básico resolve. |
| Placa de circuito impresso ilhada 4x6cm, dupla face | 1 | Semana 4-5 | **Comprado** | Eletrogate `GV4-C-003` | Montagem permanente após validação em protoboard. Os 6cm são o mínimo: a barra de 20 pinos ocupa 50,8mm. |
| Placa ilhada 3x7cm, dupla face (reserva) | 1 | Semana 4-5 | **Comprado** | Eletrogate `GV4-C-002` | Reserva. A primeira solda de um iniciante costuma sair com ponte ou trilha arrancada, e sem reserva o projeto para esperando frete. |
| Barra de pinos fêmea soquete 1x40, 180° | 3 | Semana 4-5 | **Comprado** | Eletrogate `GV4-A-004` | Encaixa a placa nos 40 pinos do Pi sem jumper. Duas cortadas ao meio formam as duas fileiras de 20; a terceira é margem para errar o corte. **Soquete, não torneada:** os pinos do Pi são quadrados e deformam o contato redondo da torneada, que ainda custa 6x mais. |
| Conector borne KRE 2 vias | 2 | Semana 4-5 | **Comprado** | Eletrogate `GV3-J-002` | Conexão do LED por parafuso. Permite reposicionar o LED em relação à lente sem desfazer solda. |
| Conector borne KRE 3 vias | 3 | Semana 4-5 | **Comprado** | Eletrogate `GV3-J-001` | Conexão do DHT22 e do sensor de solo, que ficam fora da caixa. |
| Impressão 3D da case PETG + prensa-cabos | 1 | Semana 4-5 | A cotar | — | Encomendar só após o layout final do circuito. Antes disso, uma caixa de papelão valida a geometria sem custo. |

## Orçamento

Estimativa de partida do Blueprint: **R$ 1.600** (frente aos ~R$ 900 do
TC1 original), aumento gerado principalmente pela troca de câmera
(V2→V3) e pela adição do MOSFET/resistor de gate.

Tratar como ponto de partida, não valor fechado. Objetivo da cotação
conjunta não é só o menor preço por item, mas garantir a compatibilidade
elétrica entre eles.

## Estado da compra

Os itens da Semana 1 foram comprados e **todos validados em hardware em
2026-10-11**: os três sensores, a câmera e o circuito de flash rodaram o
ciclo completo pelo cron (Blueprint v4, seção 3.4).

Os itens da Semana 4-5 da montagem definitiva foram comprados na
Eletrogate. Falta só a case, que depende de medir a geometria real.

## O que esta lista errou, e por quê

Vale registrar, porque é argumento de banca e evita repetir:

1. **Faltava o resistor em série do LED.** Componente obrigatório, sem
   o qual o LED queima. Passou despercebido porque a lista detalhou o
   resistor de gate, que é o acessório, e esqueceu o que limita a
   corrente principal.
2. **A potência dos resistores não foi especificada.** Resistência sem
   potência é meia especificação: 6,8Ω de 1/4W e de 2W custam o mesmo e
   só um dos dois sobrevive neste circuito.
3. **A duração do flash estava subestimada em até 50 vezes.** "0,5s"
   virou 5,6s a 27s na prática, porque ninguém tinha medido quanto o
   autofoco demora.
4. **O multímetro não estava na lista.** É a ferramenta que separa
   defeito real de erro de montagem, e sem ela a fase de bancada
   custaria muito mais tempo.

O padrão por trás dos quatro: **a lista foi escrita a partir do
diagrama, não a partir de uma montagem.** Itens que só aparecem quando
se monta de verdade ficaram de fora.
