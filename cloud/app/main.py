"""
cloud/app/main.py

Ponto de entrada da API FastAPI, servida via Uvicorn com 1 worker
(Tech Stack Blueprint v3.0, Fase 4 / Sumário Executivo).

Routers registrados: diagnostico.py (caminho do dispositivo), auth.py,
historico.py, alertas.py, usuarios.py e dispositivos.py (caminho do
dashboard). RBAC por dono de dispositivo (mais de 1 dispositivo físico
de verdade) ainda fica para depois, ver cloud/README.md.

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

from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import alertas, auth, diagnostico, dispositivos, historico, usuarios
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

# CORS: necessário para a versão web do Expo (app/) rodando em outra
# origem (localhost:PORTA em dev, um domínio próprio se publicada)
# conseguir chamar a API pelo navegador. O app nativo (Expo Go/iOS/
# Android) não é afetado por CORS, isso é uma restrição só de browser.
#
# allow_origins=["*"] é aceitável aqui porque a autenticação é via
# header Authorization (Bearer <JWT>), nunca cookie: diferente de auth
# por cookie, um header custom só é enviado se o código JS do próprio
# app decidir mandar, então um site malicioso em outra aba não consegue
# "andar de carona" na sessão do produtor só por ele estar logado.
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
    """Endpoint leve para o UptimeRobot: sem autenticação, sem lógica
    de negócio. Faz um SELECT trivial para confirmar que a conexão com
    o banco (Supabase) está de pé, não só que o processo FastAPI está
    no ar.

    ATENÇÃO, BUG JÁ CORRIGIDO AQUI: a primeira versão devolvia sempre
    HTTP 200, mesmo com o banco fora do ar (só o corpo JSON mudava). Um
    monitor externo como o UptimeRobot olha o status code, não o corpo
    da resposta, então nunca detectaria a falha daquele jeito. Por isso
    o código abaixo devolve 503 quando o banco não responde: nunca
    remover essa parte achando que é redundante.

    POR QUE O ESTADO DO MODELO APARECE AQUI: sem modelo carregado, a
    inferência degrada para "indisponivel" em TODA captura, e nada no
    sistema denuncia isso de fora. Já aconteceu uma vez, por caminho de
    arquivo resolvido a partir do diretório errado, e o sintoma era
    apenas diagnóstico vazio no app, indistinguível de dispositivo sem
    capturar. Com este campo, conferir é uma requisição, de qualquer
    lugar, inclusive do celular dentro da estufa.

    MODELO AUSENTE NÃO DEVOLVE 503, de propósito. A API continua
    recebendo e gravando captura, leitura e alerta ambiental: o serviço
    está de pé, só a classificação está degradada. Marcar isso como
    indisponível faria o UptimeRobot alarmar por algo que não é queda, e
    alarme que não corresponde a queda é alarme que o grupo aprende a
    ignorar."""
    corpo = {
        "status": "ok",
        "banco": "ok",
        # app.state.modelo_tflite é preenchido uma única vez no lifespan;
        # vem None quando o .tflite não foi encontrado ou não pôde ser
        # carregado (ver app/core/inference.py).
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
