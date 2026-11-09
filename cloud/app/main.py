"""
Ponto de entrada da API FastAPI, servida pelo Uvicorn com um único processo.

O modelo .tflite é carregado uma vez, na inicialização; sem o arquivo, a
API inicia mesmo assim e a inferência devolve resultado provisório.
GET /health permite ao monitoramento externo verificar o serviço e o banco.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import (
    alertas,
    auth,
    diagnostico,
    dispositivos,
    historico,
    leituras,
    usuarios,
)
from app.config import settings
from app.core.inference import carregar_modelo_tflite
from app.db.session import get_session

logger = logging.getLogger("ecovision.cloud.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Carrega o modelo .tflite em memória uma única vez."""
    app.state.modelo_tflite = carregar_modelo_tflite(settings.caminho_do_modelo)
    yield


app = FastAPI(title="EcoVision API", lifespan=lifespan)

# CORS liberado para a versão web do aplicativo. A autenticação usa o
# cabeçalho Authorization, nunca cookies, então outras origens não herdam
# a sessão do usuário.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health(
    request: Request,
    response: Response,
    sessao: AsyncSession = Depends(get_session),
) -> dict:
    """Verifica o serviço com uma consulta trivial ao banco.

    Responde 503 quando o banco não responde, para que monitores externos,
    que observam o código de status, detectem a falha. Informa também se o
    modelo está carregado; a ausência do modelo não gera 503, porque a API
    continua recebendo e gravando dados, apenas sem classificação."""
    corpo = {
        "status": "ok",
        "banco": "ok",
        # Preenchido na inicialização; None quando o modelo não foi carregado.
        "modelo": "carregado" if request.app.state.modelo_tflite is not None else "ausente",
    }

    try:
        await sessao.execute(text("SELECT 1"))
    except Exception:
        logger.error("Falha no /health ao consultar o banco.", exc_info=True)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {**corpo, "status": "erro", "banco": "indisponivel"}

    return corpo


app.include_router(diagnostico.router)
app.include_router(auth.router)
app.include_router(historico.router)
app.include_router(alertas.router)
app.include_router(usuarios.router)
app.include_router(dispositivos.router)
# POST /leituras (dispositivo). GET /leituras fica em historico.router,
# com autenticação de usuário.
app.include_router(leituras.router)
