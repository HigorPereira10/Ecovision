"""
Rotas de dispositivos:
- GET /dispositivos: dispositivos vinculados ao usuário, com `status`
  ("ativo" ou "inativo") calculado a partir da última captura
  (app/core/alertas_dispositivo.py);
- POST /dispositivos/vincular: vínculo pelo código de pareamento.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.escopo import PAPEL_IRRESTRITO
from app.core.alertas_ambientais import (
    TEMPERATURA_MAX_C,
    UMIDADE_AR_MAX_PCT,
    UMIDADE_SOLO_MIN_PCT,
)
from app.core.alertas_dispositivo import avaliar_inatividade_dispositivo
from app.core.security import obter_produtor_atual
from app.db.models import Dispositivo, RegistroImagem
from app.db.schemas import DispositivoOut, VincularDispositivoRequest
from app.db.session import get_session

logger = logging.getLogger("ecovision.cloud.dispositivos")

router = APIRouter()


async def _ultima_captura_do_device(sessao: AsyncSession, device_id: str) -> datetime | None:
    resultado = await sessao.execute(
        select(RegistroImagem.criado_em)
        .where(RegistroImagem.device_id == device_id)
        .order_by(RegistroImagem.criado_em.desc())
        .limit(1)
    )
    return resultado.scalar_one_or_none()


@router.get("/dispositivos", response_model=list[DispositivoOut])
async def listar_dispositivos(
    produtor: dict = Depends(obter_produtor_atual),
    sessao: AsyncSession = Depends(get_session),
) -> list[DispositivoOut]:
    # A entidade consultada já é `dispositivos`: filtra direto pelo dono.
    consulta = select(Dispositivo).order_by(Dispositivo.criado_em)
    if produtor.get("papel") != PAPEL_IRRESTRITO:
        consulta = consulta.where(Dispositivo.usuario_id == produtor["usuario_id"])

    resultado = await sessao.execute(consulta)
    dispositivos = resultado.scalars().all()

    return [await _montar_saida(sessao, dispositivo) for dispositivo in dispositivos]


async def _montar_saida(sessao: AsyncSession, dispositivo: Dispositivo) -> DispositivoOut:
    """Monta o DispositivoOut com o status calculado a partir da última
    captura do dispositivo."""
    ultima_captura = await _ultima_captura_do_device(sessao, dispositivo.device_id)
    inativo = avaliar_inatividade_dispositivo(ultima_captura) is not None
    return DispositivoOut(
        id=dispositivo.id,
        device_id=dispositivo.device_id,
        nome=dispositivo.nome,
        status="inativo" if inativo else "ativo",
        criado_em=dispositivo.criado_em,
        campo=dispositivo.campo,
        setor=dispositivo.setor,
        intervalo_captura_min=dispositivo.intervalo_captura_min,
        # Limiares usados pela lógica de alertas (ver DispositivoOut).
        limiar_temperatura=TEMPERATURA_MAX_C,
        limiar_umidade_ar=UMIDADE_AR_MAX_PCT,
        limiar_umidade_solo=UMIDADE_SOLO_MIN_PCT,
    )


@router.post("/dispositivos/vincular", response_model=DispositivoOut)
async def vincular_dispositivo(
    dados: VincularDispositivoRequest,
    produtor: dict = Depends(obter_produtor_atual),
    sessao: AsyncSession = Depends(get_session),
) -> DispositivoOut:
    """Vincula um dispositivo à conta do usuário pelo código de pareamento
    (ECO-XXXX-XXXX).

    O código só vale enquanto o dispositivo não tem dono, o que impede
    reivindicar um aparelho já vinculado. Em envios simultâneos do mesmo
    código, o UPDATE condicional garante que só uma conta grava.
    """
    codigo = dados.codigo.strip().upper()

    dispositivo = await sessao.scalar(
        select(Dispositivo).where(Dispositivo.codigo_pareamento == codigo)
    )

    if dispositivo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Código de pareamento não encontrado. Confira a etiqueta do aparelho.",
        )

    if dispositivo.usuario_id is not None:
        if dispositivo.usuario_id == produtor["usuario_id"]:
            # Reenvio pelo próprio dono: devolve o estado atual.
            return await _montar_saida(sessao, dispositivo)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este dispositivo já está vinculado a outra conta.",
        )

    dispositivo.usuario_id = produtor["usuario_id"]
    dispositivo.pareado_em = datetime.now(timezone.utc)
    await sessao.commit()
    await sessao.refresh(dispositivo)

    logger.info(
        "Dispositivo %s vinculado ao usuario_id=%s",
        dispositivo.device_id,
        produtor["usuario_id"],
    )
    return await _montar_saida(sessao, dispositivo)
