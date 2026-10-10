"""
cloud/app/config.py

Configuração centralizada via variáveis de ambiente (12-factor app),
carregadas no Railway a partir das variáveis definidas no serviço
(nunca hardcoded, nunca em arquivo .env versionado,
ver infra/env/cloud.env.example para o template das chaves esperadas).

Os campos JWT_* são usados por app/core/security.py (login do
dashboard, ADR 0003). JWT_SECRET_KEY tem um valor padrão só para dev
local/testes: em produção (Railway), DEVE ser sobrescrito por uma
variável de ambiente de verdade (ex.: `python -c "import secrets;
print(secrets.token_urlsafe(48))"`), nunca o valor abaixo.

Relação com o resto do sistema:
- Consumido por app/main.py, app/core/security.py, app/core/inference.py,
  app/db/session.py e app/storage/supabase_storage.py.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Raiz do repositorio: cloud/app/config.py -> cloud/app -> cloud -> raiz.
# Serve de ancora para os caminhos relativos de arquivo, abaixo.
_RAIZ_DO_REPO = Path(__file__).resolve().parents[2]


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

    # --- Autenticação do dashboard (JWT) ---
    # Valor padrão só serve para dev local/testes (32+ bytes para evitar
    # o InsecureKeyLengthWarning do PyJWT); produção sobrescreve via env var.
    JWT_SECRET_KEY: str = "chave-de-desenvolvimento-local-nao-usar-em-producao"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # --- Envio de email (confirmacao de cadastro e recuperacao de senha) ---
    #
    # Todos opcionais de proposito. Sem SMTP configurado a API sobe do
    # mesmo jeito e o cadastro passa a criar contas JA VERIFICADAS, com
    # aviso no log. E o mesmo principio do modelo de IA: uma dependencia
    # externa ausente nao pode derrubar o sistema, e muito menos deixar
    # o produtor preso numa conta que ele nunca consegue confirmar.
    #
    # Para Gmail: host smtp.gmail.com, porta 587, usuario o proprio
    # email e senha uma "senha de app" (exige verificacao em duas etapas
    # ativada na conta Google). A senha normal do Gmail NAO funciona.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USUARIO: str = ""
    SMTP_SENHA: str = ""
    SMTP_REMETENTE: str = ""

    @property
    def email_configurado(self) -> bool:
        """True quando da para enviar email de verdade."""
        return bool(self.SMTP_HOST and self.SMTP_USUARIO and self.SMTP_SENHA)

    # --- Modelo ---
    # Caminho do .tflite. Quando relativo, e resolvido a partir da RAIZ
    # DO REPOSITORIO (ver caminho_do_modelo), nao do diretorio de onde o
    # processo foi iniciado.
    #
    # Isso nao e preciosismo: a API sobe de dentro de cloud/, entao um
    # caminho relativo resolvido contra o diretorio de trabalho virava
    # cloud/ml/models/modelo.tflite, que nao existe. O carregador nao
    # derruba a API quando o arquivo falta (de proposito), entao o
    # resultado era a API subir sem modelo e devolver placeholder EM
    # SILENCIO, dando a impressao de que a inferencia estava ativa.
    TFLITE_MODEL_PATH: str = "ml/models/modelo.tflite"

    @property
    def caminho_do_modelo(self) -> str:
        """Caminho absoluto do .tflite, independente de onde o processo
        foi iniciado. Um caminho ja absoluto e devolvido como esta, para
        o deploy poder apontar para fora do repositorio se precisar."""
        caminho = Path(self.TFLITE_MODEL_PATH)
        if caminho.is_absolute():
            return str(caminho)
        return str(_RAIZ_DO_REPO / caminho)


@lru_cache
def get_settings() -> Settings:
    """Cacheado para não reler variáveis de ambiente a cada requisição."""
    return Settings()


settings = get_settings()
