"""
edge/src/upload/uploader.py

Upload HTTP dos registros pendentes para a API, com retry/backoff
(Blueprint v3.0, Fase 2).

Contrato assumido do endpoint (cloud/ ainda não implementado — conferir
os dois lados quando cloud/app/api/routes/diagnostico.py existir):
  POST {API_BASE_URL}/diagnostico
  Header: Authorization: <DEVICE_API_KEY>
  multipart/form-data:
    - imagem: arquivo JPEG comprimido
    - device_id, timestamp: strings
    - temperatura_c, umidade_ar_pct, umidade_solo_pct: números (as demais
      chaves de "leituras" gravadas por edge/src/queue/offline_queue.py)

Responsabilidades:
- Ler os pendentes da fila (edge/src/queue/offline_queue.py).
- Enviar cada um para a API, autenticado via header Authorization com a
  API Key estática (config.DEVICE_API_KEY).
- Retry com backoff exponencial (requests.Session + urllib3 Retry) para
  falhas de rede/5xx.
- Remover da fila apenas os itens confirmados (HTTP 2xx) pela API.

Relação com o resto do sistema:
- Consome a fila escrita por edge/src/main.py.
- Único ponto de contato do edge/ com o endpoint
  cloud/app/api/routes/diagnostico.py.
- Agendado a cada 15min via `crontab.example`; também chamado de forma
  best-effort ao final de cada ciclo de captura (edge/src/main.py).
"""

import logging
import sys
from pathlib import Path

if __name__ == "__main__":
    # Cron invoca este arquivo diretamente (`python edge/src/upload/uploader.py`),
    # então a raiz do repositório não entra em sys.path por padrão — precisa
    # ser adicionada manualmente para os imports `edge.src.*` funcionarem.
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from edge.src import config
from edge.src.queue import offline_queue

# BUG CORRIGIDO: este módulo não tinha nenhum log. Como roda sozinho via
# cron a cada 15min (crontab.example), sem isso não havia como saber, sem
# SSH na estufa, se os uploads estavam de fato acontecendo. basicConfig()
# é seguro de chamar de novo aqui mesmo quando main.py já chamou (é
# no-op se o root logger já tem handler configurado).
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ecovision.edge.upload")

_CAMPOS_NAO_LEITURAS = {"id", "device_id", "timestamp", "imagem_path"}


def _sessao_com_retry() -> requests.Session:
    sessao = requests.Session()
    retry = Retry(
        total=config.UPLOAD_MAX_RETRIES,
        backoff_factor=config.UPLOAD_BACKOFF_FACTOR,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["POST"],
    )
    adaptador = HTTPAdapter(max_retries=retry)
    sessao.mount("http://", adaptador)
    sessao.mount("https://", adaptador)
    return sessao


def _enviar_registro(sessao: requests.Session, registro: dict) -> bool:
    caminho_imagem = Path(registro["imagem_path"])
    if not caminho_imagem.exists():
        # Imagem já foi removida (ex.: envio anterior parcialmente
        # confirmado). Não há o que reenviar; trata como concluído para
        # não travar a fila indefinidamente. Logado como warning (não
        # info) porque também pode indicar um bug/corrupção real — sem
        # isso não havia nenhum rastro desse caso acontecer.
        logger.warning(
            "Registro %s sem imagem em %s — tratando como já enviado.",
            registro.get("id"), caminho_imagem,
        )
        return True

    leituras = {
        chave: valor
        for chave, valor in registro.items()
        if chave not in _CAMPOS_NAO_LEITURAS
    }

    dados = {
        "device_id": registro["device_id"],
        "timestamp": registro["timestamp"],
        **leituras,
    }
    headers = {"Authorization": config.DEVICE_API_KEY}

    with open(caminho_imagem, "rb") as arquivo_imagem:
        arquivos = {"imagem": (caminho_imagem.name, arquivo_imagem, "image/jpeg")}
        try:
            resposta = sessao.post(
                f"{config.API_BASE_URL}/diagnostico",
                data=dados,
                files=arquivos,
                headers=headers,
                timeout=config.UPLOAD_TIMEOUT_SECONDS,
            )
        except requests.RequestException:
            logger.warning("Falha de rede ao enviar registro %s.", registro.get("id"), exc_info=True)
            return False

    if not resposta.ok:
        logger.warning(
            "API recusou o registro %s: HTTP %d — %s",
            registro.get("id"), resposta.status_code, resposta.text[:200],
        )
    return resposta.ok


def drenar_fila_e_enviar() -> None:
    """Lê pendentes, envia com retry/backoff, remove da fila os confirmados."""
    pendentes = offline_queue.ler_pendentes()
    if not pendentes:
        logger.info("Fila vazia, nada para enviar.")
        return

    logger.info("Drenando fila: %d registro(s) pendente(s).", len(pendentes))
    sessao = _sessao_com_retry()
    ids_enviados = []

    for registro in pendentes:
        if _enviar_registro(sessao, registro):
            ids_enviados.append(registro["id"])

    if ids_enviados:
        offline_queue.remover_enviados(ids_enviados)

    logger.info(
        "Envio concluído: %d confirmado(s), %d ainda pendente(s).",
        len(ids_enviados), len(pendentes) - len(ids_enviados),
    )


if __name__ == "__main__":
    drenar_fila_e_enviar()
