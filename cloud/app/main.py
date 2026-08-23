"""
cloud/app/main.py

Ponto de entrada da API FastAPI, servida via Uvicorn com 1 worker
(Tech Stack Blueprint v3.0, Fase 4 / Sumário Executivo).

Nesta rodada só o router de diagnostico é registrado (caminho do
dispositivo) — auth/dispositivos/alertas/historico ficam para quando
app/ (dashboard) for implementado de verdade, ver cloud/README.md.

Responsabilidades:
- Instanciar a aplicação FastAPI.
- Registrar o router de app/api/routes/diagnostico.py.
- Carregar o modelo .tflite em memória UMA VEZ na inicialização
  (lifespan), via app/core/inference.py — nunca recarregar por
  requisição. Se o modelo não existir ainda, a API sobe do mesmo jeito
  (ver app/core/inference.py, resultado placeholder).
- Não abre nenhum arquivo em disco fora do carregamento do modelo
  (regra 2, Blueprint Seção 4.4).
- Expor GET /health: endpoint leve (não autenticado, não abre o corpo
  da imagem/lógica de negócio) para o UptimeRobot pingar periodicamente
  e manter o Supabase (pausa após 7 dias sem uso) e o Railway ativos —
  ver infra/monitoring/uptimerobot.md.

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

from app.api.routes import diagnostico
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
    """Endpoint leve para o UptimeRobot — sem autenticação, sem lógica
    de negócio. Faz um SELECT trivial pra confirmar que a conexão com o
    banco (Supabase) está de pé, não só que o processo FastAPI está no ar.

    BUG CORRIGIDO: a primeira versão devolvia sempre HTTP 200, mesmo com
    o banco fora do ar — só o corpo JSON mudava. Um monitor externo (ex.:
    UptimeRobot) que olha o status code, não o corpo, nunca detectaria a
    falha. Agora devolve 503 quando o banco não responde."""
    try:
        await sessao.execute(text("SELECT 1"))
    except Exception:
        logger.error("Falha no /health ao consultar o banco.", exc_info=True)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "erro", "banco": "indisponivel"}
    return {"status": "ok", "banco": "ok"}


app.include_router(diagnostico.router)
# TODO: app.include_router(auth.router) — quando o login do dashboard existir
# TODO: app.include_router(dispositivos.router)
# TODO: app.include_router(alertas.router)
# TODO: app.include_router(historico.router)
