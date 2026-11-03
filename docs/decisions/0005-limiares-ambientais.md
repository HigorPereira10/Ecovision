# ADR 0005: Limiares de risco ambiental (temperatura, umidade do ar, umidade do solo)

**Status:** Decidido. Revisado em 2026-11-03: a ressalva sobre umidade do
solo passou a citar as DUAS referências publicadas para tomate (tensão
crítica de 15-25 kPa, Embrapa; e manter acima de 60% da água disponível,
FAO-56) e a explicar por que a escala do sensor não é conversível para
nenhuma das duas. O sensor foi calibrado entre ar seco e água pura, então
não mede a grandeza certa, e os 20%/80% passaram a ser declarados como
limite de ALERTA do sistema, não recomendação. Ver "Ressalva sobre
umidade do solo" e "Como calibrar, agora que a calibração tem alvo".

## Contexto

O sistema gera um alerta automático quando o diagnóstico de imagem
aponta doença/praga (ver `cloud/app/api/routes/diagnostico.py`), mas
faltava o segundo tipo de risco previsto no schema (`alertas.leitura_id`):
risco **ambiental**, derivado direto das leituras dos sensores
(temperatura, umidade do ar, umidade do solo), independente da foto.

Isso exige números de referência: não é algo que dá pra inventar no
código sem uma fonte, principalmente porque o resultado influencia uma
recomendação real pro produtor.

## Decisão

Implementar `cloud/app/core/alertas_ambientais.py` com os limiares
abaixo, com fontes de confiabilidade diferentes por variável:

| Variável | Faixa seguem | Alerta quando | Severidade | Confiabilidade da fonte |
|---|---|---|---|---|
| Temperatura | 21-27°C dia / 16-18°C noite (ideal); 10-34°C (tolerância ampla) | `< 10°C` ou `> 34°C` | **alta**: fora da tolerância ampla, risco de perda rápida | **Alta**: Embrapa Hortaliças |
| Umidade do ar | 55-70% (ideal) | `> 90%` | **media**: favorece doença, não mata a planta diretamente | **Alta**: Embrapa Hortaliças |
| Umidade do solo (seca) | critérios publicados são **15-25 kPa** (Embrapa) e **> 60% da água disponível** (FAO-56); nenhum na unidade do sensor | `< 20%` | **alta**: estresse hídrico pode matar a planta rápido | **Limite de alerta do sistema**, não recomendação: o sensor foi calibrado entre ar e água, ver ressalva abaixo |
| Umidade do solo (encharcada) | idem acima | `> 80%` | **media**: apodrecimento é mais gradual | **Limite de alerta do sistema**, ver ressalva abaixo |

Severidade usada em `alertas.severidade` (`cloud/app/db/models.py`);
ver também [ADR 0006](0006-recomendacoes-por-diagnostico.md) para a
severidade dos alertas de doença/praga, com a mesma escala (`alta` |
`media`).

## Fontes

- **Embrapa Hortaliças, "Clima" (tomate de mesa)**:
  https://www.embrapa.br/web/hortalicas/tomate-de-mesa/clima
  > "A temperatura ótima para germinação das sementes do tomateiro
  > situa-se na faixa dos 15-25°C. Para o desenvolvimento e produção, o
  > tomateiro suporta ampla variação de temperatura (10-34°C)."
  > "A umidade relativa do ar deve se manter abaixo de 90%, o que
  > previne o surgimento de mofo nas folhas. As condições ótimas para a
  > polinização são 22-28°C e umidade relativa acima de 70%."

- **CPT, "Orientações para cultivar tomate em estufa"**:
  https://www.cpt.com.br/cursos-horticultura-agricultura/artigos/orientacoes-para-cultivar-tomate-em-estufa
  Faixa de temperatura recomendada especificamente para cultivo em
  estufa: 21-27°C de dia, 16-18°C à noite (21°C em dias nublados, 27°C
  em dias ensolarados).

- **Literatura internacional (revisão geral, contexto adicional, não
  citada como número oficial)**: umidade relativa entre 55-70% durante
  o dia é a faixa mais frequentemente recomendada entre os guias de
  cultivo em estufa consultados; acima de ~80% o risco de doenças
  fúngicas (mofo cinzento, oídio) aumenta de forma consistente entre as
  fontes.

## Ressalva sobre umidade do solo

Atualizada em 2026-11-03, quando a referência específica para tomate de
mesa tutorado foi localizada. A versão anterior desta seção dizia que
"não existe um número único e amplamente aceito". Isso estava errado:
**o critério existe, é publicado pela Embrapa, e é específico para esta
cultura.** O que não existe é equivalência entre ele e o que o sensor
mede.

### O critério agronômico, com fonte

