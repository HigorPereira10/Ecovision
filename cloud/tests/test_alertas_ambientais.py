"""
cloud/tests/test_alertas_ambientais.py

O que este arquivo verifica, em português simples:

As regras de "risco ambiental" (temperatura, umidade do ar e umidade do
solo fora da faixa considerada segura para o tomateiro). Ver
docs/decisions/0005-limiares-ambientais.md para saber de onde vieram
esses números. Este teste confere que a função de avaliação:
- não gera nada quando as leituras estão dentro da faixa ideal;
- gera o alerta certo quando cada variável, isoladamente, sai da faixa;
- consegue gerar mais de um alerta ao mesmo tempo (ex.: calor e solo
  seco juntos);
- ignora leituras ausentes (sensor que falhou não deveria gerar alerta
  sozinho, ver edge/src/main.py).
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
    """Encontrado no primeiro ciclo real, em 2026-10-11: o Pi na bancada,
    com o sensor pendurado no ar, gerou um alerta CRÍTICO de "Solo seco,
    risco de estresse hídrico". Mandar irrigar por causa de um sensor
    fora da terra é pior do que não alertar, porque ensina o produtor (e
    o grupo) a ignorar o alerta de seca."""
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
    """Em 2026-11-02 a haste foi retirada da terra e o ADS1115 passou a
    ler 1,7% a 2,1%, nao 0,0% exato. Com o piso antigo em zero exato,
    isso caia em UMIDADE_SOLO_MIN_PCT e disparava "Solo seco" com
    severidade ALTA a cada ciclo: o falso alarme que manda irrigar uma
    planta que nao precisa, e que ensina o grupo a ignorar o alerta de
    seca."""
    for leitura in (1.7, 2.1, 3.9):
        alertas = avaliar_risco_ambiental(24.0, 65.0, leitura)
        assert len(alertas) == 1, f"{leitura}% gerou {len(alertas)} alertas"
        titulo, descricao, severidade = alertas[0]
        assert "verifique o sensor" in titulo.lower(), f"{leitura}% virou {titulo!r}"
        assert severidade == "media", "suspeita de sensor pede conferencia, nao acao"
        assert f"{leitura:.1f}%" in descricao, "a descricao mostra a leitura real"
