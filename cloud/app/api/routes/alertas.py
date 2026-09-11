"""
cloud/app/api/routes/alertas.py

Endpoints de alertas para o dashboard do produtor:
- GET /alertas: lista os alertas persistidos (doença/praga, ver ADR 0006,
  e risco ambiental, ver ADR 0005) MAIS um item sintético de "dispositivo
  inativo" (ADR 0008), quando aplicável. O item sintético não existe na
  tabela `alertas` (não é gravado no banco); ver AlertaOut em
  app/db/schemas.py para o campo `sintetico` que sinaliza isso ao
  frontend.
- PATCH /alertas/{id}/lido: marca um alerta real como lido. Só aceita
  IDs de alertas de verdade (o item sintético tem id=None e não pode
  ser marcado como lido por este endpoint).

Escopo aceito nesta rodada: mesma simplificação de historico.py (só 1
dispositivo físico, sem filtrar por dono).

Relação com o resto do sistema:
- Depende de app/db/models.py (tabela alertas) e
  app/core/alertas_dispositivo.py (ADR 0008) para o item sintético.
- app/core/security.py (obter_produtor_atual, exige login).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.alertas_dispositivo import avaliar_inatividade_dispositivo
from app.core.security import obter_produtor_atual
from app.db.models import Alerta, RegistroImagem
from app.db.schemas import AlertaOut
from app.db.session import get_session

router = APIRouter()


async def _obter_ultima_captura(sessao: AsyncSession):
    """Timestamp da captura mais recente entre TODOS os dispositivos
    (só existe 1 na prática, ver docstring do módulo). None se nenhuma
    captura foi recebida ainda."""
    resultado = await sessao.execute(
        select(RegistroImagem.criado_em).order_by(RegistroImagem.criado_em.desc()).limit(1)
    )
    return resultado.scalar_one_or_none()


@router.get("/alertas", response_model=list[AlertaOut])
async def listar_alertas(
    _produtor: dict = Depends(obter_produtor_atual),
    sessao: AsyncSession = Depends(get_session),
) -> list[AlertaOut]:
    """Lista alertas persistidos (mais recente primeiro) mais o item
    sintético de dispositivo inativo, se aplicável (ver ADR 0008)."""
    resultado = await sessao.execute(select(Alerta).order_by(Alerta.criado_em.desc()))
    alertas = [AlertaOut.model_validate(alerta) for alerta in resultado.scalars().all()]

    ultima_captura = await _obter_ultima_captura(sessao)
    alerta_dispositivo = avaliar_inatividade_dispositivo(ultima_captura)

    if alerta_dispositivo is not None:
        titulo, descricao, severidade = alerta_dispositivo
        alertas.insert(
            0,
            AlertaOut(
                id=None,
                titulo=titulo,
                descricao=descricao,
                severidade=severidade,
                lido=False,
                criado_em=ultima_captura or datetime.now(timezone.utc),
                sintetico=True,
            ),
        )

    return alertas


@router.patch("/alertas/{alerta_id}/lido", response_model=AlertaOut)
async def marcar_alerta_como_lido(
    alerta_id: int,
    _produtor: dict = Depends(obter_produtor_atual),
    sessao: AsyncSession = Depends(get_session),
) -> Alerta:
    """Marca um alerta real como lido. 404 se o id não existir (isso
    também cobre a tentativa de marcar o item sintético como lido: ele
    nunca tem uma linha real na tabela, então qualquer id que o
    frontend inventar para ele vai cair aqui como 404)."""
    alerta = await sessao.get(Alerta, alerta_id)
    if alerta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta não encontrado.")

    alerta.lido = True
    await sessao.commit()
    await sessao.refresh(alerta)
    return alerta
