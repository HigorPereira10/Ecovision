"""
Limiares ambientais para os alertas gerados a partir das leituras.

- Temperatura: fora da faixa de 10 a 34 °C que o tomateiro tolera
  (Embrapa Hortaliças, Tomate de mesa: clima).
- Umidade do ar: acima de 90%, quando a folha permanece úmida por mais
  tempo e o risco de fungos aumenta.
- Umidade do solo: os critérios agronômicos publicados são a tensão de 15
  a 25 kPa (BRAGA; FELTRIM; BORGES, 2022, p. 105) e a manutenção acima de
  60% da água disponível (FAO-56, Tabela 22). O sensor do projeto não mede
  nenhuma dessas grandezas: sua escala vai do sensor seco ao submerso.
  Por isso os limiares de solo são limites de alerta do sistema, não
  recomendações. Recalibrar SOIL_DRY_RAW no ponto de murcha permanente e
  SOIL_WET_RAW na capacidade de campo aproximaria a escala da fração de
  água disponível.
"""

TEMPERATURA_MIN_C = 10.0
TEMPERATURA_MAX_C = 34.0

UMIDADE_AR_MAX_PCT = 90.0

# Solo:
# - máximo (80%): acima da capacidade de campo medida no vaso monitorado
#   (76,0%), quando a água drena e ocupa os poros de que a raiz precisa;
# - mínimo (20%): sem respaldo agronômico; na calibração atual fica abaixo
#   da faixa em que o vaso opera (67% a 76%).
# Alterar só SOIL_WET_RAW para o valor da capacidade de campo comprimiria
# a escala e anularia o alerta de encharcamento; os dois extremos devem
# ser recalibrados juntos.
UMIDADE_SOLO_MIN_PCT = 20.0  # abaixo disso: risco de seca
UMIDADE_SOLO_MAX_PCT = 80.0  # acima da capacidade de campo medida

# Capacidade de campo medida no vaso monitorado, para referência em textos.
CAPACIDADE_DE_CAMPO_MEDIDA_PCT = 76.0

# Critérios publicados, para referência em textos; não são usados em
# comparações, pois o sensor não mede essas grandezas.
TENSAO_CRITICA_IRRIGACAO_KPA = (15.0, 25.0)  # Braga et al., 2022, p. 105
AGUA_DISPONIVEL_MINIMA_PCT = 60.0  # FAO-56, Tabela 22 (p = 0,40 para tomate)

# Leituras no piso da escala indicam falha de instalação (sensor fora da
# terra, haste solta, conector frouxo ou calibração incorreta), não solo
# seco: um sensor fora da terra lê cerca de 2%. Abaixo deste valor, o
# alerta é de verificação do sensor, com severidade média. Leituras de 5%
# continuam gerando alerta de solo seco.
SOLO_PISO_SUSPEITO_PCT = 4.0


def avaliar_risco_ambiental(
    temperatura_c: float | None,
    umidade_ar_pct: float | None,
    umidade_solo_pct: float | None,
) -> list[tuple[str, str, str]]:
    """Devolve uma lista de (titulo, descricao, severidade) com os riscos
    identificados nas leituras, possivelmente vazia. Leituras ausentes são
    ignoradas.

    Severidade "alta": risco de perda rápida (temperatura fora da faixa,
    solo seco). "media": risco de progressão lenta (umidade alta, solo
    encharcado) e suspeita de falha do sensor."""
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
            # Leitura no piso da escala: suspeita de falha do sensor.
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
