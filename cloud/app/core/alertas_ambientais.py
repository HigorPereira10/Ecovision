"""
cloud/app/core/alertas_ambientais.py

Limiares de risco ambiental para gerar alerta automático a partir das
leituras de sensor de cada captura (temperatura, umidade do ar, umidade
do solo). Cada número está documentado com a fonte de onde veio, ver
docs/decisions/0005-limiares-ambientais.md para a decisão completa e as
referências. Isso é importante para poder defender de onde veio cada
limiar na banca: nenhum valor abaixo foi inventado.

Resumo das fontes (ver o ADR para o texto completo):
- Temperatura e umidade do ar: Embrapa Hortaliças, "Clima"
  (https://www.embrapa.br/web/hortalicas/tomate-de-mesa/clima).
- Umidade do solo: o critério agronômico EXISTE e está citado, mas não
  é expresso em porcentagem. Para tomate de mesa tutorado, a Embrapa
  recomenda irrigar quando a TENSÃO da água no solo chega a 15-25 kPa,
  medida com tensiômetro (15 kPa nos 10 a 20 dias após o transplante,
  25 kPa depois disso):

    BRAGA, M.B.; FELTRIM, A.L.; BORGES, L.C. Irrigação. In: ZAMBOLIM,
    L.; QUEZADO-DUVAL, A.M. (org.). Produção integrada do tomateiro
    tutorado. Viçosa, MG: UFV, CEAD, 2022. cap. 7, p. 102-116. Na
    p. 105: "Normalmente, em cultivos de tomate de mesa, as tensões
    críticas de irrigação variam de 15 a 25kPa."

  Existe também um critério em PORCENTAGEM, e ele é o que dá o alvo da
  calibração:

    ALLEN, R.G.; PEREIRA, L.S.; RAES, D.; SMITH, M. Crop
    evapotranspiration: guidelines for computing crop water
    requirements. Roma: FAO, 1998. (FAO Irrigation and Drainage Paper,
    56). Tabela 22, linha do tomate: Zr 0,7-1,5 m, p 0,40, onde p é
    "average fraction of Total Available Soil Water (TAW) that can be
    depleted from the root zone before moisture stress (reduction in
    ET) occurs".

  Ou seja: irrigar quando 40% da água disponível foi consumida, o que é
  manter o solo acima de 60% dela.

  O SENSOR DESTE PROJETO NÃO MEDE NENHUMA DAS DUAS GRANDEZAS. Ele foi
  calibrado suspenso no AR (17468 bruto) e submerso em ÁGUA PURA (7179),
  ver edge/src/config.py, onde isso já está marcado como pendência.
  Então os 0-100% significam "umidade relativa entre ar seco e
  submerso", que não é tensão, não é umidade volumétrica e não é fração
  de água disponível.

  A diferença de escala é grande e dá para medir: o próprio capítulo,
  no exemplo trabalhado da p. 106 (raiz a 400 mm), converte 25 kPa em
  41,83% de umidade VOLUMÉTRICA, com capacidade de campo em 44,65%. A
  faixa útil toda tem menos de 3 pontos percentuais. Se os 20% abaixo
  fossem a mesma grandeza, o vaso estaria em murcha permanente quase
  sempre, e não está.

  Portanto UMIDADE_SOLO_MIN_PCT e MAX são LIMITE DE ALERTA deste
  sistema, não recomendação publicada, e é assim que o app os
  apresenta: a série de solo tem traço pontilhado, em vez do tracejado
  das outras duas, e a legenda diz que a linha marca onde o alerta
  dispara.

  O CAMINHO PARA VIRAR RECOMENDAÇÃO: recalibrar SOIL_DRY_RAW no PONTO
  DE MURCHA PERMANENTE e SOIL_WET_RAW na CAPACIDADE DE CAMPO, em vez de
  ar e água. Feito isso, os 0-100% passam a aproximar "porcentagem de
  água disponível" e o piso passa a ser 60%, citável direto da FAO-56.
  Ver docs/decisions/0005-limiares-ambientais.md, seção de calibração.

Relação com o resto do sistema:
- Usado por app/api/routes/diagnostico.py logo após gravar a leitura
  ambiental de cada captura.
"""

