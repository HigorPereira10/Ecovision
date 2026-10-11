# ADR 0005: Limiares de risco ambiental (temperatura, umidade do ar, umidade do solo)

**Status:** Decidido (primeira versão, sujeito a ajuste após calibração
física do sensor de solo, ver "Revisão futura" abaixo).

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
| Umidade do solo (seca) | "úmida, mas não encharcada" (sem número único na literatura) | `< 20%` | **alta**: estresse hídrico pode matar a planta rápido | **Baixa/convenção prática**, ver ressalva abaixo |
| Umidade do solo (encharcada) | idem acima | `> 80%` | **media**: apodrecimento é mais gradual | **Baixa/convenção prática**, ver ressalva abaixo |

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

**Não existe um número único e amplamente aceito equivalente ao de
temperatura/umidade do ar.** A literatura científica mede estresse
hídrico do tomateiro em **potencial matricial do solo** (kPa, ex.:
limiares de irrigação entre -38 e -58 kPa) ou **conteúdo volumétrico de
água**; nenhuma dessas unidades é o que o sensor capacitivo de baixo
custo do EcoVision mede.

O sensor usado (`edge/src/sensors/soil_moisture.py`, ADS1115) devolve
uma porcentagem **relativa à própria calibração** do sensor
(`SOIL_DRY_RAW`/`SOIL_WET_RAW` em `edge/src/config.py`: 0% = ponto
"totalmente seco" calibrado, 100% = ponto "totalmente molhado"
calibrado). Os limiares de 20%/80% usados aqui são uma **convenção
prática comum em projetos de irrigação com esse tipo de sensor**, não
um valor derivado de um estudo específico para tomate.

## Revisão futura

Os limiares de umidade do solo devem ser revisados assim que:
1. O sensor físico for calibrado de verdade em protoboard (pendência já
   registrada em `edge/README.md`, "Pendências de grupo").
2. Houver dados reais de campo (Sprint 9, validação em campo) para
   comparar o comportamento da planta com os valores lidos.

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
