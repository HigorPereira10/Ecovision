"""
Cria ou atualiza a conta de administrador, que vê todos os dispositivos
sem precisar de pareamento.

A conta é criada já verificada, pois o cadastro público sempre atribui o
papel "produtor" e exige confirmação de e-mail. A senha vem da variável de
ambiente SENHA_ADMIN e deve cumprir as regras de senha do cadastro.

Uso (em cloud/, com o ambiente configurado):

    SENHA_ADMIN='...' python -m scripts.seed_admin

No PowerShell:

    $env:SENHA_ADMIN = '...'
    python -m scripts.seed_admin

Idempotente: se a conta existir, atualiza senha, nome e papel.
"""

import asyncio
import logging
import os
import sys

from sqlalchemy import select

from app.core.security import gerar_hash_senha
from app.db.models import Usuario
from app.db.session import _SessionLocal

logger = logging.getLogger("ecovision.cloud.seed")

NOME_ADMIN = "Administrador EcoVision"
EMAIL_ADMIN = "admin@ecovision.app"
PAPEL_ADMIN = "administrador"

VARIAVEL_SENHA = "SENHA_ADMIN"

# Mesmo mínimo exigido pelo cadastro do aplicativo.
TAMANHO_MINIMO_SENHA = 8


def _senha_do_ambiente() -> str:
    """Lê a senha do ambiente e encerra com erro se ela não estiver definida."""
    senha = os.environ.get(VARIAVEL_SENHA, "")
    if not senha:
        sys.exit(
            f"Defina {VARIAVEL_SENHA} no ambiente antes de rodar.\n"
            f"  bash:       {VARIAVEL_SENHA}='...' python -m scripts.seed_admin\n"
            f"  PowerShell: $env:{VARIAVEL_SENHA} = '...'  (e depois rode o script)"
        )
    if len(senha) < TAMANHO_MINIMO_SENHA:
        sys.exit(
            f"{VARIAVEL_SENHA} tem {len(senha)} caracteres. O cadastro do "
            f"app exige ao menos {TAMANHO_MINIMO_SENHA}, com maiúscula, "
            "minúscula, número e símbolo."
        )
    return senha


async def semear_admin() -> None:
    senha_admin = _senha_do_ambiente()

    async with _SessionLocal() as sessao:
        resultado = await sessao.execute(
            select(Usuario).where(Usuario.email == EMAIL_ADMIN)
        )
        usuario = resultado.scalar_one_or_none()

        hash_senha = gerar_hash_senha(senha_admin)

        if usuario is None:
            sessao.add(
                Usuario(
                    nome=NOME_ADMIN,
                    email=EMAIL_ADMIN,
                    senha_hash=hash_senha,
                    papel=PAPEL_ADMIN,
                    # Sem caixa postal real, a confirmação nunca chegaria.
                    email_verificado=True,
                )
            )
            await sessao.commit()
            logger.info("Conta de administrador criada: %s", EMAIL_ADMIN)
            print(f"Conta criada: {EMAIL_ADMIN}  (papel: {PAPEL_ADMIN}).")
        else:
            usuario.senha_hash = hash_senha
            usuario.nome = NOME_ADMIN
            usuario.papel = PAPEL_ADMIN
            usuario.email_verificado = True
            await sessao.commit()
            logger.info("Conta de administrador já existia, atualizada: %s", EMAIL_ADMIN)
            print(f"Conta atualizada: {EMAIL_ADMIN}  (papel: {PAPEL_ADMIN}).")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    asyncio.run(semear_admin())
