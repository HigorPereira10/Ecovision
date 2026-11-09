"""
Testes de edge/src/upload/uploader.py, com uma sessão HTTP simulada:

1. sucesso (2xx): o registro sai da fila e a imagem é apagada;
2. falha de rede: o registro e a imagem permanecem;
3. erro da API (5xx): o registro e a imagem permanecem;
4. imagem já inexistente: o registro é tratado como concluído;
5. fila vazia: nenhuma requisição é feita.

Requer Linux, pois a fila usa fcntl.
"""

from pathlib import Path

import pytest

# importorskip interrompe a coleta do arquivo inteiro sem fcntl, já que
# a fila o importa no topo.
pytest.importorskip(
    "fcntl",
    reason=(
        "uploader.py usa edge/src/fila/offline_queue.py, que depende de "
        "fcntl (só existe em Linux/Unix). Rode estes testes no WSL/Ubuntu."
    ),
)

import requests  # noqa: E402

from edge.src.fila import offline_queue  # noqa: E402
from edge.src.upload import uploader  # noqa: E402

_ler_pendentes_real = offline_queue.ler_pendentes
_remover_enviados_real = offline_queue.remover_enviados


class _RespostaFalsa:
    def __init__(self, status_code: int, ok: bool, texto: str = ""):
        self.status_code = status_code
        self.ok = ok
        self.text = texto


class _SessaoFalsaComSucesso:
    """Simula uma API que sempre aceita o envio (HTTP 200)."""

    def __init__(self):
        self.chamadas = []

    def post(self, url, data, files, headers, timeout):
        self.chamadas.append({"url": url, "data": data, "headers": headers})
        return _RespostaFalsa(status_code=200, ok=True)


class _SessaoFalsaComFalhaDeRede:
    """Simula queda de rede durante o envio."""

    def post(self, *args, **kwargs):
        raise requests.RequestException("simulação de rede fora do ar")


class _SessaoFalsaComErroDaApi:
    """Simula a API respondendo com erro de servidor."""

    def post(self, *args, **kwargs):
        return _RespostaFalsa(status_code=500, ok=False, texto="erro interno simulado")


def _preparar_fila_com_um_registro(tmp_path: Path):
    caminho_fila = tmp_path / "fila.jsonl"
    caminho_imagens = tmp_path / "images"
    id_registro = offline_queue.enfileirar(
        b"bytes-de-foto-falsa",
        {"temperatura_c": 24.0, "umidade_ar_pct": 55.0},
        caminho_fila=caminho_fila,
        caminho_imagens=caminho_imagens,
    )
    return id_registro, caminho_fila, caminho_imagens


def _conectar_fila_de_teste(monkeypatch, caminho_fila: Path, sessao_falsa):
    """drenar_fila_e_enviar() usa a fila de config.py; aqui as funções
    chamadas por ele são redirecionadas para a fila de teste."""
    monkeypatch.setattr(
        offline_queue, "ler_pendentes", lambda: _ler_pendentes_real(caminho_fila=caminho_fila)
    )
    monkeypatch.setattr(
        offline_queue,
        "remover_enviados",
        lambda ids: _remover_enviados_real(ids, caminho_fila=caminho_fila),
    )
    monkeypatch.setattr(uploader, "_sessao_com_retry", lambda: sessao_falsa)


def test_envio_com_sucesso_remove_da_fila_e_apaga_imagem(monkeypatch, tmp_path):
    id_registro, caminho_fila, caminho_imagens = _preparar_fila_com_um_registro(tmp_path)
    sessao_falsa = _SessaoFalsaComSucesso()
    _conectar_fila_de_teste(monkeypatch, caminho_fila, sessao_falsa)

    uploader.drenar_fila_e_enviar()

    assert _ler_pendentes_real(caminho_fila=caminho_fila) == []
    assert not (caminho_imagens / f"{id_registro}.jpg").exists()
    assert len(sessao_falsa.chamadas) == 1
    assert sessao_falsa.chamadas[0]["headers"]["Authorization"] is not None
    # A API usa este campo para descartar reenvios duplicados.
    assert sessao_falsa.chamadas[0]["data"]["idempotency_key"] == id_registro


def test_falha_de_rede_mantem_registro_na_fila_e_preserva_imagem(monkeypatch, tmp_path):
    id_registro, caminho_fila, caminho_imagens = _preparar_fila_com_um_registro(tmp_path)
    _conectar_fila_de_teste(monkeypatch, caminho_fila, _SessaoFalsaComFalhaDeRede())

    uploader.drenar_fila_e_enviar()

    pendentes = _ler_pendentes_real(caminho_fila=caminho_fila)
    assert len(pendentes) == 1
    assert pendentes[0]["id"] == id_registro
    assert (caminho_imagens / f"{id_registro}.jpg").exists()


def test_api_recusando_o_envio_mantem_registro_na_fila(monkeypatch, tmp_path):
    id_registro, caminho_fila, caminho_imagens = _preparar_fila_com_um_registro(tmp_path)
    _conectar_fila_de_teste(monkeypatch, caminho_fila, _SessaoFalsaComErroDaApi())

    uploader.drenar_fila_e_enviar()

    pendentes = _ler_pendentes_real(caminho_fila=caminho_fila)
    assert len(pendentes) == 1
    assert (caminho_imagens / f"{id_registro}.jpg").exists()


def test_imagem_ja_removida_e_tratada_como_ja_enviada(monkeypatch, tmp_path):
    id_registro, caminho_fila, caminho_imagens = _preparar_fila_com_um_registro(tmp_path)
    (caminho_imagens / f"{id_registro}.jpg").unlink()

    _conectar_fila_de_teste(monkeypatch, caminho_fila, _SessaoFalsaComSucesso())

    uploader.drenar_fila_e_enviar()

    assert _ler_pendentes_real(caminho_fila=caminho_fila) == []


def test_fila_vazia_nao_faz_chamada_nenhuma(monkeypatch, tmp_path):
    caminho_fila = tmp_path / "fila.jsonl"
    sessao_falsa = _SessaoFalsaComSucesso()
    _conectar_fila_de_teste(monkeypatch, caminho_fila, sessao_falsa)

    uploader.drenar_fila_e_enviar()

    assert sessao_falsa.chamadas == []
