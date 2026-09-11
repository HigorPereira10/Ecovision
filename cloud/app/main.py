"""
cloud/app/main.py

Ponto de entrada da API FastAPI, servida via Uvicorn com 1 worker
(Tech Stack Blueprint v3.0, Fase 4 / Sumário Executivo).

Routers registrados: diagnostico.py (caminho do dispositivo), auth.py,
historico.py e alertas.py (caminho do dashboard). O router de
dispositivos.py (CRUD administrativo) ainda fica para quando existir
RBAC por dono de dispositivo (mais de 1 dispositivo físico), ver
cloud/README.md.

Responsabilidades:
- Instanciar a aplicação FastAPI.
- Registrar os routers de app/api/routes/*.py.
- Carregar o modelo .tflite em memória UMA VEZ na inicialização
  (lifespan), via app/core/inference.py. NUNCA recarregar o modelo a
  cada requisição, isso destruiria a performance. Se o modelo ainda não
  existir, a API sobe do mesmo jeito (ver app/core/inference.py,
  resultado placeholder).
- Não abre nenhum arquivo em disco fora do carregamento do modelo
  (regra 2, Blueprint Seção 4.4).
- Expor GET /health: endpoint leve (não autenticado, não mexe com a
  imagem nem com lógica de negócio) para o UptimeRobot pingar
  periodicamente e manter o Supabase (que pausa após 7 dias sem uso) e
  o Railway ativos. Ver infra/monitoring/uptimerobot.md.

Relação com o resto do sistema:
- É o processo que o Railway executa (ver infra/railway/).
- Consome app/config.py para variáveis de ambiente (API Key, credenciais
  Supabase, segredo JWT).
- É o único ponto de contato do Raspberry Pi (edge/) e do frontend (app/)
  com o backend.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import alertas, auth, diagnostico, historico
from app.config import settings
from app.core.inference import carregar_modelo_tflite
from app.db.session import get_session

logger = logging.getLogger("ecovision.cloud.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Carrega o modelo .tflite em memória uma única vez."""
    app.state.modelo_tflite = carregar_modelo_tflite(settings.TFLITE_MODEL_PATH)
    yield


app = FastAPI(title="EcoVision API", lifespan=lifespan)


@app.get("/health")
async def health(response: Response, sessao: AsyncSession = Depends(get_session)) -> dict:
    """Endpoint leve para o UptimeRobot: sem autenticação, sem lógica
    de negócio. Faz um SELECT trivial para confirmar que a conexão com
    o banco (Supabase) está de pé, não só que o processo FastAPI está
    no ar.

    ATENÇÃO, BUG JÁ CORRIGIDO AQUI: a primeira versão devolvia sempre
    HTTP 200, mesmo com o banco fora do ar (só o corpo JSON mudava). Um
    monitor externo como o UptimeRobot olha o status code, não o corpo
    da resposta, então nunca detectaria a falha daquele jeito. Por isso
    o código abaixo devolve 503 quando o banco não responde: nunca
    remover essa parte achando que é redundante."""
    try:
        await sessao.execute(text("SELECT 1"))
    except Exception:
        logger.error("Falha no /health ao consultar o banco.", exc_info=True)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "erro", "banco": "indisponivel"}
    return {"status": "ok", "banco": "ok"}


app.include_router(diagnostico.router)
app.include_router(auth.router)
app.include_router(historico.router)
app.include_router(alertas.router)
# TODO: app.include_router(dispositivos.router), quando RBAC por
# dispositivo/dono for necessario (mais de 1 dispositivo fisico).
