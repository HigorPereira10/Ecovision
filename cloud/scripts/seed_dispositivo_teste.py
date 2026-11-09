"""
Vincula um dispositivo diretamente à conta de teste, sem pareamento, para
desenvolvimento local. Para dispositivos reais, use
scripts/provisionar_dispositivo.py e o pareamento pelo aplicativo.

DEVICE_ID_REAL deve ser igual ao DEVICE_ID do .env do dispositivo; caso
contrário, as capturas ficam sem dono e não aparecem em nenhuma tela.

Uso (em cloud/, com o ambiente configurado):

    python -m scripts.seed_dispositivo_teste

Idempotente: se o device_id existir, apenas atualiza o nome.
"""

import asyncio
import logging

from sqlalchemy import select

from app.db.models import Dispositivo, Usuario
from app.db.session import _SessionLocal

logger = logging.getLogger("ecovision.cloud.seed")

# Deve ser igual ao DEVICE_ID do .env do dispositivo.
DEVICE_ID_REAL = "pi-estufa-01"
NOME_TESTE = "Estufa 1"
EMAIL_DONO = "produtor@ecovision.app"  # mesma conta de seed_usuario_teste.py


async def semear_dispositivo_teste() -> None:
    async with _SessionLocal() as sessao:
        resultado_dono = await sessao.execute(select(Usuario).where(Usuario.email == EMAIL_DONO))
        dono = resultado_dono.scalar_one_or_none()
        if dono is None:
            logger.error(
                "Usuário dono (%s) não existe ainda. Rode scripts.seed_usuario_teste primeiro.",
                EMAIL_DONO,
            )
            return

        resultado = await sessao.execute(
            select(Dispositivo).where(Dispositivo.device_id == DEVICE_ID_REAL)
        )
        dispositivo = resultado.scalar_one_or_none()

        if dispositivo is None:
            sessao.add(Dispositivo(device_id=DEVICE_ID_REAL, usuario_id=dono.id, nome=NOME_TESTE))
            await sessao.commit()
            logger.info("Dispositivo criado: %s", DEVICE_ID_REAL)
        else:
            dispositivo.nome = NOME_TESTE
            dispositivo.usuario_id = dono.id
            await sessao.commit()
            logger.info("Dispositivo já existia, nome/dono atualizados: %s", DEVICE_ID_REAL)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(semear_dispositivo_teste())
