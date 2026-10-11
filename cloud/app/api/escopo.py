"""
cloud/app/api/escopo.py

Decide QUAIS dispositivos cada produtor autenticado enxerga, para que
as rotas de leitura (/leituras, /diagnosticos, /alertas, /dispositivos)
devolvam só os dados das estufas dele.

Por que isto existe: antes, essas rotas exigiam login mas devolviam os
dados de TODOS os dispositivos. Isso era aceitável enquanto o sistema
era fechado (a única conta era semeada à mão por scripts/). Com o
cadastro aberto por POST /auth/register, qualquer pessoa passaria a
criar uma conta e ver a estufa dos outros, então o filtro por dono
deixou de ser opcional.

A cadeia de posse é:

    usuarios.id
      <- dispositivos.usuario_id
         (dispositivos.device_id == registros_imagem.device_id)
           <- leituras_ambientais / diagnosticos
              <- alertas

ATENÇÃO (consequência operacional): `registros_imagem.device_id` é uma
string livre, sem chave estrangeira para `dispositivos`. O Pi envia o
device_id que estiver no .env dele, autenticado pela credencial daquele
aparelho (ADR 0009). Logo, uma captura cujo device_id não tenha linha
em `dispositivos`, ou cuja linha esteja com usuario_id nulo, NÃO tem
dono e fica invisível para todo mundo. Os dados continuam no banco,
mas nenhuma tela mostra. Para o Pi real aparecer, a tabela
`dispositivos` precisa ter o device_id dele vinculado a um usuário,
o que acontece quando o produtor digita o código de pareamento no app
(POST /dispositivos/vincular) ou, em ambiente de teste, via
cloud/scripts/seed_dispositivo_teste.py.

Administrador vê tudo: é o papel usado para suporte e para a
apresentação, e é concedido só via seed manual, nunca pelo cadastro
público (ver app/api/routes/auth.py, que força papel='produtor').
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Dispositivo

PAPEL_IRRESTRITO = "administrador"


async def device_ids_visiveis(sessao: AsyncSession, produtor: dict) -> list[str] | None:
    """Device ids que este produtor pode ver.

    Devolve None quando o acesso é irrestrito (administrador), o que as
    rotas tratam como "não aplicar filtro". Uma lista VAZIA é diferente
    de None: significa um produtor sem nenhum dispositivo vinculado, e
    as rotas devem devolver zero itens nesse caso, não a tabela toda.
    """
    if produtor.get("papel") == PAPEL_IRRESTRITO:
        return None

    resultado = await sessao.execute(
        select(Dispositivo.device_id).where(Dispositivo.usuario_id == produtor["usuario_id"])
    )
    return list(resultado.scalars().all())
