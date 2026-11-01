"""
cloud/scripts/seed_admin.py

Cria a conta de ADMINISTRADOR do grupo, usada para que mais de um
integrante consiga acompanhar os dados sem disputar a posse do
dispositivo físico.

POR QUE ISTO EXISTE
-------------------
O pareamento é de uso único por construção: `POST /dispositivos/vincular`
só aceita um aparelho cujo `usuario_id` ainda é nulo, e devolve 409 se
já houver dono (ver app/api/routes/dispositivos.py). Isso é proposital,
porque é o que garante que ninguém reivindique um equipamento alheio
tendo visto a etiqueta.

Consequência prática: com uma única placa, só uma conta de produtor
enxerga os dados. Para os outros integrantes acompanharem a coleta, o
caminho previsto pelo próprio sistema é o papel de administrador, que
em app/api/escopo.py recebe filtro nulo e portanto vê todos os
dispositivos sem parear nada.

POR QUE NÃO USAR O CADASTRO DO APP
----------------------------------
`POST /auth/register` força `papel='produtor'`, ignorando o que vier na
requisição (app/api/routes/auth.py), e o login exige `email_verificado`.
Como `admin@ecovision.app` não é caixa postal real, a conta ficaria
presa sem confirmação. Por isso a criação é direta, com
`email_verificado=True`, igual ao que já é feito em
seed_usuario_teste.py.

O QUE ESTA CONTA NÃO DEVE SER USADA PARA
----------------------------------------
Não use esta conta na demonstração para a banca. Administrador vê tudo,
sem filtro de posse, então a tela não demonstraria o controle de acesso
que o trabalho descreve. Para isso use uma conta de produtor, que é a
dona do dispositivo.

SENHA
-----
A senha NÃO está neste arquivo. Ela vem da variável de ambiente
`SENHA_ADMIN`, e o script recusa rodar sem ela.

POR QUE: este repositório vai se tornar público. Senha de um papel
irrestrito escrita em texto claro no código continuaria legível no
histórico do git mesmo depois de removida do arquivo, e trocá-la depois
da abertura não apaga a versão antiga dos commits anteriores. Variável
de ambiente nunca entra no versionamento.

A senha precisa satisfazer as cinco regras que o app exige no cadastro
(app/src/screens/CadastroScreen.tsx): oito caracteres, maiúscula,
minúscula, número e símbolo.

Como rodar, de dentro de cloud/, com o venv ativado e as variáveis de
ambiente reais carregadas. No bash:

    SENHA_ADMIN='...' python -m scripts.seed_admin

No PowerShell, definindo a variável antes:

    $env:SENHA_ADMIN = '...'
    python -m scripts.seed_admin

Idempotente: se a conta já existir, apenas atualiza senha, nome e
papel, sem criar duplicata (email é UNIQUE em app/db/models.py).
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

# Mínimo exigido pelo cadastro do app. Checado aqui também para o script
# não semear uma senha que o próprio aplicativo recusaria depois.
TAMANHO_MINIMO_SENHA = 8


def _senha_do_ambiente() -> str:
    """Lê a senha do ambiente. Sai com erro se faltar, em vez de cair num
    valor padrão: um padrão embutido é exatamente o que este script
    deixou de ter, porque o repositório será público."""
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
                    # Sem caixa postal real, a confirmação por e-mail
                    # nunca chegaria e o login devolveria 403.
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
