"""
cloud/tests/test_alertas_dispositivo.py

O que este arquivo verifica, em português simples:

A detecção de "dispositivo inativo" (falha silenciosa: sem novas
capturas por muito tempo). Ver
docs/decisions/0008-deteccao-dispositivo-inativo.md para de onde vieram
os limiares de 4h/8h. Este teste confere que a função:
- não gera nada enquanto o atraso está dentro do esperado (inclusive
  exatamente 1 ciclo perdido, que a fila offline do edge resolveria
  sozinha);
- gera severidade "media" num atraso moderado (entre 4h e 8h);
- gera severidade "alta" num atraso grande (mais de 8h);
- gera severidade "alta" quando o dispositivo nunca reportou nada.
"""

from datetime import datetime, timedelta, timezone

from app.core.alertas_dispositivo import avaliar_inatividade_dispositivo

AGORA = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)


def test_captura_recente_nao_gera_alerta():
    ultima = AGORA - timedelta(minutes=30)
    assert avaliar_inatividade_dispositivo(ultima, AGORA) is None


def test_um_ciclo_perdido_nao_gera_alerta():
    # Intervalo esperado é 2h; 3h de atraso ainda é só 1 ciclo perdido,
    # dentro do que a fila offline do edge resolveria sozinha.
    ultima = AGORA - timedelta(hours=3)
    assert avaliar_inatividade_dispositivo(ultima, AGORA) is None


def test_atraso_moderado_gera_alerta_media():
    ultima = AGORA - timedelta(hours=5)
    resultado = avaliar_inatividade_dispositivo(ultima, AGORA)
    assert resultado is not None
    titulo, descricao, severidade = resultado
    assert severidade == "media"
    assert "atrasado" in titulo.lower()


def test_atraso_grande_gera_alerta_alta():
    ultima = AGORA - timedelta(hours=10)
    resultado = avaliar_inatividade_dispositivo(ultima, AGORA)
    assert resultado is not None
    titulo, descricao, severidade = resultado
    assert severidade == "alta"
    assert "inativo" in titulo.lower()


def test_limiar_exato_de_8h_ainda_nao_e_alta():
    # > 8h dispara "alta"; exatamente 8h ainda deve ser "media", para
    # não depender de arredondamento de ponto flutuante bem na borda.
    ultima = AGORA - timedelta(hours=8)
    resultado = avaliar_inatividade_dispositivo(ultima, AGORA)
    assert resultado is not None
    assert resultado[2] == "media"


def test_dispositivo_nunca_reportou_gera_alerta_alta():
    resultado = avaliar_inatividade_dispositivo(None, AGORA)
    assert resultado is not None
    titulo, descricao, severidade = resultado
    assert severidade == "alta"
    assert "nunca" in titulo.lower()
