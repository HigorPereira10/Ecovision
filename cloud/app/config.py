"""
cloud/app/config.py

Configuração centralizada via variáveis de ambiente (12-factor app),
carregadas no Railway a partir das variáveis definidas no serviço
(nunca hardcoded, nunca em arquivo .env versionado, 
ver infra/env/cloud.env.example para o template das chaves esperadas).

Deve conter, quando implementado:
- SUPABASE_URL, SUPABASE_KEY (ou SUPABASE_SERVICE_ROLE_KEY para o backend)
- SUPABASE_STORAGE_BUCKET (nome sugerido no Blueprint: "ecovision-imagens")
- DATABASE_URL (string de conexão async do Postgres do Supabase)
- DEVICE_API_KEY (API Key estática validada nas requisições do Pi)
- JWT_SECRET_KEY, JWT_ALGORITHM
- JWT_ACCESS_TOKEN_EXPIRE_MINUTES (24h, Blueprint Seção 4.3)
- JWT_REFRESH_TOKEN_EXPIRE_DAYS (30 dias, Blueprint Seção 4.3)
- TFLITE_MODEL_PATH (caminho do .tflite versionado no repositório, não em volume)

Relação com o resto do sistema:
- Consumido por app/main.py, app/core/security.py, app/core/inference.py,
  app/db/session.py e app/storage/supabase_storage.py.
"""

# from pydantic_settings import BaseSettings

# class Settings(BaseSettings):
#     """Configurações da aplicação, populadas a partir de variáveis de ambiente."""
#     raise NotImplementedError

# settings = Settings()
