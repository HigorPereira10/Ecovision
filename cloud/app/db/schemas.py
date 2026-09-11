"""
cloud/app/db/schemas.py

Schemas Pydantic usados para validação de entrada/saída dos endpoints
FastAPI (app/api/routes/*.py), separados dos modelos ORM (app/db/models.py)
por boa prática (não expor a estrutura de banco diretamente na API).

Relação com o resto do sistema:
- DiagnosticoOut: usado por app/api/routes/diagnostico.py.
- LoginRequest/TokenResponse/RefreshRequest: usados por
  app/api/routes/auth.py.
- LeituraOut: usado por app/api/routes/leituras.py.
- DiagnosticoHistoricoOut: usado por app/api/routes/diagnosticos.py.
- AlertaOut: usado por app/api/routes/alertas.py.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DiagnosticoOut(BaseModel):
    """Resposta de POST /diagnostico. Espelha o mock
    app/src/mocks/diagnosticos.json do dashboard (campo "resultado" lá
    corresponde a classe_prevista aqui)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    classe_prevista: str
    confianca: float
    recomendacao: str | None


class LoginRequest(BaseModel):
    """Corpo de POST /auth/login."""

    email: str
    senha: str


class RefreshRequest(BaseModel):
    """Corpo de POST /auth/refresh."""

    refresh_token: str


class TokenResponse(BaseModel):
    """Resposta de POST /auth/login e POST /auth/refresh."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class LeituraOut(BaseModel):
    """Item de GET /leituras. Nomes de campo mantidos como no schema
    real (temperatura_c, umidade_ar_pct, umidade_solo_pct), diferente
    do mock antigo do app/ (temperatura, umidade_ar, umidade_solo):
    ver revisão da branch preparacao-api-real, a Amanda ajusta o
    consumo desses nomes no lado dela quando integrar de verdade."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    temperatura_c: float | None
    umidade_ar_pct: float | None
    umidade_solo_pct: float | None
    criado_em: datetime


class DiagnosticoHistoricoOut(BaseModel):
    """Item de GET /diagnosticos. `caminho_arquivo` é o caminho dentro
    do bucket do Supabase Storage (não uma URL, útil só para depuração).
    `url_imagem` é a signed URL pronta para exibir na tela (ver
    app/storage/supabase_storage.py e
    infra/supabase/storage_policies.md), válida por um tempo limitado;
    vem None se a geração da URL falhar (a lista não deve quebrar por
    causa de uma imagem)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    classe_prevista: str
    confianca: float
    recomendacao: str | None
    caminho_arquivo: str
    url_imagem: str | None = None
    criado_em: datetime


class AlertaOut(BaseModel):
    """Item de GET /alertas. `id` é None e `sintetico` é True para o
    alerta de dispositivo inativo (ADR 0008), que não corresponde a
    nenhuma linha real da tabela `alertas`: o frontend não deve tentar
    dar PATCH .../lido num item com sintetico=True."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None
    titulo: str
    descricao: str
    severidade: str
    lido: bool = False
    criado_em: datetime
    sintetico: bool = False