> BRAGA, M.B.; FELTRIM, A.L.; BORGES, L.C. Irrigação. In: ZAMBOLIM, L.;
> QUEZADO-DUVAL, A.M. (org.). **Produção integrada do tomateiro
> tutorado.** Viçosa, MG: Universidade Federal de Viçosa, Coordenadoria
> de Educação Aberta e a Distância, 2022. cap. 7, p. 102-116.
>
> p. 105: "Normalmente, em cultivos de tomate de mesa, as tensões
> críticas de irrigação variam de 15 a 25kPa. Valores menores de tensões
> (15kPa) são usados por alguns dias (10 a 20 dias), até o pegamento
> definitivo das mudas transplantadas. Após esse período, pode-se passar
> a trabalhar com limites críticos de 25 kPa."
>
> p. 105: "a profundidade efetiva do sistema radicular do tomate [é] de
> 0,40 m [...] o manejo da irrigação deve se basear na camada de 0 - 20
> cm na fase inicial e na soma das duas camadas na fase de maior
> desenvolvimento vegetativo, floração/frutificação e produção."

É documento da Embrapa sobre tomate **tutorado**, que é exatamente o
arranjo desta estufa, e não sobre tomate para processamento, cujos
limiares são diferentes (30 a 480 kPa dependendo do estádio e do sistema
de irrigação).

### O segundo critério, em porcentagem

A referência acima está em kPa, que o sensor não mede. Existe uma
segunda, internacional e em porcentagem, e é ela que dá o alvo da
calibração:

> ALLEN, R.G.; PEREIRA, L.S.; RAES, D.; SMITH, M. **Crop
> evapotranspiration: guidelines for computing crop water
> requirements.** Roma: FAO, 1998. (FAO Irrigation and Drainage Paper,
> 56).
>
> Tabela 22, "Ranges of maximum effective rooting depth (Zr), and soil
> water depletion fraction for no stress (p), for common crops", linha
> do tomate: **Zr 0,7-1,5 m, p 0,40**.
>
> Definição de p: "average fraction of Total Available Soil Water (TAW)
> that can be depleted from the root zone before moisture stress
> (reduction in ET) occurs".
>
> Ajuste por evapotranspiração: "p = p table 22 + 0.04 (5 - ETc)",
> limitado a 0,1 ≤ p ≤ 0,8, com ETc em mm/dia. A nota de rodapé 2 diz
> que os valores da tabela valem para ETc de aproximadamente 5 mm/dia.

Em linguagem direta: **irrigar quando 40% da água disponível foi
consumida, mantendo o solo acima de 60% dela.**

Numa estufa quente o ETc passa de 5 mm/dia, p cai e o piso sobe acima de
60%. Esse refinamento fica para depois da calibração: aplicá-lo agora
seria precisão decorativa sobre um número que ainda não mede a grandeza
certa.

### Por que nenhum dos dois números pode ser usado direto

O capítulo converte tensão em umidade pela **curva de retenção de água
do solo**, que é específica de cada solo. No exemplo trabalhado da
p. 106, para tomate de mesa tutorado com raiz a 400 mm:

| Grandeza | Valor |
|---|---|
| Tensão na capacidade de campo | 10 kPa |
| Umidade na capacidade de campo | 44,65% (volumétrica, cm³/cm³) |
| Tensão de irrigação adotada | 25 kPa |
| Umidade correspondente | 41,83% (volumétrica, cm³/cm³) |

**A faixa inteira de manejo tem menos de 3 pontos percentuais de
largura**, entre 44,65% e 41,83%.

E aqui está a razão de fundo, que vale para as duas fontes. O sensor foi
calibrado nos dois EXTREMOS ABSOLUTOS, e está registrado em
`edge/src/config.py`:

| Ponto | Como foi medido | Leitura bruta |
|---|---|---|
| `SOIL_DRY_RAW` | sensor suspenso **no ar** | 17468 (2,184 V) |
| `SOIL_WET_RAW` | sensor **submerso em água pura** | 7179 (0,897 V) |

Os 0-100% resultantes significam "umidade relativa entre ar seco e
submerso em água". Isso não é tensão, não é umidade volumétrica e não é
fração de água disponível. É por isso que não existe conversão: não
falta um fator de escala, falta a grandeza.

A distância entre os dois números é a prova de que as escalas são
diferentes: se os 20% do limiar fossem umidade volumétrica, o vaso
estaria permanentemente abaixo do ponto de murcha, e a planta está viva.
Em 2026-11-03, com a terra recém-molhada, o sensor leu 90,5%, valor que
como umidade volumétrica seria fisicamente impossível em solo.

### O que fica decidido

Os 20% e 80% são **limite de alerta deste sistema**, não recomendação
publicada, e o app os apresenta exatamente assim
(`app/src/components/SerieTemporalCard.tsx`, constante `FAIXA_SOLO_PCT`).

A diferença de tratamento entre as três séries é deliberada e visível:

| Série | Linha no gráfico | Traço | O que a legenda diz |
|---|---|---|---|
| Umidade do ar | 90% | tracejado largo | "recomendado" |
| Temperatura | 34 °C | tracejado largo | "recomendado" |
| Umidade do solo | 20% | **pontilhado** | "é onde o sistema avisa", e que não é recomendação |

