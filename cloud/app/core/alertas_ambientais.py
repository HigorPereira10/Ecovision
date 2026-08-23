"""
cloud/app/core/alertas_ambientais.py

Limiares de risco ambiental para gerar alerta automático a partir das
leituras de sensor de cada captura (temperatura, umidade do ar, umidade
do solo). Documentado com a fonte de cada número — ver
docs/decisions/0005-limiares-ambientais.md para a decisão completa e as
referências, importante pra poder defender de onde veio cada limiar na
banca, não são valores inventados.

Resumo das fontes (ver o ADR para o texto completo):
- Temperatura e umidade do ar: Embrapa Hortaliças, "Clima"
  (https://www.embrapa.br/web/hortalicas/tomate-de-mesa/clima).
- Umidade do solo: SEM um número único e amplamente aceito na
  literatura agronômica para sensores capacitivos relativos (0-100%
  calibrados entre SOIL_DRY_RAW/SOIL_WET_RAW, ver edge/src/config.py) —
  os limiares abaixo são uma CONVENÇÃO PRÁTICA (ponto de partida), a
  recalibrar quando o sensor físico estiver calibrado de verdade.

Relação com o resto do sistema:
- Usado por app/api/routes/diagnostico.py logo após gravar a leitura
  ambiental de cada captura.
"""

TEMPERATURA_MIN_C = 10.0
TEMPERATURA_MAX_C = 34.0

UMIDADE_AR_MAX_PCT = 90.0

UMIDADE_SOLO_MIN_PCT = 20.0  # abaixo disso: risco de seca (convenção prática)
UMIDADE_SOLO_MAX_PCT = 80.0  # acima disso: risco de solo encharcado (convenção prática)


def avaliar_risco_ambiental(
    temperatura_c: float | None,
    umidade_ar_pct: float | None,
    umidade_solo_pct: float | None,
) -> list[tuple[str, str, str]]:
    """Retorna uma lista de (titulo, descricao, severidade), uma para
    cada risco identificado nas leituras — pode ser mais de um ao mesmo
    tempo, ou nenhum. Leitura ausente (sensor falhou, ver
    edge/src/main.py) é ignorada, nunca gera alerta por conta própria.

    Severidade ("alta" | "media"): "alta" para riscos com potencial de
    perda rápida da planta (calor/frio extremo, estresse hídrico por
    seca); "media" para riscos de progressão mais lenta (favorecem
    doença, mas não matam a planta diretamente)."""
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
            f"Umidade do ar em {umidade_ar_pct:.1f}%, acima de {UMIDADE_AR_MAX_PCT:.0f}% "
            f"— favorece o surgimento de mofo/fungos nas folhas.",
            "media",
        ))

    if umidade_solo_pct is not None:
        if umidade_solo_pct < UMIDADE_SOLO_MIN_PCT:
            alertas.append((
                "Solo seco",
                f"Umidade do solo em {umidade_solo_pct:.1f}%, abaixo de "
                f"{UMIDADE_SOLO_MIN_PCT:.0f}% — risco de estresse hídrico.",
                "alta",
            ))
        elif umidade_solo_pct > UMIDADE_SOLO_MAX_PCT:
            alertas.append((
                "Solo encharcado",
                f"Umidade do solo em {umidade_solo_pct:.1f}%, acima de "
                f"{UMIDADE_SOLO_MAX_PCT:.0f}% — risco de apodrecimento de raiz/fungo.",
                "media",
            ))

    return alertas
