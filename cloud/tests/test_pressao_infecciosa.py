"""
cloud/tests/test_pressao_infecciosa.py

O que este arquivo verifica, em português simples:

1. Que a tabela de severidade do FAST foi transcrita certo, célula por
   célula, incluindo as bordas (a hora exata em que o DSV sobe) e as
   faixas de temperatura em que a tabela não vale.
2. Que o histórico é integrado pelo TEMPO entre as leituras, e que uma
   lacuna longa (dispositivo desligado) não vira molhamento inventado.
3. Que o sistema só afirma "o ambiente contradiz este diagnóstico"
   quando mediu o suficiente para isso. Este é o teste que mais importa:
   um aviso errado aqui mandaria o produtor NÃO pulverizar uma lavoura
   de fato doente.
4. Que o módulo nunca altera o diagnóstico do modelo de imagem, só
   acrescenta contexto.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.pressao_infecciosa import (
    CLASSES_FUNGICAS,
    COBERTURA_MINIMA_CONFIAVEL,
    INTERVALO_MAXIMO_POR_LEITURA_H,
    UMIDADE_MOLHAMENTO_PCT,
    UMIDADE_NUNCA_PROXIMA_PCT,
    avaliar_plausibilidade,
    calcular_pressao,
    dsv_do_dia,
)

AGORA = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


def _serie(horas: int, umidade: float, temperatura: float, fim: datetime = AGORA):
    """Série de leituras de hora em hora terminando em `fim`."""
    return [
        (fim - timedelta(hours=horas - i), temperatura, umidade) for i in range(horas)
    ]


# --- 1. a tabela do FAST (Madden et al., 1978) ---


@pytest.mark.parametrize(
    "temperatura, horas, esperado",
    [
        # Faixa 13-17 graus: 0-6 / 7-15 / 16-20 / 21+ e sem DSV 4.
        (15.0, 6, 0),
        (15.0, 7, 1),
        (15.0, 15, 1),
        (15.0, 16, 2),
        (15.0, 20, 2),
        (15.0, 21, 3),
        (15.0, 24, 3),  # a fonte não define DSV 4 nesta faixa: teto é 3
        # Faixa 18-20: 0-3 / 4-8 / 9-15 / 16-22 / 23+
        (19.0, 3, 0),
        (19.0, 4, 1),
        (19.0, 9, 2),
        (19.0, 16, 3),
        (19.0, 23, 4),
        # Faixa 21-25, a mais permissiva: 0-2 / 3-5 / 6-12 / 13-20 / 21+
        (23.0, 2, 0),
        (23.0, 3, 1),
        (23.0, 6, 2),
        (23.0, 13, 3),
        (23.0, 21, 4),
        # Faixa 26-29: 0-3 / 4-8 / 9-15 / 16-22 / 23+
        (27.5, 3, 0),
        (27.5, 4, 1),
        (27.5, 23, 4),
    ],
)
def test_dsv_segue_a_tabela_publicada(temperatura, horas, esperado):
    assert dsv_do_dia(horas, temperatura) == esperado


@pytest.mark.parametrize("temperatura", [12.9, 29.1, 5.0, 40.0])
def test_fora_da_faixa_da_tabela_o_dsv_e_zero(temperatura):
    """Abaixo de 13 e acima de 29 graus a tabela não define valor, e o
    módulo devolve 0 em vez de extrapolar."""
    assert dsv_do_dia(24, temperatura) == 0


def test_sem_molhamento_nao_ha_dsv_por_mais_quente_que_esteja():
    assert dsv_do_dia(0, 23.0) == 0


def test_temperatura_ausente_nao_vira_dsv():
    assert dsv_do_dia(24, None) == 0


def test_buracos_entre_as_faixas_publicadas_nao_devolvem_zero():
    """A tabela publicada pula 17-18, 20-21 e 25-26 graus. Um buraco
    devolveria DSV 0 para temperatura plenamente favorável, que é o erro
    mais perigoso possível aqui."""
    for temperatura in (17.5, 20.5, 25.5):
        assert dsv_do_dia(24, temperatura) > 0, f"{temperatura} graus caiu num buraco"


# --- 2. integração do histórico ---


def test_horas_molhadas_saem_do_tempo_entre_leituras():
    leituras = _serie(horas=10, umidade=95.0, temperatura=23.0)
    pressao = calcular_pressao(leituras, ate=AGORA, janela_dias=1)
    assert pressao.horas_molhadas == pytest.approx(10.0, abs=0.1)
    assert pressao.dsv_acumulado > 0


def test_umidade_abaixo_do_limiar_nao_conta_como_molhamento():
    leituras = _serie(horas=10, umidade=UMIDADE_MOLHAMENTO_PCT - 0.1, temperatura=23.0)
    pressao = calcular_pressao(leituras, ate=AGORA, janela_dias=1)
    assert pressao.horas_molhadas == 0.0
    assert pressao.dsv_acumulado == 0


def test_lacuna_longa_nao_vira_molhamento_inventado():
    """Uma leitura úmida solta, seguida de 9 horas de dispositivo
    desligado, não pode virar 9 horas de folha molhada."""
    leituras = [
        (AGORA - timedelta(hours=12), 23.0, 95.0),
        (AGORA - timedelta(hours=3), 23.0, 50.0),
    ]
    pressao = calcular_pressao(leituras, ate=AGORA, janela_dias=1)
    assert pressao.horas_molhadas <= INTERVALO_MAXIMO_POR_LEITURA_H


def test_leitura_sem_sensor_e_descartada():
    """Sem temperatura ou sem umidade não dá para decidir nada, e a
    leitura some em vez de virar zero."""
    leituras = [
        (AGORA - timedelta(hours=2), None, 95.0),
        (AGORA - timedelta(hours=1), 23.0, None),
    ]
    pressao = calcular_pressao(leituras, ate=AGORA, janela_dias=1)
    assert pressao.horas_observadas == 0.0
    assert pressao.dsv_acumulado == 0


def test_temperatura_media_e_ponderada_so_pelas_horas_molhadas():
    """A tabela do FAST pede a temperatura DURANTE o molhamento, não a
    média do dia. Aqui o dia tem 2h molhadas a 23 graus e 8h secas a 35,
    e a média que importa é 23."""
    leituras = [
        (AGORA - timedelta(hours=10), 35.0, 50.0),
        (AGORA - timedelta(hours=4), 35.0, 50.0),
        (AGORA - timedelta(hours=2), 23.0, 95.0),
        (AGORA - timedelta(hours=1), 23.0, 95.0),
    ]
    pressao = calcular_pressao(leituras, ate=AGORA, janela_dias=1)
    (dia,) = pressao.dias
    assert dia.temperatura_media_molhada_c == pytest.approx(23.0, abs=0.1)


def test_leitura_fora_da_janela_e_ignorada():
    leituras = _serie(horas=5, umidade=95.0, temperatura=23.0, fim=AGORA - timedelta(days=30))
    pressao = calcular_pressao(leituras, ate=AGORA, janela_dias=14)
    assert pressao.horas_observadas == 0.0


# --- 3. quando o sistema pode (e não pode) contradizer o modelo ---


def test_nao_avisa_quando_mediu_pouco_demais():
    """ESTE É O TESTE QUE MAIS IMPORTA. Com o dispositivo desligado
    quase a janela inteira, afirmar que não houve molhamento mandaria o
    produtor deixar de pulverizar uma planta de fato doente."""
    leituras = _serie(horas=3, umidade=50.0, temperatura=23.0)
    pressao = calcular_pressao(leituras, ate=AGORA, janela_dias=14)
    assert pressao.cobertura < COBERTURA_MINIMA_CONFIAVEL
    assert avaliar_plausibilidade("pinta_preta", pressao) is None


def test_avisa_quando_mediu_bastante_e_nao_houve_molhamento():
    leituras = _serie(horas=24 * 10, umidade=65.0, temperatura=27.0, fim=AGORA)
    pressao = calcular_pressao(leituras, ate=AGORA, janela_dias=14)
    assert pressao.cobertura >= COBERTURA_MINIMA_CONFIAVEL
    assert pressao.dsv_acumulado == 0

    aviso = avaliar_plausibilidade("pinta_preta", pressao)
    assert aviso is not None
    titulo, descricao = aviso
    assert "pinta preta" in descricao
    assert "65%" in descricao  # relata a umidade máxima medida, não o limiar


def test_umidade_perto_do_limiar_nao_gera_ressalva():
    """A margem de UMIDADE_NUNCA_PROXIMA_PCT existe porque o proxy
    subestima o molhamento e a folha condensa antes do ar chegar a 90%.
    Com umidade raspando no limiar, calar é o certo."""
    leituras = _serie(horas=24 * 10, umidade=UMIDADE_NUNCA_PROXIMA_PCT + 0.1,
                      temperatura=27.0, fim=AGORA)
    pressao = calcular_pressao(leituras, ate=AGORA, janela_dias=14)
    assert pressao.dsv_acumulado == 0  # ainda abaixo dos 90% de molhamento
    assert avaliar_plausibilidade("pinta_preta", pressao) is None


def test_umidade_maxima_e_a_da_janela_nao_a_media():
    """Um único pico de umidade já basta para o módulo calar, mesmo que
    a média da janela seja baixa."""
    leituras = _serie(horas=24 * 10, umidade=60.0, temperatura=27.0, fim=AGORA)
    leituras.append((AGORA - timedelta(hours=50), 27.0, 88.0))
    pressao = calcular_pressao(leituras, ate=AGORA, janela_dias=14)
    assert pressao.umidade_maxima_pct == 88.0
    assert avaliar_plausibilidade("pinta_preta", pressao) is None


def test_a_ressalva_nunca_manda_deixar_de_pulverizar():
    """A cadeia de inferência tem elos fracos declarados no módulo
    (proxy de molhamento, sensor pontual, DSV de outra espécie,
    irrigação por cima invisível). Com essa base, desaconselhar
    tratamento pode custar a lavoura. O texto pede conferência."""
    leituras = _serie(horas=24 * 10, umidade=65.0, temperatura=27.0, fim=AGORA)
    pressao = calcular_pressao(leituras, ate=AGORA, janela_dias=14)
    _titulo, descricao = avaliar_plausibilidade("pinta_preta", pressao)

    minusculo = descricao.lower()
    for proibido in ("não pulverize", "nao pulverize", "evite pulverizar",
                     "dispense o fungicida", "não trate", "nao trate"):
        assert proibido not in minusculo, f"texto desaconselha tratamento: {proibido}"
    assert "conferir" in minusculo or "confira" in minusculo


def test_a_ressalva_declara_o_ponto_cego_da_irrigacao_por_cima():
    """Se a irrigação molha a folha, a conclusão não vale, e quem lê
    precisa saber disso sem ir ao código."""
    leituras = _serie(horas=24 * 10, umidade=65.0, temperatura=27.0, fim=AGORA)
    pressao = calcular_pressao(leituras, ate=AGORA, janela_dias=14)
    _titulo, descricao = avaliar_plausibilidade("pinta_preta", pressao)
    assert "irrigação" in descricao.lower()


def test_nao_avisa_quando_houve_molhamento_de_verdade():
    """Ambiente favorável mais diagnóstico de fungo é concordância, e
    concordância não precisa de alerta."""
    leituras = _serie(horas=24 * 10, umidade=95.0, temperatura=23.0, fim=AGORA)
    pressao = calcular_pressao(leituras, ate=AGORA, janela_dias=14)
    assert pressao.dsv_acumulado > 0
    assert avaliar_plausibilidade("pinta_preta", pressao) is None


@pytest.mark.parametrize("classe", sorted(CLASSES_FUNGICAS))
def test_as_duas_classes_fungicas_sao_avaliadas(classe):
    leituras = _serie(horas=24 * 10, umidade=65.0, temperatura=27.0, fim=AGORA)
    pressao = calcular_pressao(leituras, ate=AGORA, janela_dias=14)
    assert avaliar_plausibilidade(classe, pressao) is not None


@pytest.mark.parametrize("classe", ["saudavel", "imagem_inadequada", "deficiencia_nutricional"])
def test_classe_nao_fungica_nunca_gera_aviso(classe):
    """Deficiência nutricional não depende de molhamento foliar, então
    molhamento nenhum não é argumento contra ela."""
    leituras = _serie(horas=24 * 10, umidade=65.0, temperatura=27.0, fim=AGORA)
    pressao = calcular_pressao(leituras, ate=AGORA, janela_dias=14)
    assert avaliar_plausibilidade(classe, pressao) is None


# --- 4. o módulo é só contexto, nunca sobrescreve ---


def test_avaliar_devolve_texto_e_nunca_uma_classe():
    """A assinatura é a garantia: não há como este módulo trocar o
    diagnóstico, porque ele não devolve classe nem confiança."""
    leituras = _serie(horas=24 * 10, umidade=65.0, temperatura=27.0, fim=AGORA)
    pressao = calcular_pressao(leituras, ate=AGORA, janela_dias=14)
    aviso = avaliar_plausibilidade("pinta_preta", pressao)
    assert isinstance(aviso, tuple) and len(aviso) == 2
    assert all(isinstance(parte, str) for parte in aviso)


# --- 5. fusos misturados (Postgres com fuso, SQLite sem) ---------------


def test_leitura_sem_fuso_e_tratada_como_utc():
    """O Postgres devolve capturado_em COM fuso e o SQLite dos testes
    devolve SEM. Misturar levantava TypeError, e como quem chama captura
    excecao para nao derrubar a rota, a ressalva sumia sem sintoma."""
    ingenuas = [(m.replace(tzinfo=None), t, u) for m, t, u in
                _serie(horas=10, umidade=95.0, temperatura=23.0)]
    pressao = calcular_pressao(ingenuas, ate=AGORA, janela_dias=1)
    assert pressao.horas_molhadas == pytest.approx(10.0, abs=0.1)
    assert pressao.dsv_acumulado > 0


def test_mistura_de_leitura_com_e_sem_fuso_nao_quebra():
    leituras = _serie(horas=6, umidade=95.0, temperatura=23.0)
    leituras += [(m.replace(tzinfo=None), t, u) for m, t, u in
                 _serie(horas=6, umidade=95.0, temperatura=23.0,
                        fim=AGORA - timedelta(hours=12))]
    pressao = calcular_pressao(leituras, ate=AGORA, janela_dias=1)
    assert pressao.horas_observadas > 0


def test_ate_sem_fuso_tambem_funciona():
    leituras = _serie(horas=10, umidade=95.0, temperatura=23.0)
    pressao = calcular_pressao(leituras, ate=AGORA.replace(tzinfo=None), janela_dias=1)
    assert pressao.horas_molhadas == pytest.approx(10.0, abs=0.1)
