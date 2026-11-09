"""
Envio dos registros pendentes da fila local para POST /diagnostico.

Cada registro é enviado como multipart/form-data (imagem, device_id,
timestamp, leituras e idempotency_key), com o cabeçalho Authorization
contendo a credencial do dispositivo. Falhas de rede e respostas 5xx são
repetidas com espera exponencial. Só os registros confirmados pela API
saem da fila. Executado pelo cron a cada 15 minutos e ao fim de cada
ciclo de captura.
"""

import logging
import sys
from pathlib import Path

if __name__ == "__main__":
    # O cron executa este arquivo diretamente; a raiz do repositório
    # precisa estar em sys.path para os imports edge.src.*.
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from edge.src import config
from edge.src.fila import offline_queue

# Registro em stdout, redirecionado para upload.log pelo cron. basicConfig
# não tem efeito se main.py já tiver configurado o logging.
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
        # A imagem já não existe: o registro é tratado como concluído para
        # não travar a fila, com aviso no log.
        logger.warning(
            "Registro %s sem imagem em %s, tratando como já enviado.",
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
        # O id gerado na fila permite à API descartar reenvios do mesmo
        # registro.
        "idempotency_key": registro["id"],
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
            "API recusou o registro %s: HTTP %d, %s",
            registro.get("id"), resposta.status_code, resposta.text[:200],
        )
    return resposta.ok


def drenar_fila_e_enviar() -> None:
    """Lê os pendentes, envia com novas tentativas e remove da fila os confirmados."""
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
