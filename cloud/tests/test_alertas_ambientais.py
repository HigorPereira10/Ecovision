"""
Testes de app/core/alertas_ambientais.py: nenhum alerta dentro da faixa,
alerta correto para cada variável fora da faixa, mais de um alerta ao
mesmo tempo e leituras ausentes ignoradas.
"""

from app.core.alertas_ambientais import avaliar_risco_ambiental


def test_leituras_dentro_da_faixa_nao_gera_alerta():
    assert avaliar_risco_ambiental(24.0, 65.0, 50.0) == []


def test_temperatura_fora_da_faixa_gera_alerta():
    alertas = avaliar_risco_ambiental(5.0, 65.0, 50.0)
    assert len(alertas) == 1
    assert "Temperatura" in alertas[0][0]

    alertas = avaliar_risco_ambiental(40.0, 65.0, 50.0)
    assert len(alertas) == 1
    assert "Temperatura" in alertas[0][0]


def test_umidade_do_ar_muito_alta_gera_alerta():
    alertas = avaliar_risco_ambiental(24.0, 95.0, 50.0)
    assert len(alertas) == 1
    assert "Umidade do ar" in alertas[0][0]


def test_solo_seco_e_solo_encharcado_geram_alertas_diferentes():
    alertas_seco = avaliar_risco_ambiental(24.0, 65.0, 10.0)
    assert len(alertas_seco) == 1
    assert "seco" in alertas_seco[0][0].lower()

    alertas_encharcado = avaliar_risco_ambiental(24.0, 65.0, 90.0)
    assert len(alertas_encharcado) == 1
    assert "encharcado" in alertas_encharcado[0][0].lower()


def test_solo_em_zero_vira_suspeita_de_sensor_e_nao_alerta_de_seca():
    """Leitura no piso da escala (sensor fora da terra) gera alerta de
    verificação do sensor, e não de solo seco."""
    alertas = avaliar_risco_ambiental(24.0, 65.0, 0.0)

    assert len(alertas) == 1
    titulo, descricao, severidade = alertas[0]
    assert "sensor" in titulo.lower()
    assert "seco" not in titulo.lower(), "nao pode mais falar em seca aqui"
    assert severidade == "media", "suspeita de sensor pede conferencia, nao acao no cultivo"
    assert "antes de irrigar" in descricao


def test_solo_baixo_mas_acima_de_zero_continua_sendo_seca():
    """A guarda do zero não pode engolir a seca de verdade: 5% é leitura
    plausível de solo seco, e tem que continuar gerando alerta alto."""
    alertas = avaliar_risco_ambiental(24.0, 65.0, 5.0)

    assert len(alertas) == 1
    titulo, _, severidade = alertas[0]
    assert "seco" in titulo.lower()
    assert severidade == "alta"


def test_multiplos_riscos_simultaneos():
    alertas = avaliar_risco_ambiental(40.0, 95.0, 10.0)
    assert len(alertas) == 3


def test_leitura_ausente_nao_gera_alerta_por_conta_propria():
    assert avaliar_risco_ambiental(None, None, None) == []


def test_sensor_fora_da_terra_nao_vira_alerta_de_seca():
    """Um sensor fora da terra lê cerca de 2%, não 0,0% exato; essas
    leituras também geram alerta de verificação do sensor."""
    for leitura in (1.7, 2.1, 3.9):
        alertas = avaliar_risco_ambiental(24.0, 65.0, leitura)
        assert len(alertas) == 1, f"{leitura}% gerou {len(alertas)} alertas"
        titulo, descricao, severidade = alertas[0]
        assert "verifique o sensor" in titulo.lower(), f"{leitura}% virou {titulo!r}"
        assert severidade == "media", "suspeita de sensor pede conferencia, nao acao"
        assert f"{leitura:.1f}%" in descricao, "a descricao mostra a leitura real"
