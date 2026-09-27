"""
edge/tests/test_offline_queue.py

O que este arquivo verifica, em português simples:

A "fila offline" é o mecanismo que guarda fotos e leituras de sensores
em disco quando a internet da estufa cai, para não perder nada, e
depois manda tudo assim que a conexão volta. Estes testes simulam esse
ciclo inteiro, sem precisar de rede nem de Raspberry Pi:

1. "Enfileirar" duas capturas, como se fossem duas fotos tiradas com a
   internet fora do ar.
2. Ler o que está pendente de envio e confirmar que as duas aparecem,
   com os dados de sensor corretos.
3. "Confirmar o envio" de uma delas e checar que:
   - ela some da lista de pendentes;
   - o arquivo de imagem dela é apagado do disco (não faz sentido
     guardar a foto depois que ela já foi entregue à API);
   - a outra, que ainda não foi confirmada, continua intacta, tanto o
     registro quanto o arquivo de imagem dela.

Só roda em Linux/WSL porque o módulo testado usa fcntl (trava de
arquivo) para proteger a fila de corrupção quando a captura (escreve) e
o envio (lê/remove) rodam ao mesmo tempo via cron. Esse recurso não
existe no Python do Windows.
"""

from pathlib import Path

import pytest

# pytest.importorskip interrompe a COLETA do arquivo (não só os testes)
# se fcntl não existir. Isso é necessário porque offline_queue.py importa
# fcntl direto no topo do arquivo, então um simples skipif não evitaria
# o ModuleNotFoundError ao tentar importar o módulo no Windows.
pytest.importorskip(
    "fcntl",
    reason=(
        "offline_queue.py usa fcntl (trava de arquivo), que só existe em "
        "Linux/Unix. Rode estes testes dentro do WSL/Ubuntu."
    ),
)

from edge.src.fila import offline_queue  # noqa: E402 (import após o importorskip acima)


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
    """Antes da primeira captura, o arquivo da fila ainda nem existe.
    Isso não pode ser tratado como erro, e sim como 'nada pendente'."""
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
