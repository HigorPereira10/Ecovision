"""
cloud/app/api/routes/historico.py

Endpoints de consulta histórica: leituras ambientais e diagnósticos
passados, para as telas de Histórico/Diagnóstico do frontend (app/).

Regra importante (Blueprint Seção 4.2, passo 5): o frontend NUNCA acessa
o Supabase diretamente. Este endpoint é quem busca os dados no Supabase
e devolve a resposta já pronta para exibição.

Rotas definidas como /leituras e /diagnosticos (nível raiz, sem prefixo
/historico), pela mesma convenção dos demais endpoints (/diagnostico,
/alertas): mantém a API com um único namespace de recursos, em vez de
misturar rotas com e sem prefixo.

Escopo aceito nesta rodada: como só existe 1 dispositivo físico no
projeto (mesma limitação já aceita em app/core/security.py para a API
Key), estes endpoints retornam os dados de TODOS os dispositivos, sem
filtrar por "dispositivos do produtor autenticado" (RBAC completo por
dono do dispositivo fica para quando existir mais de 1 dispositivo de
verdade e a tabela `dispositivos` for populada).

Relação com o resto do sistema:
- Consumido pelo frontend (app/) nas telas de Histórico e Diagnóstico.
- Depende de app/db/models.py (leituras_ambientais, diagnosticos) e
  app/core/security.py (obter_produtor_atual, exige login).
- `url_imagem` em DiagnosticoHistoricoOut vem de
  app/storage/supabase_storage.py (signed URL, bucket privado, decisão
  em infra/supabase/storage_policies.md).
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import obter_produtor_atual
from app.db.models import Diagnostico, LeituraAmbiental, RegistroImagem
from app.db.schemas import DiagnosticoHistoricoOut, LeituraOut
from app.db.session import get_session
from app.storage.supabase_storage import gerar_url_assinada_imagem

router = APIRouter()

# Limite defensivo: evita uma consulta sem filtro devolver a tabela
# inteira depois de meses de captura a cada 2h (ver ADR 0008 para o
# valor do intervalo padrão). Ajustável se a validação em campo (Sprint
# 9) mostrar que o histórico real precisa de mais.
_LIMITE_MAXIMO_ITENS = 1000


@router.get("/leituras", response_model=list[LeituraOut], dependencies=[Depends(obter_produtor_atual)])
async def listar_leituras(
    horas: int | None = Query(default=None, gt=0, description="Filtra leituras dos últimos N horas."),
    sessao: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Lista leituras ambientais, mais antiga primeiro (série temporal
    para gráfico). Sem `horas`, devolve as últimas _LIMITE_MAXIMO_ITENS
    leituras disponíveis.

    ATENÇÃO: os dois ramos abaixo NÃO podem ser escritos como uma única
    query com dois `.order_by()` encadeados (asc, depois desc): no
    SQLAlchemy isso ACRESCENTA cláusulas de ordenação em vez de
    substituir, e como é a mesma coluna, o segundo `.order_by()` é
    ignorado (a primeira cláusula já decide o empate). Isso já causou
    um bug real aqui: o `.reverse()` do ramo sem filtro invertia uma
    lista que já estava em ordem crescente, devolvendo a ordem errada."""
    base = select(LeituraAmbiental, RegistroImagem.device_id).join(
        RegistroImagem, LeituraAmbiental.registro_imagem_id == RegistroImagem.id
    )

    if horas is not None:
        desde = datetime.now(timezone.utc) - timedelta(hours=horas)
        consulta = base.where(LeituraAmbiental.criado_em >= desde).order_by(
            LeituraAmbiental.criado_em.asc()
        )
        linhas = (await sessao.execute(consulta)).all()
    else:
        # sem filtro: pega as N mais recentes (DESC + limit) e so depois
        # inverte para ordem cronologica, senao limitar uma consulta ASC
        # pegaria as N MAIS ANTIGAS em vez das N mais recentes.
        consulta = base.order_by(LeituraAmbiental.criado_em.desc()).limit(_LIMITE_MAXIMO_ITENS)
        linhas = list((await sessao.execute(consulta)).all())
        linhas.reverse()

    return [
        {
            "id": leitura.id,
            "device_id": device_id,
            "temperatura_c": leitura.temperatura_c,
            "umidade_ar_pct": leitura.umidade_ar_pct,
            "umidade_solo_pct": leitura.umidade_solo_pct,
            "criado_em": leitura.criado_em,
        }
        for leitura, device_id in linhas
    ]


@router.get(
    "/diagnosticos",
    response_model=list[DiagnosticoHistoricoOut],
    dependencies=[Depends(obter_produtor_atual)],
)
async def listar_diagnosticos(
    horas: int | None = Query(default=None, gt=0, description="Filtra diagnósticos dos últimos N horas."),
    sessao: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Lista diagnósticos, mais recente primeiro (feed de histórico)."""
    consulta = (
        select(Diagnostico, RegistroImagem.caminho_arquivo)
        .join(RegistroImagem, Diagnostico.registro_imagem_id == RegistroImagem.id)
        .order_by(Diagnostico.criado_em.desc())
        .limit(_LIMITE_MAXIMO_ITENS)
    )

    if horas is not None:
        desde = datetime.now(timezone.utc) - timedelta(hours=horas)
        consulta = consulta.where(Diagnostico.criado_em >= desde)

    resultado = await sessao.execute(consulta)
    linhas = resultado.all()

    # Uma chamada de rede ao Supabase por imagem (gera a signed URL sob
    # demanda, ver storage_policies.md: nao faz sentido persistir algo
    # que expira). Aceito para o volume de 1 dispositivo do protótipo;
    # se _LIMITE_MAXIMO_ITENS crescer muito, isso pode virar o gargalo
    # da rota antes do banco.
    return [
        {
            "id": diagnostico.id,
            "classe_prevista": diagnostico.classe_prevista,
            "confianca": diagnostico.confianca,
            "recomendacao": diagnostico.recomendacao,
            "caminho_arquivo": caminho_arquivo,
            "url_imagem": await gerar_url_assinada_imagem(caminho_arquivo),
            "criado_em": diagnostico.criado_em,
        }
        for diagnostico, caminho_arquivo in linhas
    ]
