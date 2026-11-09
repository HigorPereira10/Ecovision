"""
Configuração da API por variáveis de ambiente (modelo em infra/env/cloud.env.example).

JWT_SECRET_KEY tem um valor padrão apenas para desenvolvimento e testes;
em produção deve ser definido no ambiente, por exemplo com
`python -c "import secrets; print(secrets.token_urlsafe(48))"`.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Raiz do repositório, usada para resolver caminhos relativos de arquivo.
_RAIZ_DO_REPO = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Configurações da aplicação, populadas a partir de variáveis de ambiente."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Supabase ---
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_STORAGE_BUCKET: str = "ecovision-imagens"
    DATABASE_URL: str

    # --- Dispositivos ---
    # Chave global anterior, aceita apenas por compatibilidade em
    # app/api/dispositivo_auth.py. A credencial válida é a de cada
    # dispositivo, guardada como hash em dispositivos.chave_hash.
    DEVICE_API_KEY: str

    # --- Autenticação do aplicativo (JWT) ---
    # O padrão (32+ bytes) serve só para desenvolvimento e testes.
    JWT_SECRET_KEY: str = "chave-de-desenvolvimento-local-nao-usar-em-producao"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # --- E-mail (confirmação de cadastro e recuperação de senha) ---
    # Opcional: sem configuração, a API inicia e cria contas já
    # verificadas, com aviso no log.
    #
    # Produção: API HTTP do Brevo, já que o Railway bloqueia as portas de
    # SMTP nos planos Free, Trial e Hobby.
    BREVO_API_KEY: str = ""

    # Desenvolvimento local: SMTP (no Gmail, use uma senha de app).
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USUARIO: str = ""
    SMTP_SENHA: str = ""

    # Remetente usado pelos dois caminhos; no Brevo, precisa ser um
    # endereço verificado na conta.
    EMAIL_REMETENTE: str = ""

    @property
    def remetente(self) -> str:
        return self.EMAIL_REMETENTE or self.SMTP_USUARIO

    @property
    def smtp_configurado(self) -> bool:
        return bool(self.SMTP_HOST and self.SMTP_USUARIO and self.SMTP_SENHA)

    @property
    def email_configurado(self) -> bool:
        """True quando há algum caminho de envio de e-mail configurado."""
        return bool(self.BREVO_API_KEY and self.remetente) or self.smtp_configurado

    # --- Modelo ---
    # Caminho relativo é resolvido a partir da raiz do repositório, e não
    # do diretório de trabalho (a API inicia dentro de cloud/).
    TFLITE_MODEL_PATH: str = "ml/models/modelo_dominio.tflite"

    # Diagnóstico por janelas (app/core/janelas.py). Com False, classifica
    # o quadro inteiro reduzido a 224 × 224, o que deixa a folha pequena
    # demais para o modelo e degrada a acurácia.
    DIAGNOSTICO_POR_JANELA: bool = True

    @property
    def caminho_do_modelo(self) -> str:
        """Caminho absoluto do .tflite; um caminho já absoluto é devolvido
        como está."""
        caminho = Path(self.TFLITE_MODEL_PATH)
        if caminho.is_absolute():
            return str(caminho)
        return str(_RAIZ_DO_REPO / caminho)


@lru_cache
def get_settings() -> Settings:
    """Cacheado para não reler variáveis de ambiente a cada requisição."""
    return Settings()


settings = get_settings()
