"""
POST /leituras: leituras de sensores enviadas pelo dispositivo a cada 15
minutos, sem foto.

Difere de POST /diagnostico por receber JSON (não há arquivo) e por não
passar pela fila local do dispositivo. Gera os mesmos alertas ambientais,
pelo mesmo código (app/api/alertas_de_leitura.py). A consulta das
leituras (GET /leituras, com autenticação de usuário) fica em
app/api/routes/historico.py.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.alertas_de_leitura import montar_alertas_ambientais
from app.api.dispositivo_auth import autenticar_dispositivo
from app.core.security import obter_credencial_dispositivo
from app.db.models import LeituraAmbiental
from app.db.schemas import LeituraDispositivoIn, LeituraOut
from app.db.session import get_session

logger = logging.getLogger("ecovision.cloud.leituras")

router = APIRouter()


def _para_saida(leitura: LeituraAmbiental) -> dict:
    """Monta a resposta no formato de GET /leituras; `tem_foto` indica se a
    leitura veio de um ciclo de captura."""
    return {
        "id": leitura.id,
        "device_id": leitura.device_id,
        "temperatura_c": leitura.temperatura_c,
        "umidade_ar_pct": leitura.umidade_ar_pct,
        "umidade_solo_pct": leitura.umidade_solo_pct,
        "tem_foto": leitura.registro_imagem_id is not None,
        "criado_em": leitura.criado_em,
    }


async def _buscar_por_idempotency_key(
    sessao: AsyncSession, chave: str
) -> LeituraAmbiental | None:
    return await sessao.scalar(
        select(LeituraAmbiental).where(LeituraAmbiental.idempotency_key == chave)
    )


@router.post("/leituras", response_model=LeituraOut, status_code=status.HTTP_201_CREATED)
async def receber_leitura(
    dados: LeituraDispositivoIn,
    credencial: str = Depends(obter_credencial_dispositivo),
    sessao: AsyncSession = Depends(get_session),
) -> dict:
    """Recebe uma leitura de sensores do dispositivo, sem foto."""
    # A autenticação usa o device_id do corpo (ver app/api/dispositivo_auth.py).
    await autenticar_dispositivo(sessao, dados.device_id, credencial)

    existente = await _buscar_por_idempotency_key(sessao, dados.idempotency_key)
    if existente is not None:
        logger.info(
            "Reenvio de leitura detectado (idempotency_key=%s): devolvendo a "
            "linha já gravada.",
            dados.idempotency_key,
        )
        return _para_saida(existente)

    # Uma requisição com as três medições nulas é aceita: indica que o
    # ciclo ocorreu sem resposta dos sensores, o que permite distinguir
    # sensor com falha de dispositivo desligado.
    leitura = LeituraAmbiental(
        device_id=dados.device_id,
        registro_imagem_id=None,
        idempotency_key=dados.idempotency_key,
        temperatura_c=dados.temperatura_c,
        umidade_ar_pct=dados.umidade_ar_pct,
        umidade_solo_pct=dados.umidade_solo_pct,
    )
    sessao.add(leitura)

    try:
        await sessao.flush()  # obtém leitura.id antes dos alertas

        for alerta in montar_alertas_ambientais(leitura):
            sessao.add(alerta)

        await sessao.commit()
    except IntegrityError:
        # Requisições simultâneas com a mesma chave: a perdedora devolve o
        # resultado da vencedora.
        await sessao.rollback()
        logger.info(
            "Corrida de idempotency_key=%s em /leituras: devolvendo a linha "
            "da requisição que venceu.",
            dados.idempotency_key,
        )
        vencedora = await _buscar_por_idempotency_key(sessao, dados.idempotency_key)
        if vencedora is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Falha ao gravar a leitura.",
            )
        return _para_saida(vencedora)

    await sessao.refresh(leitura)

    logger.info(
        "Leitura %s registrada para device_id=%s (T=%s, ar=%s, solo=%s)",
        leitura.id, leitura.device_id,
        leitura.temperatura_c, leitura.umidade_ar_pct, leitura.umidade_solo_pct,
    )
    return _para_saida(leitura)
