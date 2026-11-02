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
- Umidade do solo: ATENÇÃO, esta é a parte mais frágil. Não existe um
  número único e amplamente aceito na literatura agronômica para
  sensores capacitivos relativos (0-100% calibrados entre
  SOIL_DRY_RAW/SOIL_WET_RAW, ver edge/src/config.py). Os limiares
  abaixo são uma CONVENÇÃO PRÁTICA, só um ponto de partida, e devem ser
  recalibrados assim que o sensor físico for calibrado de verdade.

Relação com o resto do sistema:
- Usado por app/api/routes/diagnostico.py logo após gravar a leitura
  ambiental de cada captura.
"""

TEMPERATURA_MIN_C = 10.0
TEMPERATURA_MAX_C = 34.0

UMIDADE_AR_MAX_PCT = 90.0

UMIDADE_SOLO_MIN_PCT = 20.0  # abaixo disso: risco de seca (convenção prática)
UMIDADE_SOLO_MAX_PCT = 80.0  # acima disso: risco de solo encharcado (convenção prática)

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
