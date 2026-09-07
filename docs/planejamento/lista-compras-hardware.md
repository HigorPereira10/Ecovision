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
| Raspberry Pi Zero 2 W | 1 | Semana 1 | A cotar | — | Processador central da borda. Não roda inferência de IA. |
| Raspberry Pi Camera Module 3 | 1 | Semana 1 | A cotar | — | Autofoco PDAF 5cm–infinito, essencial a 15cm de distância. V2 descartada por foco fixo (ver ADR 0001). |
| Cabo FFC 15cm (Pi Zero ↔ Camera) | 1 | Semana 1 | A cotar | — | Pi Zero usa conector CSI de 22 pinos; a Camera V3 vem com cabo para Pi 4, precisa de adaptador. |
| MicroSD 32GB Classe 10 (A1/A2) | 1 | Semana 1 | A cotar | — | OS + cache offline. A1/A2 evitam corrupção silenciosa por IOPS insuficiente. |
| Fonte 5V/3A, conector Micro-USB | 1 | Semana 1 | A cotar | — | Carregador de celular comum causa brownout e corrupção do SD. |
| Dissipador de alumínio + thermal pad | 1 | Semana 1 | A cotar | — | Reduz temperatura do SoC em 10-15°C; throttling inicia a 80°C. |
| Anel de LED Branco (Ring LED, 5V) | 1 | Semana 1 | A cotar | — | Flash dominante a 15cm, acionado via GPIO por 0,5s. |
| MOSFET canal N (nível lógico 3.3V), ex. 2N7000/IRLZ44N | 1 | Semana 1 | A cotar | — | Chave digital entre GPIO (máx. 16mA) e o Ring LED (5V); item que faltava no Blueprint v2.0. |
| Resistor de gate 220-330Ω (para o MOSFET) | 1 | Semana 1 | A cotar | — | Limita corrente de chaveamento no gate do MOSFET. |
| Sensor DHT22 | 2 | Semana 1 | A cotar | — | Temperatura/umidade do ar. 1 sobressalente incluído. |
| Sensor Capacitivo de Umidade do Solo | 2 | Semana 1 | A cotar | — | Capacitivo evita corrosão por eletrólise. Sinal analógico, requer ADS1115. |
| Módulo ADC ADS1115 | 1 | Semana 1 | A cotar | — | Pi Zero não tem ADC nativo; obrigatório para o sensor de solo. |
| Jumpers, resistores (10kΩ), protoboard kit | kit | Semana 1 | A cotar | — | Prototipagem e pull-up do DHT22. Não soldar nada antes de validar o circuito completo. |
| Placa universal para soldagem final | 1 | Semana 4-5 | A cotar | — | Montagem permanente após validação em protoboard. |
| Impressão 3D da case PETG + prensa-cabos | 1 | Semana 4-5 | A cotar | — | Encomendar só após o layout final do circuito. |

## Orçamento

Estimativa de partida do Blueprint: **R$ 1.600** (frente aos ~R$ 900 do
TC1 original), aumento gerado principalmente pela troca de câmera
(V2→V3) e pela adição do MOSFET/resistor de gate.

Tratar como ponto de partida, não valor fechado. Objetivo da cotação
conjunta não é só o menor preço por item, mas garantir a compatibilidade
elétrica entre eles.

## Pendência de grupo

Fechar esta lista definitiva (com links/lojas escolhidas e status
atualizado) em uma única sessão do grupo, **antes de qualquer compra da
Semana 1**: essa sessão é o item de maior urgência da Fase 0 (ver
[`docs/planejamento/divisao-equipe-e-roadmap.md`](divisao-equipe-e-roadmap.md)).
Só depois dessa sessão os itens "Semana 1" devem ser efetivamente
comprados, já que são bloqueadores do início do trabalho de hardware.
