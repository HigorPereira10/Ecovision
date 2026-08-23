"""
cloud/tests/test_alertas_ambientais.py

O que este arquivo verifica, em português simples:

As regras de "risco ambiental" (temperatura, umidade do ar e umidade do
solo fora da faixa considerada segura para o tomateiro) — ver
docs/decisions/0005-limiares-ambientais.md para de onde vieram esses
números. Este teste confere que a função de avaliação:
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


def test_multiplos_riscos_simultaneos():
    alertas = avaliar_risco_ambiental(40.0, 95.0, 10.0)
    assert len(alertas) == 3


def test_leitura_ausente_nao_gera_alerta_por_conta_propria():
    assert avaliar_risco_ambiental(None, None, None) == []