TEMPERATURA_MIN_C = 10.0
TEMPERATURA_MAX_C = 34.0

UMIDADE_AR_MAX_PCT = 90.0

# OS DOIS LIMIARES DE SOLO NÃO TÊM O MESMO RESPALDO, e a diferença foi
# medida em 2026-11-06. Ver docs/decisions/0005-limiares-ambientais.md,
# seção "Medição de campo de 2026-11-06".
#
# MAX (80%): MEDIDO. A capacidade de campo deste vaso é 76,0% (bruto
# 9648), identificada pelo patamar de 6 horas que seguiu a drenagem da
# rega de 03/11/2026. Água acima da capacidade de campo é água que o solo
# não retém: está drenando e ocupando os poros de que a raiz precisa para
# respirar. Os 80% ficam 4 pontos acima disso, então o alerta tem
# justificativa agronômica direta, e os 16 alertas já emitidos saíram todos
# nas horas seguintes a regas.
#
# MIN (20%): SEM RESPALDO E INALCANÇÁVEL. Em 367 leituras este alerta
# nunca disparou, porque o vaso opera entre 67% e 76%. Só dispararia com a
# sonda fora da terra, que é o caso que SOLO_PISO_SUSPEITO_PCT trata. O
# número certo depende do ponto de murcha permanente, que exige secar o
# vaso até a planta murchar e não é extraível da série (em 3 dias o solo
# caiu 8,4 pontos abaixo da capacidade de campo sem sinal de estresse).
#
# NÃO "CORRIJA" ISTO TROCANDO SOIL_WET_RAW PARA 9648. Mudar só o extremo
# molhado comprime a faixa de operação nos 11 pontos de cima da escala e
# faz saturado virar indistinguível de capacidade de campo, porque os dois
# passam a ser cortados em 100%. Isso destruiria o alerta de encharcamento,
# que é o que funciona. O ADR explica.
UMIDADE_SOLO_MIN_PCT = 20.0  # abaixo disso: risco de seca
UMIDADE_SOLO_MAX_PCT = 80.0  # acima disso: acima da capacidade de campo medida

# Capacidade de campo medida neste vaso, em 2026-11-06, a partir da série
# de 15 minutos. Não entra em comparação nenhuma: existe para o texto da
# documentação citar a medição sem repetir o número em três arquivos.
CAPACIDADE_DE_CAMPO_MEDIDA_PCT = 76.0

# Os dois critérios publicados, para o texto da documentação e das telas
# citarem sem repetir o número solto em três arquivos. NENHUM dos dois
# entra em comparação: o sensor não mede kPa nem água disponível.
TENSAO_CRITICA_IRRIGACAO_KPA = (15.0, 25.0)  # Braga et al., 2022, p. 105
AGUA_DISPONIVEL_MINIMA_PCT = 60.0  # FAO-56, Tabela 22 (p = 0,40 para tomate)

# Leitura de solo em exatamente 0,0% quase nunca é solo seco de verdade.
# O percentual vem de _clamp(0, 100) sobre o valor bruto do ADS1115
# (edge/src/sensors/soil_moisture.py), então 0,0% é o PISO da escala:
# significa "leu no limite seco ou além dele". Isso acontece com o
# sensor fora da terra, com a haste solta, com o conector frouxo, ou
# com SOIL_DRY_RAW mal calibrado, e não com solo de estufa irrigada,
# que não chega a zero absoluto.
#
# Decisão do grupo em 2026-10-11, depois do primeiro ciclo real: tratar
# esse caso como SUSPEITA DE SENSOR, severidade média, em vez de alerta
# crítico de seca. Dizer "risco de estresse hídrico" quando o sensor
# está pendurado no ar manda o produtor irrigar sem motivo, e ensina o
# grupo a ignorar o alerta de seca justamente antes da banca.
#
# O NÚMERO AGORA É MEDIDO, não mais zero exato.
#
# Em 2026-11-02 a haste foi retirada da terra (para os fios saírem do
# enquadramento da câmera) e o ADS1115 passou a ler 17239 a 17307 em
# bruto, que na calibração do ecovision-pi-01 dá 1,7% a 2,1%. Ou seja:
# sensor fora da terra NÃO devolve 0,0 exato, devolve a vizinhança do
# extremo seco. Com o piso em zero, essas leituras passavam direto e
# caíam em UMIDADE_SOLO_MIN_PCT, disparando "Solo seco" com severidade
# ALTA a cada ciclo. É o falso alarme que a nota acima existia para
# evitar, e ele aconteceu.
#
# POR QUE 4 E NÃO 5: o grupo já decidiu, e está fixado em
# test_solo_baixo_mas_acima_de_zero_continua_sendo_seca, que 5% é
# leitura PLAUSÍVEL de solo seco de verdade e tem que continuar gerando
# alerta alto. O piso fica logo abaixo disso para não engolir seca real.
#
# A margem acima do sensor solto é estreita (2,1% medido contra 4,0% de
# piso) porque as duas faixas são vizinhas mesmo. Se um dia um sensor
# fora da terra ler acima de 4%, suba este número E o do teste juntos,
# nunca só um.
SOLO_PISO_SUSPEITO_PCT = 4.0


