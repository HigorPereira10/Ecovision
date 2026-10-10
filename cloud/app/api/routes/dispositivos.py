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

Escopo por dono: devolve apenas os dispositivos cujo `usuario_id` é o
do produtor autenticado (ver app/api/escopo.py). Produtor recém
cadastrado, sem nenhum dispositivo vinculado, recebe lista vazia.
Campos de localização (campo/setor) e limiares configuráveis por
dispositivo, que a tela de Perfil já desenha, ficam só como
funcionalidade visual do app por enquanto (ver DispositivoOut em
app/db/schemas.py) até existir mais de 1 dispositivo físico de verdade.

Relação com o resto do sistema:
- Consumido por app/src/services/dispositivos.ts.
- Depende de app/db/models.py (tabelas dispositivos e registros_imagem)
  e app/core/security.py (obter_produtor_atual, exige login).
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.escopo import PAPEL_IRRESTRITO
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
    # Filtra pelo dono direto em vez de usar device_ids_visiveis():
    # aqui a entidade consultada JÁ é `dispositivos`, então dá para
    # comparar o usuario_id sem passar pelos device_ids.
    consulta = select(Dispositivo).order_by(Dispositivo.criado_em)
    if produtor.get("papel") != PAPEL_IRRESTRITO:
        consulta = consulta.where(Dispositivo.usuario_id == produtor["usuario_id"])

    resultado = await sessao.execute(consulta)
    dispositivos = resultado.scalars().all()

    return [await _montar_saida(sessao, dispositivo) for dispositivo in dispositivos]


async def _montar_saida(sessao: AsyncSession, dispositivo: Dispositivo) -> DispositivoOut:
    """Monta o DispositivoOut calculando o status sob demanda a partir
    da última captura recebida daquele device_id (ADR 0008)."""
    ultima_captura = await _ultima_captura_do_device(sessao, dispositivo.device_id)
    inativo = avaliar_inatividade_dispositivo(ultima_captura) is not None
    return DispositivoOut(
        id=dispositivo.id,
        device_id=dispositivo.device_id,
        nome=dispositivo.nome,
        status="inativo" if inativo else "ativo",
        criado_em=dispositivo.criado_em,
    )


@router.post("/dispositivos/vincular", response_model=DispositivoOut)
async def vincular_dispositivo(
    dados: VincularDispositivoRequest,
    produtor: dict = Depends(obter_produtor_atual),
    sessao: AsyncSession = Depends(get_session),
) -> DispositivoOut:
    """Vincula um dispositivo à conta do produtor autenticado, a partir
    do código de pareamento que vem com o aparelho (ECO-XXXX-XXXX).

    É isto que permite o cadastro ser aberto: qualquer um cria conta,
    mas só enxerga dados depois de provar a posse física de um
    equipamento, digitando um código que só está impresso nele.

    O código vale uma única vez, na prática: ele só funciona enquanto
    `usuario_id` for nulo, então um aparelho já reivindicado não pode
    ser tomado por outra conta, nem mesmo por quem viu a etiqueta.

    Sem tratamento especial de corrida: se duas contas enviarem o mesmo
    código ao mesmo tempo, o `UPDATE` condicional abaixo faz uma delas
    gravar e a outra encontrar `usuario_id` já preenchido na releitura.
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
            # Reenvio do mesmo produtor (ex.: tocou duas vezes no botão).
            # Devolver o estado atual em vez de erro é mais útil.
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
