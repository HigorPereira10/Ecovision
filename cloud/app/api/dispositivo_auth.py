"""
Autenticação dos dispositivos que enviam dados a POST /diagnostico e
POST /leituras.

Cada dispositivo tem um segredo próprio; o banco guarda apenas o hash
bcrypt em dispositivos.chave_hash. A chave global anterior ainda é aceita
por compatibilidade, com aviso no log a cada uso. O módulo fica em
app/api/ porque consulta o banco, e app/core/ não depende de app/db/.
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

    Devolve o Dispositivo autenticado pela chave própria, ou None quando a
    autenticação usou a chave global. Levanta 401 com a mesma mensagem para
    device_id inexistente e segredo errado.
    """
    # --- Compatibilidade com a chave global ---
    # Comparação em bytes, em tempo constante, aceitando qualquer valor
    # sem gerar erro 500.
    if secrets.compare_digest(
        credencial.encode("utf-8"), settings.DEVICE_API_KEY.encode("utf-8")
    ):
        logger.warning(
            "device_id=%s autenticou com a chave global. Provisione uma "
            "credencial própria com scripts/provisionar_dispositivo.py.",
            device_id,
        )
        return None
    # --- Fim da compatibilidade ---

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
