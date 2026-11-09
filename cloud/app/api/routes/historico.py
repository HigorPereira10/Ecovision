"""
Consultas históricas: GET /leituras e GET /diagnosticos.

Devolvem apenas os dados dos dispositivos vinculados ao usuário
(app/api/escopo.py); capturas de dispositivos sem dono não aparecem para
ninguém. As imagens são entregues por URLs assinadas
(app/storage/supabase_storage.py). A escrita de leituras (POST /leituras)
fica em app/api/routes/leituras.py, com autenticação de dispositivo.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.escopo import device_ids_visiveis
from app.core.security import obter_produtor_atual
from app.db.models import Diagnostico, LeituraAmbiental, RegistroImagem
from app.db.schemas import DiagnosticoHistoricoOut, LeituraOut
from app.db.session import get_session
from app.storage.supabase_storage import gerar_urls_assinadas_imagens

router = APIRouter()

# Limite de itens por consulta, para que uma consulta sem filtro não
# devolva a tabela inteira.
_LIMITE_MAXIMO_ITENS = 1000


@router.get("/leituras", response_model=list[LeituraOut])
async def listar_leituras(
    horas: int | None = Query(default=None, gt=0, description="Filtra leituras dos últimos N horas."),
    produtor: dict = Depends(obter_produtor_atual),
    sessao: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Lista leituras ambientais em ordem cronológica (série para gráfico).
    Sem `horas`, devolve as últimas _LIMITE_MAXIMO_ITENS leituras.

    Os dois ramos usam consultas separadas: encadear dois .order_by() no
    SQLAlchemy acrescenta cláusulas em vez de substituir."""
    # Sem JOIN com registros_imagem: device_id é coluna da leitura, e o
    # JOIN descartaria as leituras sem foto.
    base = select(LeituraAmbiental)

    device_ids = await device_ids_visiveis(sessao, produtor)
    if device_ids is not None:
        base = base.where(LeituraAmbiental.device_id.in_(device_ids))

    if horas is not None:
        desde = datetime.now(timezone.utc) - timedelta(hours=horas)
        consulta = base.where(LeituraAmbiental.criado_em >= desde).order_by(
            LeituraAmbiental.criado_em.asc()
        )
        leituras = list((await sessao.execute(consulta)).scalars().all())
    else:
        # Sem filtro: busca as N mais recentes (DESC + limit) e inverte
        # para a ordem cronológica.
        consulta = base.order_by(LeituraAmbiental.criado_em.desc()).limit(_LIMITE_MAXIMO_ITENS)
        leituras = list((await sessao.execute(consulta)).scalars().all())
        leituras.reverse()

    return [
        {
            "id": leitura.id,
            "device_id": leitura.device_id,
            "temperatura_c": leitura.temperatura_c,
            "umidade_ar_pct": leitura.umidade_ar_pct,
            "umidade_solo_pct": leitura.umidade_solo_pct,
            "tem_foto": leitura.registro_imagem_id is not None,
            "criado_em": leitura.criado_em,
        }
        for leitura in leituras
    ]


@router.get(
    "/diagnosticos",
    response_model=list[DiagnosticoHistoricoOut],
)
async def listar_diagnosticos(
    horas: int | None = Query(default=None, gt=0, description="Filtra diagnósticos dos últimos N horas."),
    limite: int = Query(
        default=_LIMITE_MAXIMO_ITENS,
        gt=0,
        le=_LIMITE_MAXIMO_ITENS,
        description="Quantos diagnósticos devolver, do mais recente para o mais antigo.",
    ),
    produtor: dict = Depends(obter_produtor_atual),
    sessao: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Lista diagnósticos, do mais recente ao mais antigo.

    `limite` existe porque cada item exige uma URL assinada: a tela de
    Diagnóstico pede poucos itens, e a de Histórico, a janela inteira.
    """
    consulta = (
        select(Diagnostico, RegistroImagem.caminho_arquivo, RegistroImagem.device_id)
        .join(RegistroImagem, Diagnostico.registro_imagem_id == RegistroImagem.id)
        .order_by(Diagnostico.criado_em.desc())
        .limit(limite)
    )

    device_ids = await device_ids_visiveis(sessao, produtor)
    if device_ids is not None:
        consulta = consulta.where(RegistroImagem.device_id.in_(device_ids))

    if horas is not None:
        desde = datetime.now(timezone.utc) - timedelta(hours=horas)
        consulta = consulta.where(Diagnostico.criado_em >= desde)

    resultado = await sessao.execute(consulta)
    linhas = resultado.all()

    # As URLs assinadas são geradas em lote, em uma única chamada ao Supabase.
    urls = await gerar_urls_assinadas_imagens(
        [caminho_arquivo for _, caminho_arquivo, _ in linhas]
    )

    return [
        {
            "id": diagnostico.id,
            "device_id": device_id,
            "classe_prevista": diagnostico.classe_prevista,
            "confianca": diagnostico.confianca,
            "recomendacao": diagnostico.recomendacao,
            "caminho_arquivo": caminho_arquivo,
            "url_imagem": urls.get(caminho_arquivo),
            "criado_em": diagnostico.criado_em,
        }
        for diagnostico, caminho_arquivo, device_id in linhas
    ]
