"""
cloud/app/core/pressao_infecciosa.py

Calcula a PRESSÃO DE INFECÇÃO por fungo foliar a partir do histórico de
temperatura e umidade do ar, para dizer se as condições da estufa
sustentam, ou não, um diagnóstico de doença fúngica.

POR QUE ISTO EXISTE
-------------------
O classificador de imagem tem um espaço de rótulos fechado e atribui
toda entrada a uma das classes conhecidas. Medido em 2026-11-01, no
ecovision-pi-01: quatro capturas da mesma planta, com amarelamento
internerval generalizado, saíram como `pinta_preta` com até 77,8% de
confiança. A planta não tem pinta preta; ela tem sintoma que o modelo
não sabe nomear, e a literatura de extensão registra essa confusão como
regra, não exceção, porque deficiência nutricional e doença fúngica
produzem os mesmos amarelamento e necrose.

O que o olho do modelo não resolve, a estufa resolve: *Alternaria
solani* e *Septoria lycopersici* precisam de água líquida sobre a folha
por horas seguidas para germinar e penetrar o tecido. Sem molhamento
foliar não há infecção, por mais que a mancha se pareça com uma.

Este módulo é a metade de IoT do trabalho cobrindo a metade de visão.
Ele NÃO corrige o diagnóstico: só informa se o ambiente o sustenta. A
decisão de nunca sobrescrever o modelo é deliberada, ver
`avaliar_plausibilidade`.

O MODELO FAST / TOM-CAST
------------------------
A tabela abaixo é o submodelo de orvalho do FAST (Forecasting
Alternaria solani on Tomato), de Madden, Pennypacker e MacNab, 1978,
Phytopathology 68:1354-1358, que é a base do TOM-CAST usado em campo
até hoje. Cada dia recebe um valor de severidade (DSV) de 0 a 4,
conforme as horas de molhamento foliar e a temperatura média durante o
molhamento. Os DSV diários se acumulam, e o acúmulo é o que dispara
recomendação de pulverização (os limiares de pulverização variam por
região, de 15 a 35 DSV, e NÃO são usados aqui: este módulo mede
pressão, não recomenda defensivo).

MOLHAMENTO FOLIAR É ESTIMADO, NÃO MEDIDO
----------------------------------------
Não existe sensor de molhamento foliar no dispositivo. O proxy usado é
umidade relativa acima de um limiar, que é o método mais simples da
literatura e tem precisão aceitável quando calibrado localmente.

O limiar de 90% não foi escolhido por conveniência: Sentelhas et al.
(2008), comparando quatro locais, calibraram 83% em Ames (EUA), 85% em
Elora (Canadá), 92% em Florença (Itália) e 90% em PIRACICABA (Brasil).
Para uma estufa no Brasil, 90% é o valor medido na condição mais
próxima da nossa.

LIMITAÇÃO: o estudo mostra que o proxy SUBESTIMA o molhamento em
Piracicaba. Então este módulo erra para o lado conservador: quando ele
diz que houve pressão, houve; quando diz que não houve, pode ter havido
um pouco. Isso importa para como a saída é lida, ver
`avaliar_plausibilidade`.

TRÊS PONTOS CEGOS QUE PRECISAM ESTAR À VISTA
--------------------------------------------
1. IRRIGAÇÃO POR CIMA. Se alguém molha a folhagem, a folha fica
   encharcada com o ar a 60% de umidade e este módulo não vê nada. O
   proxy enxerga orvalho e condensação, não mangueira. Em estufa com
   irrigação foliar, a saída deste módulo NÃO VALE.

2. MICROCLIMA DA FOLHA. O DHT22 mede o ar num ponto só. Por
   resfriamento radiativo noturno, uma folha pode condensar com o ar
   ambiente bem abaixo de 90%. Por isso existe a margem de
   UMIDADE_NUNCA_PROXIMA_PCT: só afirmamos ausência quando a umidade
   ficou longe do limiar a janela inteira, não quando passou raspando.

3. O DSV É DE Alternaria solani, EM CAMPO ABERTO, EM CLIMA TEMPERADO.
   Madden et al. calibraram para tomate de campo nos Estados Unidos.
   Adaptações para outras regiões mudaram os limiares (Espanha,
   Noruega, China). Estufa brasileira não foi validada por ninguém, e
   para Septoria lycopersici o número não vale de jeito nenhum, só o
   raciocínio qualitativo de que sem água líquida não há infecção.

É por causa destes três que `avaliar_plausibilidade` devolve uma
RESSALVA, e não um veredito, e nunca diz ao produtor para deixar de
pulverizar.

Relação com o resto do sistema:
- Consome `leituras_ambientais` (app/db/models.py), as mesmas leituras
  que app/core/alertas_ambientais.py já usa para alerta instantâneo. A
  diferença é a janela: lá é a leitura de agora, aqui é o histórico.
- Pensado para ser chamado por app/api/routes/diagnostico.py, junto do
  diagnóstico, e por app/api/routes/historico.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

# Umidade relativa a partir da qual se considera a folha molhada.
# Ver "MOLHAMENTO FOLIAR É ESTIMADO" no topo: 90% é o limiar calibrado
# para Piracicaba em Sentelhas et al. (2008).
UMIDADE_MOLHAMENTO_PCT = 90.0

# Tabela do submodelo de orvalho do FAST (Madden et al., 1978).
#
# Cada entrada é (temperatura mínima, temperatura máxima, limiares em
# horas de molhamento para atingir DSV 1, 2, 3 e 4). `None` no último
# significa que a faixa não alcança DSV 4 na tabela publicada: a linha
# de 13 a 17 graus termina em "21+" e a célula de DSV 4 está vazia na
# fonte, então o teto daquela faixa é 3.
#
# As faixas publicadas deixam buracos (17 a 18, 20 a 21, 25 a 26 graus).
# Aqui elas são fechadas pela borda inferior da faixa seguinte, porque
# um buraco devolveria DSV 0 para temperatura plenamente favorável, que
# é o erro mais perigoso que este módulo poderia cometer.
_TABELA_FAST: tuple[tuple[float, float, tuple[int, int, int, int | None]], ...] = (
    (13.0, 18.0, (7, 16, 21, None)),
    (18.0, 21.0, (4, 9, 16, 23)),
    (21.0, 26.0, (3, 6, 13, 21)),
    (26.0, 29.0, (4, 9, 16, 23)),
)

# Fora de 13 a 29 graus a tabela não define valor. Tratamos como DSV 0:
# abaixo de 13 o fungo praticamente não se desenvolve, e acima de 29 a
# folha seca rápido demais para a infecção se estabelecer. A fonte não
# dá orientação para essas faixas, então isto é interpretação nossa e
# está marcado como tal.
TEMPERATURA_MINIMA_TABELA_C = 13.0
TEMPERATURA_MAXIMA_TABELA_C = 29.0

# Quanto tempo uma única leitura pode "representar" ao integrar o
# histórico. Sem este teto, uma lacuna de 9 horas com o dispositivo
# desligado viraria 9 horas de molhamento por causa de uma leitura
# úmida solta antes dela. Com captura a cada 2h, 2,5h dá folga para
# atraso de cron sem inventar tempo que ninguém mediu.
INTERVALO_MAXIMO_POR_LEITURA_H = 2.5

# Janela padrão de acúmulo. Lesão de pinta preta aparece dias depois da
# infecção, então a pergunta certa não é "está chovendo agora", e sim
# "houve molhamento nas semanas que antecederam este sintoma".
JANELA_PADRAO_DIAS = 14

# Abaixo desta fração de cobertura a janela tem buraco grande demais
# para afirmar ausência de pressão. Ver `Pressao.cobertura_confiavel`.
COBERTURA_MINIMA_CONFIAVEL = 0.5

# Margem que absorve o viés conhecido do proxy. Sentelhas et al. mediram
# que umidade relativa SUBESTIMA o molhamento em Piracicaba, e o
# microclima da folha pode condensar com o ar abaixo de 90%. Então não
# basta nenhuma leitura ter cruzado os 90%: a umidade precisa ter ficado
# LONGE do limiar a janela inteira.
#
# Com isso a ressalva só sai quando o caso é folgado. No histórico desta
# estufa até 2026-11-01 a umidade máxima registrada foi 78,9%, ou seja,
# 6 pontos abaixo desta margem e 11 abaixo do limiar de molhamento.
UMIDADE_NUNCA_PROXIMA_PCT = 85.0

# Classes do modelo que dependem de molhamento foliar para infectar.
# `septoriose` entra porque Septoria lycopersici também exige água
# líquida sobre a folha, mas ATENÇÃO: o DSV é calibrado para Alternaria
# solani, não para Septoria. Para ela vale o raciocínio qualitativo
# (sem molhamento não há infecção), não o número.
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
        """Houve medição suficiente para afirmar AUSÊNCIA de pressão?

        Presença de pressão é afirmável com qualquer cobertura: se o
        molhamento foi medido, ele aconteceu. Ausência é que não é,
        porque o que não foi medido pode ter acontecido no escuro.
        """
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
    """Normaliza o fuso, tratando datetime ingênuo como UTC.

    POR QUE ISTO EXISTE: o Postgres devolve `capturado_em` COM fuso,
    porque a coluna é DateTime(timezone=True), e o SQLite dos testes
    devolve SEM. Misturar os dois levanta
    `TypeError: can't compare offset-naive and offset-aware datetimes`.

    O erro era especialmente ruim porque não aparecia: quem chama este
    módulo (app/api/routes/diagnostico.py) captura exceção para nunca
    derrubar a rota, então a ressalva simplesmente deixava de existir,
    sem sintoma nenhum. Tratar aqui é o que mantém o módulo igual nos
    dois bancos.

    UTC é a suposição certa porque o dispositivo grava em UTC
    (edge/src/fila/offline_queue.py) e é em UTC que o banco guarda.
    """
    return momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)


def calcular_pressao(
    leituras: list[tuple[datetime, float | None, float | None]],
    ate: datetime,
    janela_dias: int = JANELA_PADRAO_DIAS,
) -> Pressao:
    """Integra o histórico e devolve a pressão acumulada na janela.

    `leituras` é uma lista de (momento, temperatura_c, umidade_ar_pct),
    em qualquer ordem. Leitura com temperatura ou umidade ausente é
    descartada: sem os dois não dá para decidir nem se a folha estava
    molhada nem em que temperatura.

    Cada leitura representa o tempo até a leitura SEGUINTE, limitado por
    INTERVALO_MAXIMO_POR_LEITURA_H. É esse trecho que conta como
    molhado, ou não, conforme a umidade daquela leitura.
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
            # Média PONDERADA pelo tempo, e só sobre as horas molhadas:
            # a tabela do FAST pede a temperatura durante o molhamento,
            # não a média do dia inteiro.
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
    """Confronta o diagnóstico do modelo com o que a estufa registrou.

    Devolve (titulo, descricao) quando há uma ressalva a fazer, ou None
    quando não há.

    O QUE ESTA FUNÇÃO NÃO FAZ, DE PROPÓSITO
    ---------------------------------------
    Não altera a classe nem a confiança. Sobrescrever o modelo
    esconderia a discordância, e a discordância é a informação útil.

    Também NÃO diz para deixar de pulverizar, e isso é o ponto mais
    importante do módulo inteiro. A cadeia que leva até aqui tem elos
    fracos declarados no topo do arquivo: molhamento é estimado por
    umidade do ar, o sensor mede um ponto só, o DSV é de outra espécie
    em outro clima, e irrigação por cima é invisível para nós. Dizer
    "não pulverize" com base nisso pode custar a lavoura.

    O que o texto faz é relatar o que foi MEDIDO, dizer por que isso é
    relevante, e pedir conferência presencial. Quem decide é quem está
    na estufa e pode virar a folha.

    TRÊS CONDIÇÕES, TODAS OBRIGATÓRIAS
    ----------------------------------
    1. A classe é fúngica. Deficiência nutricional não depende de
       molhamento, então molhamento nenhum não é argumento contra ela.
    2. Houve medição suficiente (ver `cobertura_confiavel`). Ausência de
       dado não é dado.
    3. A umidade ficou LONGE do limiar a janela inteira, não só abaixo
       dele (ver UMIDADE_NUNCA_PROXIMA_PCT). Isto absorve o viés
       conhecido do proxy.

    Presença de pressão com diagnóstico de doença é concordância, e
    concordância não precisa de ressalva.
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
