# ADR 0005: Limiares de risco ambiental (temperatura, umidade do ar, umidade do solo)

**Status:** Decidido. Revisado em 2026-11-03: a ressalva sobre umidade do
solo passou a citar a referência específica para tomate de mesa tutorado
(tensão crítica de 15-25 kPa) e a explicar, com os números do próprio
capítulo, por que a escala do sensor não é conversível para ela sem
calibração. Ver "Ressalva sobre umidade do solo" e "Como calibrar contra
o critério da Embrapa".

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
| Umidade do solo (seca) | critério publicado é **15-25 kPa de tensão** (Embrapa), não porcentagem | `< 20%` | **alta**: estresse hídrico pode matar a planta rápido | **Limite operacional**: o critério agronômico está citado, mas a escala do sensor é outra, ver ressalva abaixo |
| Umidade do solo (encharcada) | idem acima | `> 80%` | **media**: apodrecimento é mais gradual | **Limite operacional**, ver ressalva abaixo |

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

### Por que esse número não pode ser usado direto

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
largura**, entre 44,65% e 41,83%. O sensor do EcoVision
(`edge/src/sensors/soil_moisture.py`, ADS1115) não devolve umidade
volumétrica nem tensão: devolve porcentagem **relativa aos próprios
pontos de calibração** (`SOIL_DRY_RAW` e `SOIL_WET_RAW` em
`edge/src/config.py`, 0% = seco calibrado, 100% = molhado calibrado).

A distância entre os dois números é a prova de que as escalas são
diferentes: se os 20% do limiar fossem umidade volumétrica, o vaso
estaria permanentemente abaixo do ponto de murcha, e a planta está viva.
Em 2026-11-03, com a terra recém-molhada, o sensor leu 90,5%, valor que
como umidade volumétrica seria fisicamente impossível em solo.

### O que fica decidido

Os limiares de 20% e 80% continuam valendo como **limite operacional do
projeto**, e é assim que o app os apresenta ao produtor
(`app/src/components/SerieTemporalCard.tsx`, constante `FAIXA_SOLO_PCT`):
a legenda da série de solo cita o critério da Embrapa em kPa e diz, na
mesma frase, que o sensor não mede tensão e que o limite aguarda
calibração. O pé do cartão traz a referência bibliográfica.

Essa é a diferença de tratamento entre as três séries, e é deliberada:
temperatura e umidade do ar têm limiar e fonte na mesma unidade, então a
linha tracejada **é** a recomendação. Na série de solo, a linha é nossa
e a recomendação está citada ao lado.

## Revisão futura

Os limiares de umidade do solo devem ser revisados assim que:
1. O sensor físico for calibrado de verdade em protoboard (pendência já
   registrada em `edge/README.md`, "Pendências de grupo").
2. Houver dados reais de campo (Sprint 9, validação em campo) para
   comparar o comportamento da planta com os valores lidos.

### Como calibrar contra o critério da Embrapa

Agora que a referência está identificada, a calibração tem alvo. Dois
caminhos, do mais simples ao mais correto:

1. **Pareamento com tensiômetro.** Instalar um tensiômetro no mesmo
   vaso, na camada de 0 a 20 cm, e registrar pares (leitura do sensor,
   kPa) ao longo de um ciclo de secagem, do solo encharcado até o ponto
   em que a planta murcha. O limiar passa a ser a porcentagem do sensor
   que corresponde a 25 kPa. Tensiômetro de punção é o instrumento mais
   barato dessa lista, e a própria Embrapa observa que ele lê bem até
   cerca de 80 kPa, o que cobre a faixa de manejo com folga.

2. **Curva de retenção do substrato.** Coletar amostra indeformada em
   anel volumétrico na camada de 0 a 20 cm e levantar a curva em
   laboratório. É o procedimento que o capítulo descreve, dá o resultado
   mais defensável, e é o que exige laboratório de física do solo.

Enquanto nenhum dos dois for feito, a documentação e a tela devem
continuar dizendo que o limite é operacional. **Trocar o rótulo sem
fazer a medição seria atribuir à Embrapa um número que não é dela.**

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
