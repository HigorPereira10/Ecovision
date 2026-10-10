"""
cloud/app/api/dispositivo_auth.py

Autentica o Raspberry Pi que envia capturas para POST /diagnostico.

POR QUE ISTO EXISTE: o ADR 0003 escolheu uma API Key estática e GLOBAL,
com a justificativa explícita de que o sistema tinha "1 único
dispositivo". Quando o cadastro de produtores foi aberto, essa premissa
caiu: com chave global, qualquer um que a possua pode enviar captura se
passando por QUALQUER `device_id`, ou seja, injetar um diagnóstico falso
na estufa de outro produtor. E como a mesma chave fica no `.env` de todo
Pi, um aparelho comprometido comprometeria a frota inteira.

Agora cada dispositivo tem o próprio segredo, cujo hash bcrypt fica em
`dispositivos.chave_hash`. O segredo em claro existe só no `.env` daquele
Pi, nunca no banco: se o banco vazar, as credenciais não servem.

TRANSIÇÃO: a chave global continua aceita por enquanto, e cada uso dela
gera um aviso no log com o device_id. Isso existe para não derrubar um
dispositivo em campo no instante do deploy. Depois que todos os Pis
estiverem provisionados (ver cloud/scripts/provisionar_dispositivo.py),
basta apagar o ramo marcado abaixo e a chave global deixa de valer.

Este módulo mora em app/api/ e não em app/core/ porque precisa consultar
o banco, e app/core/ não importa app/db/ (ver o diagrama em
docs/architecture/).
"""

import logging
import secrets

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import verificar_senha
from app.db.models import Dispositivo

logger = logging.getLogger("ecovision.cloud.dispositivo_auth")


async def autenticar_dispositivo(
    sessao: AsyncSession, device_id: str, credencial: str
) -> Dispositivo | None:
    """Confere se `credencial` autoriza enviar dados como `device_id`.

    Devolve o Dispositivo quando a autenticação foi pela chave própria,
    ou None quando passou pela chave global de transição (caso em que o
    aparelho pode nem ter cadastro). Levanta 401 se a credencial não
    serve.

    A mensagem de erro é a mesma para device_id inexistente e para
    segredo errado, de propósito: diferenciar permitiria descobrir quais
    device_ids existem testando valores.
    """
    # --- RAMO DE TRANSIÇÃO: remover quando todos os Pis forem provisionados ---
    # compare_digest em vez de == para a comparação não vazar, pelo tempo
    # de resposta, quantos caracteres iniciais da chave estavam certos.
    #
    # Comparação em BYTES, não em texto: compare_digest recusa strings
    # com caracteres não-ASCII e levanta TypeError, que escaparia daqui
    # como erro 500. Como a credencial vem de fora, qualquer um poderia
    # derrubar a rota mandando um byte acentuado no header.
    if secrets.compare_digest(
        credencial.encode("utf-8"), settings.DEVICE_API_KEY.encode("utf-8")
    ):
        logger.warning(
            "device_id=%s autenticou com a CHAVE GLOBAL (ADR 0003). Provisionar "
            "uma chave propria com scripts/provisionar_dispositivo.py.",
            device_id,
        )
        return None
    # --- FIM DO RAMO DE TRANSIÇÃO ---

    dispositivo = await sessao.scalar(
        select(Dispositivo).where(Dispositivo.device_id == device_id)
    )

    if dispositivo is None or dispositivo.chave_hash is None:
        logger.warning("Tentativa de envio com device_id desconhecido: %s", device_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credencial de dispositivo inválida.",
        )

    if not verificar_senha(credencial, dispositivo.chave_hash):
        logger.warning("Segredo incorreto para device_id=%s", device_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credencial de dispositivo inválida.",
        )

    return dispositivo
