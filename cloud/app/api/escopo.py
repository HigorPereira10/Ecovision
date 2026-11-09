"""
Escopo por dono: define quais dispositivos cada usuário enxerga nas rotas
de consulta (/leituras, /diagnosticos, /alertas e /dispositivos).

Cadeia de posse:

    usuarios.id
      <- dispositivos.usuario_id
         (dispositivos.device_id == registros_imagem.device_id)
           <- leituras_ambientais / diagnosticos
              <- alertas

registros_imagem.device_id não tem chave estrangeira: uma captura de um
device_id sem dono em `dispositivos` fica gravada, mas não aparece para
nenhum usuário. O administrador vê tudo; esse papel nunca é concedido pelo
cadastro público.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Dispositivo

PAPEL_IRRESTRITO = "administrador"


async def device_ids_visiveis(sessao: AsyncSession, produtor: dict) -> list[str] | None:
    """Device ids visíveis para o usuário.

    Devolve None para acesso irrestrito (administrador). Uma lista vazia
    significa usuário sem dispositivos, e as rotas devem devolver zero
    itens.
    """
    if produtor.get("papel") == PAPEL_IRRESTRITO:
        return None

    resultado = await sessao.execute(
        select(Dispositivo.device_id).where(Dispositivo.usuario_id == produtor["usuario_id"])
    )
    return list(resultado.scalars().all())
