"""
cloud/app/storage/supabase_storage.py

Integração com o Supabase Storage (bucket de objetos, S3-compatible),
(v3.0, Seção 4.2) para persistir as imagens capturadas pelo Pi.

Convenção de nomenclatura definida no Blueprint: bucket "ecovision-imagens",
caminho por dispositivo e timestamp: {device_id}/{timestamp}.jpg.

Decisão de design: salvar_imagem() retorna o CAMINHO dentro do bucket,
não uma URL resolvida. A escolha entre signed URL e bucket público JÁ
FOI DECIDIDA (infra/supabase/storage_policies.md: bucket privado +
signed URLs, o comentário anterior aqui dizia "ainda em aberto" por
engano, a implementação que faltava é gerar_url_assinada_imagem()
abaixo), mas o CAMINHO continua sendo o que fica gravado em
registros_imagem: a URL assinada é gerada sob demanda (expira, não faz
sentido persistir), não no momento do upload.

Relação com o resto do sistema:
- salvar_imagem() é chamado por app/api/routes/diagnostico.py logo
  após a inferência, ANTES de a imagem ser descartada da memória
  (regra 4, Blueprint Seção 4.4).
- gerar_urls_assinadas_imagens() é chamado por
  app/api/routes/historico.py (GET /diagnosticos) para resolver
  registros_imagem.caminho_arquivo numa URL temporária exibível. É a
  versão em lote; gerar_url_assinada_imagem() continua sendo a
  primitiva de uma imagem só, e não deve ser usada em laço (ver o
  docstring da versão em lote).
"""

import asyncio
import logging

from supabase import Client, create_client

from app.config import settings

logger = logging.getLogger("ecovision.cloud.storage")

_cliente: Client | None = None

# 1h: tempo suficiente para carregar a tela de histórico/diagnóstico e
# o produtor olhar as imagens, sem manter o link válido por mais tempo
# do que o necessário (ver infra/supabase/storage_policies.md).
_EXPIRACAO_URL_ASSINADA_SEGUNDOS = 3600


def _obter_cliente() -> Client:
    global _cliente
    if _cliente is None:
        _cliente = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return _cliente


async def salvar_imagem(device_id: str, timestamp: str, bytes_imagem: bytes) -> str:
    """Faz upload para o bucket configurado e retorna o caminho salvo
    (ex.: "pi-teste/2026-08-22T10-00-00.jpg"). O nome do arquivo troca
    ':' por '-' porque ':' não é seguro em paths de object storage."""
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
    """Gera uma URL temporária (signed URL) para exibir uma imagem do
    bucket privado no dashboard. Retorna None em caso de falha (ex.:
    arquivo não existe mais no bucket, Supabase indisponível) em vez de
    propagar a exceção: uma imagem que falhou em carregar não deveria
    derrubar a lista inteira de diagnósticos (GET /diagnosticos)."""
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
    """Gera as signed URLs de vários caminhos de uma vez e devolve um
    mapa caminho -> URL (None quando o Supabase não resolveu aquele
    item).

    POR QUE ISTO EXISTE: chamar gerar_url_assinada_imagem() dentro de um
    laço custa uma requisição HTTP por imagem, em sequência. Em
    2026-11-01 isso derrubou a tela de Histórico: o banco tinha 2
    registros até a coleta noturna e passou a 124, e GET /diagnosticos
    foi de meio segundo para 12 a 14 segundos, acima do
    EXPO_PUBLIC_API_TIMEOUT de 10 s do app. As rotas /leituras e
    /alertas, que não assinam nada, continuaram em 0,5 s. O gargalo não
    era o banco.

    Trocar o laço por asyncio.gather NÃO resolveria: apesar de
    gerar_url_assinada_imagem ser `async def`, o corpo é o cliente
    síncrono do supabase-py e não tem ponto de suspensão, então as
    chamadas continuariam sequenciais e ainda bloqueariam o event loop.
    A API do Storage aceita uma lista de caminhos (`create_signed_urls`),
    o que resolve as N imagens numa única ida à rede.

    O to_thread existe porque essa chamada é bloqueante: sem ele, uma
    requisição de histórico travaria o event loop inteiro, incluindo o
    POST /diagnostico que o Pi faz a cada ciclo.
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
        # Mesma política do caso unitário: imagem que não carrega não
        # deve derrubar a lista inteira de diagnósticos.
        logger.warning(
            "Falha ao gerar signed URLs em lote para %d caminhos.", len(unicos),
            exc_info=True,
        )
        return {caminho: None for caminho in unicos}

    # A resposta vem na ordem dos caminhos enviados, mas cada item traz
    # o próprio `path`, então o mapa é montado por ele e não por índice:
    # um item com erro não desloca os demais.
    mapa: dict[str, str | None] = {caminho: None for caminho in unicos}
    for indice, resposta in enumerate(respostas or []):
        caminho = resposta.get("path") or (unicos[indice] if indice < len(unicos) else None)
        if caminho in mapa:
            mapa[caminho] = resposta.get("signedUrl") or resposta.get("signedURL")
    return mapa
