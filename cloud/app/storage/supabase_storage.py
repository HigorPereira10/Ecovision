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
- gerar_url_assinada_imagem() é chamado por
  app/api/routes/historico.py (GET /diagnosticos) para resolver
  registros_imagem.caminho_arquivo numa URL temporária exibível.
"""

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
