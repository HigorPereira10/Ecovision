"""
cloud/app/api/routes/dispositivos.py

GET /dispositivos: lista os dispositivos IoT cadastrados (tabela
`dispositivos`), para a tela de Perfil do app.

Decisão do grupo em 2026-09-14: o projeto tem só 1 Raspberry Pi físico
até agora, mas a tela de Perfil já foi desenhada para exibir uma lista
(pensando num produtor com mais de uma estufa no futuro). Esta rota
devolve a lista de verdade (hoje, na prática, sempre com 0 ou 1 item);
o app não precisa saber se é 1 ou N, só itera a lista normalmente.

`status` ('ativo' | 'inativo') é computado sob demanda a partir da
última captura recebida daquele device_id, reaproveitando
app/core/alertas_dispositivo.py (ADR 0008) em vez de duplicar os
limiares de atraso numa segunda lógica.

Escopo aceito nesta rodada: mesma simplificação de historico.py e
alertas.py (só 1 dispositivo físico de verdade, sem filtrar por dono).
Campos de localização (campo/setor) e limiares configuráveis por
dispositivo, que a tela de Perfil já desenha, ficam só como
funcionalidade visual do app por enquanto (ver DispositivoOut em
app/db/schemas.py) até existir mais de 1 dispositivo físico de verdade.

Relação com o resto do sistema:
- Consumido por app/src/services/dispositivos.ts.
- Depende de app/db/models.py (tabelas dispositivos e registros_imagem)
  e app/core/security.py (obter_produtor_atual, exige login).
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.alertas_dispositivo import avaliar_inatividade_dispositivo
from app.core.security import obter_produtor_atual
from app.db.models import Dispositivo, RegistroImagem
from app.db.schemas import DispositivoOut
from app.db.session import get_session

router = APIRouter()


async def _ultima_captura_do_device(sessao: AsyncSession, device_id: str) -> datetime | None:
    resultado = await sessao.execute(
        select(RegistroImagem.criado_em)
        .where(RegistroImagem.device_id == device_id)
        .order_by(RegistroImagem.criado_em.desc())
        .limit(1)
    )
    return resultado.scalar_one_or_none()


@router.get("/dispositivos", response_model=list[DispositivoOut], dependencies=[Depends(obter_produtor_atual)])
async def listar_dispositivos(sessao: AsyncSession = Depends(get_session)) -> list[DispositivoOut]:
    resultado = await sessao.execute(select(Dispositivo).order_by(Dispositivo.criado_em))
    dispositivos = resultado.scalars().all()

    saida = []
    for dispositivo in dispositivos:
        ultima_captura = await _ultima_captura_do_device(sessao, dispositivo.device_id)
        inativo = avaliar_inatividade_dispositivo(ultima_captura) is not None
        saida.append(
            DispositivoOut(
                id=dispositivo.id,
                device_id=dispositivo.device_id,
                nome=dispositivo.nome,
                status="inativo" if inativo else "ativo",
                criado_em=dispositivo.criado_em,
            )
        )
    return saida
