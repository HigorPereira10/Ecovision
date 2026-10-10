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

Escopo por dono: o produtor só vê alertas originados dos dispositivos
dele. Um alerta nasce ligado a um diagnóstico OU a uma leitura (ver
app/api/routes/diagnostico.py), e os dois caminhos chegam ao device_id
pela tabela registros_imagem, então o filtro cobre os dois. Isso vale
também para o alerta sintético de dispositivo inativo, que passa a
olhar só as capturas dos dispositivos do produtor, e para o PATCH de
leitura, que responde 404 em alerta de outro dono.

Relação com o resto do sistema:
- Depende de app/db/models.py (tabela alertas) e
  app/core/alertas_dispositivo.py (ADR 0008) para o item sintético.
- app/core/security.py (obter_produtor_atual, exige login).
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
    """Timestamp da captura mais recente entre os dispositivos que este
    produtor enxerga. None se nenhuma captura foi recebida ainda.

    `device_ids=None` significa acesso irrestrito (administrador) e não
    aplica filtro; uma lista vazia restringe a nada, que é o correto
    para um produtor sem dispositivos: sem isso, ele receberia o alerta
    de "dispositivo inativo" de uma estufa que nem é dele."""
    consulta = select(RegistroImagem.criado_em).order_by(RegistroImagem.criado_em.desc()).limit(1)
    if device_ids is not None:
        consulta = consulta.where(RegistroImagem.device_id.in_(device_ids))
    resultado = await sessao.execute(consulta)
    return resultado.scalar_one_or_none()


def _filtro_de_posse(device_ids: list[str]):
    """Cláusula que mantém só os alertas originados dos dispositivos
    informados. Um alerta aponta para um diagnóstico OU para uma
    leitura, nunca para os dois, então as duas sub-consultas abaixo
    cobrem todos os casos."""
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
    """Lista alertas persistidos (mais recente primeiro) mais o item
    sintético de dispositivo inativo, se aplicável (ver ADR 0008).
    Restrito aos dispositivos do produtor autenticado."""
    device_ids = await device_ids_visiveis(sessao, produtor)

    consulta = select(Alerta).order_by(Alerta.criado_em.desc())
    if device_ids is not None:
        consulta = consulta.where(_filtro_de_posse(device_ids))

    resultado = await sessao.execute(consulta)
    alertas = [AlertaOut.model_validate(alerta) for alerta in resultado.scalars().all()]

    # Produtor SEM nenhum dispositivo vinculado não recebe o alerta
    # sintético. Sem esta guarda, quem acabou de se cadastrar e ainda
    # nem tem equipamento via "Dispositivo nunca reportou dados.
    # Verifique a alimentação, a conexão Wi-Fi e os logs do Raspberry
    # Pi", falando de um aparelho que não existe.
    #
    # `device_ids is None` é o administrador, que enxerga tudo e por
    # isso continua recebendo o alerta normalmente.
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
    """Marca um alerta real como lido. 404 se o id não existir (isso
    também cobre a tentativa de marcar o item sintético como lido: ele
    nunca tem uma linha real na tabela, então qualquer id que o
    frontend inventar para ele vai cair aqui como 404).

    Alerta de outro dono responde 404, e não 403, de propósito: 403
    confirmaria que aquele id existe, deixando um produtor descobrir
    quantos alertas os outros têm testando ids em sequência."""
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
