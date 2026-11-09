"""
Cria ou atualiza a conta de produtor de teste (produtor@ecovision.app).

A senha vem da variável de ambiente SENHA_PRODUTOR_TESTE.

Uso (em cloud/, com o ambiente configurado):

    SENHA_PRODUTOR_TESTE='...' python -m scripts.seed_usuario_teste

No PowerShell:

    $env:SENHA_PRODUTOR_TESTE = '...'
    python -m scripts.seed_usuario_teste

Idempotente: se a conta existir, apenas atualiza o hash da senha.
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

# Atenção: o script sobrescreve a senha da conta abaixo. Use apenas em
# banco de desenvolvimento; em produção, crie contas pelo aplicativo.

NOME_TESTE = "Produtor EcoVision"
# E-mail neutro do projeto, exibido na tela de Perfil.
EMAIL_TESTE = "produtor@ecovision.app"
PAPEL_TESTE = "produtor"

VARIAVEL_SENHA = "SENHA_PRODUTOR_TESTE"


def _senha_do_ambiente() -> str:
    """Lê a senha do ambiente e recusa executar sem ela."""
    senha = os.environ.get(VARIAVEL_SENHA, "")
    if not senha:
        sys.exit(
            f"Defina {VARIAVEL_SENHA} no ambiente antes de rodar.\n"
            f"  bash:       {VARIAVEL_SENHA}='...' python -m scripts.seed_usuario_teste\n"
            f"  PowerShell: $env:{VARIAVEL_SENHA} = '...'  (e depois rode o script)"
        )
    return senha


async def semear_usuario_teste() -> None:
    senha_teste = _senha_do_ambiente()

    async with _SessionLocal() as sessao:
        resultado = await sessao.execute(select(Usuario).where(Usuario.email == EMAIL_TESTE))
        usuario = resultado.scalar_one_or_none()

        hash_senha = gerar_hash_senha(senha_teste)

        if usuario is None:
            sessao.add(
                Usuario(nome=NOME_TESTE, email=EMAIL_TESTE, senha_hash=hash_senha, papel=PAPEL_TESTE)
            )
            await sessao.commit()
            logger.info("Usuário de teste criado: %s", EMAIL_TESTE)
        else:
            usuario.senha_hash = hash_senha
            usuario.nome = NOME_TESTE
            await sessao.commit()
            logger.info("Usuário de teste já existia, senha e nome atualizados: %s", EMAIL_TESTE)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(semear_usuario_teste())
