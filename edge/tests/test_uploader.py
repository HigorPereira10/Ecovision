"""
edge/tests/test_uploader.py

O que este arquivo verifica, em português simples:

O módulo de upload pega o que está pendente na fila offline e manda
para a API pela internet. Como não existe uma API de verdade rodando
durante os testes (o backend em cloud/ ainda nem está pronto), aqui a
gente troca a "sessão HTTP" real por uma falsa, que devolve exatamente
a resposta que queremos simular — sem precisar de internet, servidor,
nem do backend pronto.

Casos cobertos:
1. Envio com sucesso (a API responde 2xx): o registro deve sumir da
   fila e o arquivo de imagem correspondente deve ser apagado.
2. Falha de rede (a internet da estufa caiu no meio do envio): o
   registro deve continuar na fila e a imagem NÃO pode ser apagada —
   senão a foto se perderia de vez, sem nunca ter sido entregue.
3. A API responde com erro (ex.: 500, fora do ar): mesmo comportamento
   do caso 2 — nada é apagado até vir uma confirmação de sucesso.
4. Caso raro, mas real, incluído porque apareceu em revisão de código:
   a imagem já não existe mais em disco (ex.: uma tentativa anterior já
   tinha apagado o arquivo, mas a confirmação de sucesso não chegou a
   tempo de limpar o registro da fila). O sistema trata isso como "já
   enviado" — em vez de travar a fila para sempre por causa de um
   arquivo que não existe mais.
5. Fila vazia: não deve tentar nenhuma chamada de rede.

Mesma observação de test_offline_queue.py: só roda em Linux/WSL, porque
o módulo de fila usado por baixo depende de fcntl.
"""

from pathlib import Path

import pytest

# pytest.importorskip interrompe a COLETA do arquivo (não só os testes)
# se fcntl não existir — necessário porque uploader.py importa
# offline_queue.py, que importa fcntl direto no topo do arquivo, então
# um simples skipif não evitaria o ModuleNotFoundError no Windows.
pytest.importorskip(
    "fcntl",
    reason=(
        "uploader.py usa edge/src/queue/offline_queue.py, que depende de "
        "fcntl (só existe em Linux/Unix). Rode estes testes no WSL/Ubuntu."
    ),
)

import requests  # noqa: E402

from edge.src.queue import offline_queue  # noqa: E402
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
        self.chamadas.append({"url": url, "headers": headers})
        return _RespostaFalsa(status_code=200, ok=True)


class _SessaoFalsaComFalhaDeRede:
    """Simula a internet da estufa caindo durante o envio."""

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
    """drenar_fila_e_enviar() não recebe parâmetros — ele sempre usa a
    fila configurada em edge/src/config.py. Para não mexer na fila real
    do dispositivo durante o teste, trocamos temporariamente as funções
    que ele chama por versões que apontam para a fila de teste."""
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
