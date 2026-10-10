"""
cloud/scripts/seed_usuario_teste.py

Cria (ou atualiza a senha de) a conta de produtor usada para testar o
login de verdade contra a API, com as MESMAS credenciais que o mock do
app/ já usa (app/src/services/auth.ts): produtor@ecovision.app /
tomate123. Decisão do grupo em 2026-09-11: por enquanto não existe
endpoint de cadastro (POST /auth/registrar); a primeira conta é
semeada manualmente assim, direto no banco configurado em DATABASE_URL.

Como rodar (dentro de cloud/, com o venv ativado e as variáveis de
ambiente reais carregadas, ou seja, contra o Supabase de verdade):

    python -m scripts.seed_usuario_teste

Idempotente: rodar de novo só atualiza o hash da senha se o usuário já
existir, não cria duplicata (email é UNIQUE em app/db/models.py).
"""

import asyncio
import logging

from sqlalchemy import select

from app.core.security import gerar_hash_senha
from app.db.models import Usuario
from app.db.session import _SessionLocal

logger = logging.getLogger("ecovision.cloud.seed")

# ATENCAO: rodar este script SOBRESCREVE A SENHA da conta abaixo pela
# SENHA_TESTE, que e fraca e publica (esta aqui no codigo). Desde
# 2026-10-10 esse email e a conta real do grupo em producao, dona do
# pi-estufa-01. Rodar isto contra o banco de producao rebaixaria a
# seguranca dela sem avisar ninguem.
#
# Use apenas contra banco LOCAL de desenvolvimento. Para criar conta em
# producao, use o cadastro do proprio app (POST /auth/register), que
# exige senha forte.

NOME_TESTE = "Produtor EcoVision"
# Conta de produtor do grupo, dona do Pi real. E-mail neutro do
# projeto em vez do nome de alguem: ele aparece na tela de Perfil, e
# essa tela vai para a apresentacao.
EMAIL_TESTE = "produtor@ecovision.app"
SENHA_TESTE = "tomate123"
PAPEL_TESTE = "produtor"


async def semear_usuario_teste() -> None:
    async with _SessionLocal() as sessao:
        resultado = await sessao.execute(select(Usuario).where(Usuario.email == EMAIL_TESTE))
        usuario = resultado.scalar_one_or_none()

        hash_senha = gerar_hash_senha(SENHA_TESTE)

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
