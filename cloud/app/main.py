"""
cloud/app/main.py

Ponto de entrada da API FastAPI, servida via Uvicorn com 1 worker
(Tech Stack Blueprint v3.0, Fase 4 / Sumário Executivo).

Responsabilidades quando implementado:
- Instanciar a aplicação FastAPI.
- Registrar os routers de app/api/routes/ (diagnostico, auth, dispositivos,
  alertas, historico).
- Carregar o modelo .tflite em memória UMA VEZ na inicialização (startup
  event), via app/core/inference.py, nunca recarregar por requisição.
- Configurar CORS para o(s) frontend(s) consumidores (app/dashboard).
- Não deve abrir nenhum arquivo em disco (regra 2, Blueprint Seção 4.4).

Relação com o resto do sistema:
- É o processo que o Railway executa (ver infra/railway/).
- Consome app/config.py para variáveis de ambiente (API Key, credenciais
  Supabase, segredo JWT).
- É o único ponto de contato do Raspberry Pi (edge/) e do frontend (app/)
  com o backend.
"""

# from fastapi import FastAPI
# from app.api.routes import diagnostico, auth, dispositivos, alertas, historico
# from app.core.inference import carregar_modelo_tflite

# app = FastAPI(title="EcoVision API")

# @app.on_event("startup")
# async def startup() -> None:
#     """Carrega o modelo .tflite em memória uma única vez."""
#     raise NotImplementedError

# TODO: app.include_router(diagnostico.router)
# TODO: app.include_router(auth.router)
# TODO: app.include_router(dispositivos.router)
# TODO: app.include_router(alertas.router)
# TODO: app.include_router(historico.router)
