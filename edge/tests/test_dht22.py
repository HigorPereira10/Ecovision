"""
Testes de edge/src/sensors/dht22.py: novas tentativas em falhas pontuais,
erro claro ao esgotá-las, arredondamento, recusa de leitura implausível e
liberação do sensor ao final.
"""

from unittest.mock import MagicMock

import pytest

from edge.src.sensors import dht22


class _DispositivoSimulado:
    """Simula adafruit_dht.DHT22: cada acesso a .temperature consome uma
    tentativa da lista (tupla (temperatura, umidade) ou "erro"); .humidity
    devolve o valor da mesma tentativa."""

    def __init__(self, tentativas):
        self._tentativas = list(tentativas)
        self._atual = None
        self.exit = MagicMock()

    @property
    def temperature(self):
        self._atual = self._tentativas.pop(0)
        if self._atual == "erro":
            raise RuntimeError("falha simulada de checksum/timing")
        return self._atual[0]

    @property
    def humidity(self):
        return self._atual[1]


def test_pino_nao_mapeado_da_erro_claro_com_o_numero_do_pino():
    with pytest.raises(RuntimeError, match="Pino BCM 99"):
        dht22._pino_board(99)


def test_leitura_com_sucesso_de_primeira_arredonda_os_valores(fake_dht22_classe):
    fake_dht22_classe.return_value = _DispositivoSimulado([(24.567, 55.321)])

    resultado = dht22.ler_dht22(4)

    assert resultado == {"temperatura_c": 24.6, "umidade_ar_pct": 55.3}


def test_dispositivo_e_liberado_mesmo_com_sucesso(fake_dht22_classe):
    dispositivo = _DispositivoSimulado([(20.0, 50.0)])
    fake_dht22_classe.return_value = dispositivo

    dht22.ler_dht22(4)

    dispositivo.exit.assert_called_once()


def test_tenta_de_novo_apos_falhas_pontuais_e_acaba_lendo_com_sucesso(fake_dht22_classe, monkeypatch):
    monkeypatch.setattr(dht22.time, "sleep", lambda segundos: None)
    fake_dht22_classe.return_value = _DispositivoSimulado(["erro", "erro", (22.2, 60.0)])

    resultado = dht22.ler_dht22(4)

    assert resultado == {"temperatura_c": 22.2, "umidade_ar_pct": 60.0}


def test_desiste_apos_esgotar_todas_as_tentativas(fake_dht22_classe, monkeypatch):
    monkeypatch.setattr(dht22.time, "sleep", lambda segundos: None)
    dispositivo = _DispositivoSimulado(["erro"] * dht22._RETRIES)
    fake_dht22_classe.return_value = dispositivo

    with pytest.raises(RuntimeError, match="DHT22 no pino 4"):
        dht22.ler_dht22(4)

    dispositivo.exit.assert_called_once()
