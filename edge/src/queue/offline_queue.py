"""
edge/src/queue/offline_queue.py

Fila offline em disco (formato JSON Lines) para tolerar quedas de rede
no ambiente de estufa (Blueprint v3.0, Fase 2).

Decisão de implementação: cada linha da fila guarda só METADADOS (id,
device_id, timestamp, leituras dos sensores e o caminho do arquivo de
imagem). A imagem comprimida é salva como arquivo separado em
edge/data/queue/images/{id}.jpg, não em base64 dentro do JSON, para não
inflar em ~33% o tamanho num SD card já limitado (Blueprint, BoM:
microSD 32GB compartilhado com o OS).

`fcntl.flock` protege o arquivo da fila contra corrupção se a captura
(escreve) e a drenagem (lê/remove) rodarem ao mesmo tempo via cron.

Relação com o resto do sistema:
- Escrito por edge/src/main.py a cada ciclo de captura.
- Drenado por edge/src/upload/uploader.py, agendado a cada 15min via cron.
"""

import fcntl
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from edge.src import config


def _garantir_diretorios(caminho_fila: Path, caminho_imagens: Path) -> None:
    caminho_fila.parent.mkdir(parents=True, exist_ok=True)
    caminho_imagens.mkdir(parents=True, exist_ok=True)


def enfileirar(
    imagem_bytes: bytes,
    leituras: dict,
    caminho_fila: Path = config.QUEUE_FILE,
    caminho_imagens: Path = config.QUEUE_IMAGES_DIR,
) -> str:
    """Salva a imagem comprimida em disco e adiciona um registro de
    metadados como nova linha JSON na fila. Retorna o id gerado."""
    _garantir_diretorios(caminho_fila, caminho_imagens)

    registro_id = uuid.uuid4().hex
    caminho_imagem = caminho_imagens / f"{registro_id}.jpg"
    caminho_imagem.write_bytes(imagem_bytes)

    registro = {
        "id": registro_id,
        "device_id": config.DEVICE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "imagem_path": str(caminho_imagem),
        **leituras,
    }

    with open(caminho_fila, "a", encoding="utf-8") as arquivo:
        fcntl.flock(arquivo, fcntl.LOCK_EX)
        try:
            arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
        finally:
            fcntl.flock(arquivo, fcntl.LOCK_UN)

    return registro_id


def ler_pendentes(caminho_fila: Path = config.QUEUE_FILE) -> list:
    """Lê os registros ainda não enviados."""
    if not caminho_fila.exists():
        return []

    with open(caminho_fila, "r", encoding="utf-8") as arquivo:
        fcntl.flock(arquivo, fcntl.LOCK_SH)
        try:
            linhas = arquivo.readlines()
        finally:
            fcntl.flock(arquivo, fcntl.LOCK_UN)

    return [json.loads(linha) for linha in linhas if linha.strip()]


def remover_enviados(ids_enviados: list, caminho_fila: Path = config.QUEUE_FILE) -> None:
    """Remove da fila os registros já confirmados como enviados (HTTP 2xx)
    e apaga o arquivo de imagem correspondente de cada um."""
    if not ids_enviados or not caminho_fila.exists():
        return

    ids_enviados = set(ids_enviados)

    with open(caminho_fila, "r+", encoding="utf-8") as arquivo:
        fcntl.flock(arquivo, fcntl.LOCK_EX)
        try:
            registros = [json.loads(linha) for linha in arquivo if linha.strip()]

            restantes = []
            for registro in registros:
                if registro["id"] in ids_enviados:
                    Path(registro["imagem_path"]).unlink(missing_ok=True)
                else:
                    restantes.append(registro)

            arquivo.seek(0)
            arquivo.truncate()
            for registro in restantes:
                arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
        finally:
            fcntl.flock(arquivo, fcntl.LOCK_UN)
