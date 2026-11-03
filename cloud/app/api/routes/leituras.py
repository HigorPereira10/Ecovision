"""
cloud/app/api/routes/leituras.py

Endpoint de ingestão de leitura ambiental SEM foto: POST /leituras

POR QUE ESTE ENDPOINT EXISTE
----------------------------
Até a migration 0008, leitura de sensor só entrava no sistema de carona
em POST /diagnostico, porque `leituras_ambientais.registro_imagem_id`
era obrigatório. O Pi lia os sensores e tirava a foto no mesmo ciclo, a
cada 2 horas, e mandava os dois juntos.

A consequência aparecia na tela inicial do app: a temperatura exibida
podia ter até 2 horas de idade, e não havia nada mais novo para buscar.
Pior, o card mostrava o número sem marca de tempo, então 29,7 °C medido
às 19:49 era lido como a temperatura de agora.

O ciclo de 2 horas é caro por causa da FOTO: acionar o LED, comprimir
1,2 MB, subir para o Storage, rodar a inferência TFLite. Ler o DHT22
leva 2 segundos e a requisição abaixo tem umas três linhas de JSON.
Então o Pi passou a fazer dois cronogramas (ver edge/crontab.example):

  sensor sem foto    a cada 15 min   -> POST /leituras   (este módulo)
  foto + sensor      a cada  2 h     -> POST /diagnostico

DIFERENÇAS DELIBERADAS EM RELAÇÃO A POST /diagnostico
-----------------------------------------------------
1. Corpo em JSON, não multipart. Multipart existe lá para carregar o
   arquivo; sem arquivo, seria só cerimônia.

2. Sem fila offline no Pi. Perder uma amostra de sensor custa quase
   nada: a próxima vem em 15 minutos e a série continua legível. Perder
   uma FOTO custa um diagnóstico, e é por isso que só ela passa pela
   fila de edge/src/fila/offline_queue.py. Ver a nota em
   edge/src/sensores.py.

3. Não gera alerta de doença, obviamente, mas gera os MESMOS alertas
   ambientais, pelo mesmo código (app/api/alertas_de_leitura.py). Se
   fossem dois trechos iguais em dois arquivos, um limiar novo passaria
   a valer num caminho e não no outro sem nada falhar: o produtor
   receberia alerta de solo seco no ciclo com foto e não no sem foto.

A LEITURA onde quem le se autentica por LOGIN de produtor é GET
/leituras, em app/api/routes/historico.py. Escrita e leitura do mesmo
recurso ficam separadas porque são dois fluxos de autenticação sem nada
em comum: aqui entra credencial de dispositivo (ADR 0009), lá entra JWT
de usuário com escopo por dono.
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
    """Monta a resposta no mesmo formato de GET /leituras.

    `tem_foto` é derivado, não coluna: é o que diferencia um ciclo de
    captura de um ciclo só de sensor.
    """
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
    # Mesma razão de POST /diagnostico: a autenticação precisa do
    # device_id, que vem no corpo, para conferir se aquela credencial
    # autoriza enviar COMO aquele dispositivo. Ver app/api/dispositivo_auth.py.
    await autenticar_dispositivo(sessao, dados.device_id, credencial)

    existente = await _buscar_por_idempotency_key(sessao, dados.idempotency_key)
    if existente is not None:
        logger.info(
            "Reenvio de leitura detectado (idempotency_key=%s): devolvendo a "
            "linha já gravada.",
            dados.idempotency_key,
        )
        return _para_saida(existente)

    # Requisição com as três medições nulas é ACEITA de propósito. Ela
    # significa "o ciclo rodou às 14:15 e nenhum sensor respondeu", que
    # é informação diferente de "não houve ciclo". Sem ela, a tela não
    # tem como distinguir sensor quebrado de Pi desligado, e exibiria a
    # leitura boa de duas horas atrás como se fosse a atual.
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
        await sessao.flush()  # garante leitura.id antes dos alertas

        for alerta in montar_alertas_ambientais(leitura):
            sessao.add(alerta)

        await sessao.commit()
    except IntegrityError:
        # Duas requisições com a mesma chave ao mesmo tempo: a que
        # perdeu devolve o resultado da que venceu, em vez de um 500.
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
