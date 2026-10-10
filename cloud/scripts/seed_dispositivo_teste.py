"""
cloud/scripts/seed_dispositivo_teste.py

Cadastra o Raspberry Pi real na tabela `dispositivos`, vinculado à
conta de produtor semeada por seed_usuario_teste.py. Sem essa linha,
GET /dispositivos sempre devolve uma lista vazia (a tabela existe, mas
ninguém grava nela: o /diagnostico não exige um cadastro prévio em
`dispositivos`, ver app/core/security.py).

ANTES DE RODAR: troque DEVICE_ID_REAL abaixo pelo mesmo valor
configurado em DEVICE_ID no .env do Raspberry Pi (edge/src/config.py).
Se os dois valores não baterem, o dispositivo aparece cadastrado mas
sempre como "inativo" (o status é calculado batendo esse device_id
contra o device_id que chega em cada /diagnostico).

Como rodar (dentro de cloud/, com o venv ativado e as variáveis de
ambiente reais carregadas):

    python -m scripts.seed_dispositivo_teste

Idempotente: rodar de novo só atualiza o nome se o device_id já
existir, não cria duplicata (device_id é UNIQUE em app/db/models.py).
"""

import asyncio
import logging

from sqlalchemy import select

from app.db.models import Dispositivo, Usuario
from app.db.session import _SessionLocal

logger = logging.getLogger("ecovision.cloud.seed")

# Decidido com o grupo em 2026-10-10. Tem que bater EXATAMENTE com o
# DEVICE_ID do edge/.env no cartao do Raspberry (edge/src/config.py
# exige a variavel e nao tem valor padrao). Se os dois divergirem, as
# capturas chegam ao banco mas ficam sem dono e, com o filtro de
# app/api/escopo.py, invisiveis em todas as telas.
DEVICE_ID_REAL = "pi-estufa-01"
NOME_TESTE = "Estufa 1"
EMAIL_DONO = "joao.pereira@exemplo.com"  # mesma conta de seed_usuario_teste.py


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
