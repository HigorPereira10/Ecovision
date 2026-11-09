"""
Rotas de alertas:
- GET /alertas: alertas gravados (de diagnóstico e ambientais) e, quando
  aplicável, o alerta sintético de dispositivo inativo, que não existe na
  tabela (campo `sintetico` em AlertaOut);
- PATCH /alertas/{id}/lido: marca um alerta gravado como lido.

O usuário vê apenas os alertas originados de seus dispositivos; alerta de
outro dono responde 404.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.escopo import device_ids_visiveis
from app.core.alertas_dispositivo import avaliar_inatividade_dispositivo
from app.core.security import obter_produtor_atual
from app.db.models import Alerta, Diagnostico, LeituraAmbiental, RegistroImagem
from app.db.schemas import AlertaOut
from app.db.session import get_session

router = APIRouter()


async def _obter_ultima_captura(sessao: AsyncSession, device_ids: list[str] | None):
    """Momento da captura mais recente entre os dispositivos visíveis, ou
    None.

    `device_ids=None` significa acesso irrestrito (administrador); uma
    lista vazia não retorna nada."""
    consulta = select(RegistroImagem.criado_em).order_by(RegistroImagem.criado_em.desc()).limit(1)
    if device_ids is not None:
        consulta = consulta.where(RegistroImagem.device_id.in_(device_ids))
    resultado = await sessao.execute(consulta)
    return resultado.scalar_one_or_none()


def _filtro_de_posse(device_ids: list[str]):
    """Filtro dos alertas originados dos dispositivos informados. Um
    alerta aponta para um diagnóstico ou para uma leitura, e as duas
    subconsultas cobrem os dois casos."""
    diagnosticos_do_dono = (
        select(Diagnostico.id)
        .join(RegistroImagem, Diagnostico.registro_imagem_id == RegistroImagem.id)
        .where(RegistroImagem.device_id.in_(device_ids))
    )
    leituras_do_dono = (
        select(LeituraAmbiental.id)
        .join(RegistroImagem, LeituraAmbiental.registro_imagem_id == RegistroImagem.id)
        .where(RegistroImagem.device_id.in_(device_ids))
    )
    return or_(
        Alerta.diagnostico_id.in_(diagnosticos_do_dono),
        Alerta.leitura_id.in_(leituras_do_dono),
    )


@router.get("/alertas", response_model=list[AlertaOut])
async def listar_alertas(
    produtor: dict = Depends(obter_produtor_atual),
    sessao: AsyncSession = Depends(get_session),
) -> list[AlertaOut]:
    """Lista os alertas gravados, do mais recente ao mais antigo, e o alerta
    sintético de dispositivo inativo, quando aplicável."""
    device_ids = await device_ids_visiveis(sessao, produtor)

    consulta = select(Alerta).order_by(Alerta.criado_em.desc())
    if device_ids is not None:
        consulta = consulta.where(_filtro_de_posse(device_ids))

    resultado = await sessao.execute(consulta)
    alertas = [AlertaOut.model_validate(alerta) for alerta in resultado.scalars().all()]

    # Usuário sem dispositivo vinculado não recebe o alerta de inatividade;
    # o administrador (device_ids is None) recebe normalmente.
    tem_dispositivo = device_ids is None or len(device_ids) > 0

    ultima_captura = None
    alerta_dispositivo = None
    if tem_dispositivo:
        ultima_captura = await _obter_ultima_captura(sessao, device_ids)
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
    produtor: dict = Depends(obter_produtor_atual),
    sessao: AsyncSession = Depends(get_session),
) -> Alerta:
    """Marca um alerta gravado como lido.

    Responde 404 para id inexistente, para o alerta sintético e para
    alerta de outro dono (403 revelaria que o id existe)."""
    alerta = await sessao.get(Alerta, alerta_id)
    if alerta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta não encontrado.")

    device_ids = await device_ids_visiveis(sessao, produtor)
    if device_ids is not None:
        pertence = await sessao.execute(
            select(Alerta.id).where(Alerta.id == alerta_id, _filtro_de_posse(device_ids))
        )
        if pertence.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Alerta não encontrado."
            )

    alerta.lido = True
    await sessao.commit()
    await sessao.refresh(alerta)
    return alerta
