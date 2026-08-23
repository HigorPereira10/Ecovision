"""
cloud/app/config.py

Configuração centralizada via variáveis de ambiente (12-factor app),
carregadas no Railway a partir das variáveis definidas no serviço
(nunca hardcoded, nunca em arquivo .env versionado,
ver infra/env/cloud.env.example para o template das chaves esperadas).

Os campos JWT_* já existem aqui (com default) mesmo sem uso nesta
rodada — o login do dashboard fica para quando app/ for implementado
de verdade, mas assim o .env.example não precisa mudar de novo depois.

Relação com o resto do sistema:
- Consumido por app/main.py, app/core/security.py, app/core/inference.py,
  app/db/session.py e app/storage/supabase_storage.py.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação, populadas a partir de variáveis de ambiente."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Supabase ---
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_STORAGE_BUCKET: str = "ecovision-imagens"
    DATABASE_URL: str

    # --- Autenticação do dispositivo IoT (API Key estática) ---
    DEVICE_API_KEY: str

    # --- Autenticação do dashboard (JWT) — não usada nesta rodada ---
    JWT_SECRET_KEY: str = "nao-usado-nesta-rodada"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # --- Modelo ---
    TFLITE_MODEL_PATH: str = "ml/models/modelo.tflite"


@lru_cache
def get_settings() -> Settings:
    """Cacheado para não reler variáveis de ambiente a cada requisição."""
    return Settings()


settings = get_settings()
