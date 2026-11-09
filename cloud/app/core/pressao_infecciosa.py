"""
Pressão de infecção por fungos foliares, calculada a partir do histórico
de temperatura e umidade do ar.

Alternaria solani e Septoria lycopersici precisam de água líquida sobre a
folha por horas seguidas para infectar. Este módulo estima o molhamento
foliar e acumula a severidade diária (DSV) pelo submodelo de orvalho do
FAST (Madden; Pennypacker; MacNab, 1978, Phytopathology 68:1354-1358), base
do TOM-CAST. O resultado não altera o diagnóstico: serve para acrescentar
uma ressalva quando o ambiente claramente não sustentou uma doença fúngica.

Limitações:
- o molhamento é estimado pela umidade relativa (limiar de 90%, calibrado
  para Piracicaba por Sentelhas et al., 2008), que tende a subestimá-lo;
- irrigação sobre a folhagem não é detectada;
- o DHT22 mede o ar em um único ponto, não o microclima da folha;
- o DSV foi calibrado para Alternaria solani em campo aberto e clima
  temperado; para Septoria vale apenas o raciocínio qualitativo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

# Umidade relativa a partir da qual a folha é considerada molhada
# (Sentelhas et al., 2008, Piracicaba).
UMIDADE_MOLHAMENTO_PCT = 90.0

# Submodelo de orvalho do FAST (Madden et al., 1978): (temperatura mínima,
# temperatura máxima, horas de molhamento para DSV 1, 2, 3 e 4). None
# indica que a faixa não alcança DSV 4 na tabela publicada. As lacunas
# entre faixas da fonte são fechadas pela faixa seguinte, para que uma
# temperatura favorável nunca resulte em DSV 0.
_TABELA_FAST: tuple[tuple[float, float, tuple[int, int, int, int | None]], ...] = (
    (13.0, 18.0, (7, 16, 21, None)),
    (18.0, 21.0, (4, 9, 16, 23)),
    (21.0, 26.0, (3, 6, 13, 21)),
    (26.0, 29.0, (4, 9, 16, 23)),
)

# Fora de 13 a 29 °C a tabela não define valor; o módulo usa DSV 0
# (interpretação própria, não da fonte).
TEMPERATURA_MINIMA_TABELA_C = 13.0
TEMPERATURA_MAXIMA_TABELA_C = 29.0

# Tempo máximo que uma leitura representa ao integrar o histórico, para
# que lacunas de medição não sejam contadas como molhamento.
INTERVALO_MAXIMO_POR_LEITURA_H = 2.5

# Janela de acúmulo: as lesões aparecem dias após a infecção.
JANELA_PADRAO_DIAS = 14

# Cobertura mínima da janela para afirmar ausência de pressão.
COBERTURA_MINIMA_CONFIAVEL = 0.5

# Margem sobre o limiar de molhamento: a ressalva só é emitida quando a
# umidade ficou abaixo deste valor durante toda a janela, compensando o
# viés do proxy e o microclima da folha.
UMIDADE_NUNCA_PROXIMA_PCT = 85.0

# Classes que dependem de molhamento foliar. Para septoriose vale o
# raciocínio qualitativo, não o valor do DSV.
CLASSES_FUNGICAS = frozenset({"pinta_preta", "septoriose"})


@dataclass(frozen=True)
class DiaAvaliado:
    """Um dia do histórico, com o que foi medido e o DSV resultante."""

    dia: date
    horas_molhadas: float
    temperatura_media_molhada_c: float | None
    horas_observadas: float
    dsv: int


@dataclass(frozen=True)
class Pressao:
    """Resultado acumulado da janela."""

    dsv_acumulado: int
    horas_molhadas: float
    horas_observadas: float
    horas_esperadas: float
    umidade_maxima_pct: float | None
    dias: tuple[DiaAvaliado, ...]

    @property
    def cobertura(self) -> float:
        """Fração da janela que o dispositivo realmente mediu."""
        if self.horas_esperadas <= 0:
            return 0.0
        return min(1.0, self.horas_observadas / self.horas_esperadas)

    @property
    def cobertura_confiavel(self) -> bool:
        """Indica se houve medição suficiente para afirmar ausência de
        pressão (a presença pode ser afirmada com qualquer cobertura)."""
        return self.cobertura >= COBERTURA_MINIMA_CONFIAVEL


def dsv_do_dia(horas_molhadas: float, temperatura_media_c: float | None) -> int:
    """Converte horas de molhamento e temperatura média no DSV do dia,
    pela tabela do FAST. Devolve 0 fora da faixa coberta pela tabela."""
    if temperatura_media_c is None or horas_molhadas <= 0:
        return 0
    if not (TEMPERATURA_MINIMA_TABELA_C <= temperatura_media_c <= TEMPERATURA_MAXIMA_TABELA_C):
        return 0

    for minima, maxima, limiares in _TABELA_FAST:
        if minima <= temperatura_media_c < maxima or (
            maxima == TEMPERATURA_MAXIMA_TABELA_C and temperatura_media_c == maxima
        ):
            dsv = 0
            for nivel, limiar in enumerate(limiares, start=1):
                if limiar is not None and horas_molhadas >= limiar:
                    dsv = nivel
            return dsv
    return 0


def _para_utc(momento: datetime) -> datetime:
    """Normaliza o fuso, tratando datetime sem fuso como UTC.

    O PostgreSQL devolve datas com fuso e o SQLite dos testes, sem; o
    dispositivo grava em UTC.
    """
    return momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)


def calcular_pressao(
    leituras: list[tuple[datetime, float | None, float | None]],
    ate: datetime,
    janela_dias: int = JANELA_PADRAO_DIAS,
) -> Pressao:
    """Integra o histórico e devolve a pressão acumulada na janela.

    `leituras` é uma lista de (momento, temperatura_c, umidade_ar_pct), em
    qualquer ordem; leituras sem temperatura ou umidade são descartadas.
    Cada leitura representa o tempo até a seguinte, limitado por
    INTERVALO_MAXIMO_POR_LEITURA_H.
    """
    ate = _para_utc(ate)
    inicio = ate - timedelta(days=janela_dias)
    validas = sorted(
        (_para_utc(momento), temperatura, umidade)
        for momento, temperatura, umidade in leituras
        if temperatura is not None
        and umidade is not None
        and inicio <= _para_utc(momento) <= ate
    )

    por_dia: dict[date, dict[str, float]] = {}
    for indice, (momento, temperatura, umidade) in enumerate(validas):
        if indice + 1 < len(validas):
            bruto_h = (validas[indice + 1][0] - momento).total_seconds() / 3600.0
        else:
            bruto_h = (ate - momento).total_seconds() / 3600.0
        duracao_h = max(0.0, min(bruto_h, INTERVALO_MAXIMO_POR_LEITURA_H))
        if duracao_h <= 0:
            continue

        acumulado = por_dia.setdefault(
            momento.date(),
            {"molhadas": 0.0, "observadas": 0.0, "soma_temperatura": 0.0},
        )
        acumulado["observadas"] += duracao_h
        if umidade >= UMIDADE_MOLHAMENTO_PCT:
            acumulado["molhadas"] += duracao_h
            # Média ponderada pelo tempo, só nas horas molhadas, como pede
            # a tabela do FAST.
            acumulado["soma_temperatura"] += temperatura * duracao_h

    dias: list[DiaAvaliado] = []
    for dia in sorted(por_dia):
        valores = por_dia[dia]
        molhadas = valores["molhadas"]
        media = (valores["soma_temperatura"] / molhadas) if molhadas > 0 else None
        dias.append(
            DiaAvaliado(
                dia=dia,
                horas_molhadas=round(molhadas, 2),
                temperatura_media_molhada_c=(round(media, 1) if media is not None else None),
                horas_observadas=round(valores["observadas"], 2),
                dsv=dsv_do_dia(molhadas, media),
            )
        )

    return Pressao(
        dsv_acumulado=sum(dia.dsv for dia in dias),
        horas_molhadas=round(sum(dia.horas_molhadas for dia in dias), 2),
        horas_observadas=round(sum(dia.horas_observadas for dia in dias), 2),
        horas_esperadas=float(janela_dias * 24),
        umidade_maxima_pct=(max(u for _, _, u in validas) if validas else None),
        dias=tuple(dias),
    )


def avaliar_plausibilidade(classe_prevista: str, pressao: Pressao) -> tuple[str, str] | None:
    """Confronta o diagnóstico com o histórico ambiental.

    Devolve (titulo, descricao) quando há ressalva, ou None. Não altera a
    classe nem a confiança, e nunca orienta a deixar de pulverizar: apenas
    relata o que foi medido e pede conferência na estufa.

    A ressalva exige três condições:
    1. a classe é fúngica;
    2. houve medição suficiente na janela (cobertura_confiavel);
    3. a umidade ficou abaixo de UMIDADE_NUNCA_PROXIMA_PCT durante toda a
       janela.
    """
    if classe_prevista not in CLASSES_FUNGICAS:
        return None
    if pressao.dsv_acumulado > 0:
        return None
    if not pressao.cobertura_confiavel:
        return None
    if pressao.umidade_maxima_pct is None:
        return None
    if pressao.umidade_maxima_pct >= UMIDADE_NUNCA_PROXIMA_PCT:
        return None

    doenca = classe_prevista.replace("_", " ")
    return (
        "Confira esta suspeita de perto",
        f"A imagem sugere {doenca}, mas as condições medidas na estufa não "
        f"favoreceram infecção por fungo: em {len(pressao.dias)} dia(s) de "
        f"medição a umidade do ar ficou no máximo em "
        f"{pressao.umidade_maxima_pct:.0f}%, sem nenhum período estimado de "
        "folha molhada. Fungo foliar precisa de água líquida sobre a folha "
        "por horas seguidas para infectar, então vale conferir a planta de "
        "perto antes de tratar: amarelamento por falta de nutriente, falta "
        "d'água ou folha velha se parecem muito com mancha de doença. "
        "Atenção: se a irrigação molha as folhas, esta observação não se "
        "aplica, porque o sensor mede a umidade do ar e não a da folha."
    )
