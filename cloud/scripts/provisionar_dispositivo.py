"""
Provisiona um dispositivo na tabela `dispositivos`, gerando:

- o segredo do dispositivo, para o .env do aparelho; o banco guarda só o
  hash, e o valor em claro é exibido uma única vez;
- o código de pareamento (ECO-XXXX-XXXX), para a etiqueta do aparelho,
  usado pelo produtor no aplicativo (POST /dispositivos/vincular).

O dispositivo é criado sem dono. Executar de novo para um device_id
existente gera novo segredo e novo código, mantendo o dono.

Uso (em cloud/, com o ambiente configurado):

    python -m scripts.provisionar_dispositivo <device_id> "<nome>"
"""

import asyncio
import logging
import sys

from sqlalchemy import select

from app.core.security import (
    gerar_codigo_pareamento,
    gerar_hash_senha,
    gerar_segredo_dispositivo,
)
from app.db.models import Dispositivo
from app.db.session import _SessionLocal

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("ecovision.cloud.provisionar")


async def provisionar(device_id: str, nome: str) -> None:
    segredo = gerar_segredo_dispositivo()
    codigo = gerar_codigo_pareamento()

    async with _SessionLocal() as sessao:
        dispositivo = await sessao.scalar(
            select(Dispositivo).where(Dispositivo.device_id == device_id)
        )

        if dispositivo is None:
            dispositivo = Dispositivo(device_id=device_id, nome=nome)
            sessao.add(dispositivo)
            acao = "criado"
        else:
            dispositivo.nome = nome
            acao = "atualizado (segredo e codigo rotacionados)"

        dispositivo.chave_hash = gerar_hash_senha(segredo)
        dispositivo.codigo_pareamento = codigo
        await sessao.commit()
        await sessao.refresh(dispositivo)

        dono = dispositivo.usuario_id

    print()
    print("=" * 66)
    print(f"  Dispositivo {acao}: {device_id}")
    print("=" * 66)
    print(f"  Nome        : {nome}")
    print(f"  Dono atual  : {dono if dono is not None else 'nenhum (aguardando pareamento)'}")
    print()
    print("  VAI NO .env DO RASPBERRY (edge/.env):")
    print(f"    DEVICE_ID={device_id}")
    print(f"    DEVICE_API_KEY={segredo}")
    print()
    print("  VAI NA ETIQUETA DO APARELHO (o agricultor digita no app):")
    print(f"    {codigo}")
    print()
    print("  O segredo acima nao volta a ser exibido: guarde agora.")
    print("=" * 66)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("uso: python -m scripts.provisionar_dispositivo <device_id> [nome]")
    device_id_arg = sys.argv[1]
    nome_arg = sys.argv[2] if len(sys.argv) > 2 else device_id_arg
    asyncio.run(provisionar(device_id_arg, nome_arg))
