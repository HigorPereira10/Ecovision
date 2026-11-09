"""
Testes de edge/src/fila/offline_queue.py: enfileiramento, leitura dos
pendentes e remoção apenas dos registros confirmados, com suas imagens.

Requer Linux, pois a fila usa fcntl.
"""

from pathlib import Path

import pytest

# importorskip interrompe a coleta do arquivo inteiro sem fcntl, já que
# offline_queue.py o importa no topo.
pytest.importorskip(
    "fcntl",
    reason=(
        "offline_queue.py usa fcntl (trava de arquivo), que só existe em "
        "Linux/Unix. Rode estes testes dentro do WSL/Ubuntu."
    ),
)

from edge.src.fila import offline_queue  # noqa: E402


def test_ciclo_completo_enfileirar_ler_remover(tmp_path: Path):
    caminho_fila = tmp_path / "fila.jsonl"
    caminho_imagens = tmp_path / "images"

    id_1 = offline_queue.enfileirar(
        b"bytes-da-foto-1",
        {"temperatura_c": 25.3, "umidade_ar_pct": 60.1},
        caminho_fila=caminho_fila,
        caminho_imagens=caminho_imagens,
    )
    id_2 = offline_queue.enfileirar(
        b"bytes-da-foto-2",
        {"temperatura_c": 26.0, "umidade_ar_pct": 58.0},
        caminho_fila=caminho_fila,
        caminho_imagens=caminho_imagens,
    )

    pendentes = offline_queue.ler_pendentes(caminho_fila=caminho_fila)
    assert len(pendentes) == 2
    registro_1 = next(r for r in pendentes if r["id"] == id_1)
    assert registro_1["temperatura_c"] == 25.3
    assert Path(registro_1["imagem_path"]).exists()

    offline_queue.remover_enviados([id_1], caminho_fila=caminho_fila)

    restantes = offline_queue.ler_pendentes(caminho_fila=caminho_fila)
    assert len(restantes) == 1
    assert restantes[0]["id"] == id_2
    assert not (caminho_imagens / f"{id_1}.jpg").exists(), (
        "imagem já confirmada devia ter sido apagada"
    )
    assert (caminho_imagens / f"{id_2}.jpg").exists(), (
        "imagem ainda pendente não devia ser apagada"
    )


def test_ler_pendentes_com_fila_inexistente_retorna_lista_vazia(tmp_path: Path):
    """Antes da primeira captura o arquivo da fila não existe; isso
    significa "nada pendente", não erro."""
    caminho_fila = tmp_path / "nao-existe" / "fila.jsonl"
    assert offline_queue.ler_pendentes(caminho_fila=caminho_fila) == []


def test_remover_enviados_com_lista_vazia_nao_faz_nada(tmp_path: Path):
    caminho_fila = tmp_path / "fila.jsonl"
    caminho_imagens = tmp_path / "images"
    offline_queue.enfileirar(
        b"bytes",
        {"temperatura_c": 20.0},
        caminho_fila=caminho_fila,
        caminho_imagens=caminho_imagens,
    )

    offline_queue.remover_enviados([], caminho_fila=caminho_fila)

    assert len(offline_queue.ler_pendentes(caminho_fila=caminho_fila)) == 1
