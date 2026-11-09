"""
Integração com o Supabase Storage.

As imagens ficam no bucket privado configurado, em
{device_id}/{timestamp}.jpg. salvar_imagem() devolve o caminho, que é o
que se grava em registros_imagem; as URLs assinadas são geradas sob
demanda, em lote, por gerar_urls_assinadas_imagens().
"""

import asyncio
import logging

from supabase import Client, create_client

from app.config import settings

logger = logging.getLogger("ecovision.cloud.storage")

_cliente: Client | None = None

# Validade das URLs assinadas.
_EXPIRACAO_URL_ASSINADA_SEGUNDOS = 3600


def _obter_cliente() -> Client:
    global _cliente
    if _cliente is None:
        _cliente = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return _cliente


async def salvar_imagem(device_id: str, timestamp: str, bytes_imagem: bytes) -> str:
    """Envia a imagem ao bucket e devolve o caminho gravado. O nome do
    arquivo troca ':' por '-', que não é seguro em caminhos de objeto."""
    nome_arquivo = f"{timestamp.replace(':', '-')}.jpg"
    caminho = f"{device_id}/{nome_arquivo}"

    cliente = _obter_cliente()
    cliente.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
        caminho,
        bytes_imagem,
        {"content-type": "image/jpeg"},
    )
    return caminho


async def gerar_url_assinada_imagem(caminho: str) -> str | None:
    """Gera a URL assinada de uma imagem, ou None em caso de falha, para
    não derrubar a lista de diagnósticos."""
    cliente = _obter_cliente()
    try:
        resposta = cliente.storage.from_(settings.SUPABASE_STORAGE_BUCKET).create_signed_url(
            caminho, _EXPIRACAO_URL_ASSINADA_SEGUNDOS
        )
    except Exception:
        logger.warning("Falha ao gerar signed URL para '%s'.", caminho, exc_info=True)
        return None

    return resposta.get("signedUrl")


async def gerar_urls_assinadas_imagens(caminhos: list[str]) -> dict[str, str | None]:
    """Gera as URLs assinadas de vários caminhos em uma única chamada e
    devolve um mapa caminho -> URL (None quando não resolvido).

    Uma chamada por imagem tornava a listagem lenta demais. O cliente do
    supabase-py é síncrono, por isso a chamada roda em asyncio.to_thread,
    sem bloquear o event loop.
    """
    if not caminhos:
        return {}

    unicos = list(dict.fromkeys(caminhos))
    cliente = _obter_cliente()

    def _assinar() -> list[dict]:
        return cliente.storage.from_(settings.SUPABASE_STORAGE_BUCKET).create_signed_urls(
            unicos, _EXPIRACAO_URL_ASSINADA_SEGUNDOS
        )

    try:
        respostas = await asyncio.to_thread(_assinar)
    except Exception:
        # Uma imagem que não carrega não derruba a lista.
        logger.warning(
            "Falha ao gerar signed URLs em lote para %d caminhos.", len(unicos),
            exc_info=True,
        )
        return {caminho: None for caminho in unicos}

    # O mapa é montado pelo `path` de cada item, e não pelo índice, para
    # que um item com erro não desloque os demais.
    mapa: dict[str, str | None] = {caminho: None for caminho in unicos}
    for indice, resposta in enumerate(respostas or []):
        caminho = resposta.get("path") or (unicos[indice] if indice < len(unicos) else None)
        if caminho in mapa:
            mapa[caminho] = resposta.get("signedUrl") or resposta.get("signedURL")
    return mapa