def avaliar_risco_ambiental(
    temperatura_c: float | None,
    umidade_ar_pct: float | None,
    umidade_solo_pct: float | None,
) -> list[tuple[str, str, str]]:
    """Retorna uma lista de (titulo, descricao, severidade), uma para
    cada risco identificado nas leituras. Pode devolver mais de um risco
    ao mesmo tempo, ou nenhum. Uma leitura ausente (sensor falhou, ver
    edge/src/main.py) é sempre ignorada e nunca gera alerta sozinha.

    Severidade ("alta" | "media"): "alta" para riscos com potencial de
    perda rápida da planta (calor/frio extremo, estresse hídrico por
    seca); "media" para riscos de progressão mais lenta (favorecem
    doença, mas não matam a planta diretamente) e para suspeita de
    falha de sensor, que pede conferência e não ação no cultivo."""
    alertas: list[tuple[str, str, str]] = []

    if temperatura_c is not None and not (TEMPERATURA_MIN_C <= temperatura_c <= TEMPERATURA_MAX_C):
        alertas.append((
            "Temperatura fora da faixa segura",
            f"Temperatura de {temperatura_c:.1f}°C fora da faixa de tolerância do "
            f"tomateiro ({TEMPERATURA_MIN_C:.0f}-{TEMPERATURA_MAX_C:.0f}°C).",
            "alta",
        ))

    if umidade_ar_pct is not None and umidade_ar_pct > UMIDADE_AR_MAX_PCT:
        alertas.append((
            "Umidade do ar muito alta",
            f"Umidade do ar em {umidade_ar_pct:.1f}%, acima de {UMIDADE_AR_MAX_PCT:.0f}%. "
            f"Isso favorece o surgimento de mofo e fungos nas folhas.",
            "media",
        ))

    if umidade_solo_pct is not None:
        if umidade_solo_pct <= SOLO_PISO_SUSPEITO_PCT:
            # Antes de falar em seca, desconfiar do sensor. Ver a nota
            # em SOLO_PISO_SUSPEITO_PCT para o porquê.
            alertas.append((
                "Verifique o sensor de umidade do solo",
                f"A leitura de umidade do solo voltou em {umidade_solo_pct:.1f}%, "
                f"no piso da escala (abaixo de {SOLO_PISO_SUSPEITO_PCT:.0f}%). "
                "Isso costuma indicar sensor fora da terra, haste solta, "
                "conector frouxo ou calibração pendente, e não solo seco. "
                "Confira a instalação antes de irrigar.",
                "media",
            ))
        elif umidade_solo_pct < UMIDADE_SOLO_MIN_PCT:
            alertas.append((
                "Solo seco",
                f"Umidade do solo em {umidade_solo_pct:.1f}%, abaixo de "
                f"{UMIDADE_SOLO_MIN_PCT:.0f}%. Risco de estresse hídrico.",
                "alta",
            ))
        elif umidade_solo_pct > UMIDADE_SOLO_MAX_PCT:
            alertas.append((
                "Solo encharcado",
                f"Umidade do solo em {umidade_solo_pct:.1f}%, acima de "
                f"{UMIDADE_SOLO_MAX_PCT:.0f}%. Risco de apodrecimento de raiz ou fungo.",
                "media",
            ))

    return alertas