O traço diferente existe porque uma linha tracejada num gráfico é lida
como "este é o limite". Nas duas primeiras isso é verdade: limiar e fonte
estão na mesma unidade. Na terceira seria a nossa invenção com a mesma
aparência de autoridade das outras duas. O pé do cartão cita as duas
fontes publicadas e diz que a linha de 20% aguarda calibração contra
elas.

**A linha fica visível, e não é removida**, porque o alerta de solo seco
dispara de verdade nesse valor (ver `UMIDADE_SOLO_MIN_PCT`). Gatilho que
dispara invisível é pior do que gatilho mal justificado: o produtor
receberia um aviso cujo critério não está em tela nenhuma. A tela de
Perfil também mostra o valor, como "Alerta de solo seco, abaixo de 20%",
que descreve o que o sistema faz em vez de alegar o que a agronomia
recomenda.

## Revisão futura

Os limiares de umidade do solo devem ser revisados assim que:
1. O sensor físico for calibrado de verdade em protoboard (pendência já
   registrada em `edge/README.md`, "Pendências de grupo").
2. Houver dados reais de campo (Sprint 9, validação em campo) para
   comparar o comportamento da planta com os valores lidos.

### Como calibrar, agora que a calibração tem alvo

Três caminhos, do mais barato ao mais defensável. O primeiro é o que
transforma o limiar em número citável com o menor esforço, e é o
recomendado.

**1. Recalibrar os dois extremos (recomendado).** Trocar os pontos de
calibração de `edge/src/config.py`:

| Hoje | Deveria ser |
|---|---|
| `SOIL_DRY_RAW` no ar | `SOIL_DRY_RAW` no **ponto de murcha permanente** |
| `SOIL_WET_RAW` em água pura | `SOIL_WET_RAW` na **capacidade de campo** |

Na prática: molhar o vaso até drenar livremente e esperar a drenagem
parar, que é a capacidade de campo, e ler o sensor ali. Depois deixar
secar sem irrigar até a planta murchar e não recuperar à noite, que é o
ponto de murcha permanente, e ler ali. Com esses dois pontos, os 0-100%
de `soil_moisture.py` passam a aproximar **porcentagem de água
disponível**, que é exatamente a grandeza da Tabela 22 da FAO-56, e o
piso passa a ser **60%**, citável direto. Custa um ciclo de secagem e
nenhum instrumento novo.

**2. Pareamento com tensiômetro.** Instalar um tensiômetro no mesmo
vaso, na camada de 0 a 20 cm, e registrar pares (leitura do sensor, kPa)
ao longo de um ciclo de secagem. O limiar passa a ser a porcentagem do
sensor que corresponde a 25 kPa, citável de Braga et al. A Embrapa
observa que o tensiômetro lê bem até cerca de 80 kPa, o que cobre a
faixa de manejo com folga. Custa o instrumento.

**3. Curva de retenção do substrato.** Coletar amostra indeformada em
anel volumétrico na camada de 0 a 20 cm e levantar a curva em
laboratório. É o procedimento que o capítulo da Embrapa descreve e dá o
resultado mais defensável. Exige laboratório de física do solo.

Enquanto nenhum dos três for feito, a documentação e a tela continuam
dizendo que a linha é limite de alerta, não recomendação. **Trocar o
rótulo sem fazer a medição seria atribuir à Embrapa, ou à FAO, um número
que não é delas.**

## Implementação

- `cloud/app/core/alertas_ambientais.py`
- Consumido por `cloud/app/api/routes/diagnostico.py`


## Adendo (2026-10-11): leitura de solo em 0,0% é suspeita de sensor

Descoberto no primeiro ciclo com o dispositivo montado. Com o sensor
capacitivo fora da terra, a leitura voltou em **0,0%** e o sistema
gerou um alerta **crítico** de "Solo seco, risco de estresse hídrico".

0,0% é o **piso da escala**, não uma medição: o percentual vem de um
clamp entre 0 e 100 sobre o valor bruto do ADS1115
(`edge/src/sensors/soil_moisture.py`), então zero significa "leu no
limite seco ou além dele". Isso acontece com sensor fora da terra,
haste solta, conector frouxo ou `SOIL_DRY_RAW` mal calibrado, e não com
solo de estufa irrigada, que não chega a zero absoluto.

**Decisão:** exatamente 0,0% gera "Verifique o sensor de umidade do
solo", severidade **media**, em vez do alerta de seca. Qualquer valor
acima de zero e abaixo de `UMIDADE_SOLO_MIN_PCT` continua sendo seca,
com severidade alta.

**Por quê:** mandar irrigar por causa de um sensor pendurado no ar é
pior do que não alertar. Alarme que não corresponde ao mundo ensina
quem usa o sistema a ignorar aquele alarme, e o primeiro a ser ignorado
seria justamente o de seca.

A margem é zero por enquanto, de propósito: só o valor exato dispara.
Depois da calibração com terra de verdade, dá para subir o piso para um
número medido, quando houver dado para escolhê-lo.

Implementado em `cloud/app/core/alertas_ambientais.py`
(`SOLO_PISO_SUSPEITO_PCT`), com teste em
`cloud/tests/test_alertas_ambientais.py`.
