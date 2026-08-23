"""
cloud/app/db/schemas.py

Schemas Pydantic usados para validação de entrada/saída dos endpoints
FastAPI (app/api/routes/*.py), separados dos modelos ORM (app/db/models.py)
por boa prática (não expor a estrutura de banco diretamente na API).

Nesta rodada só a resposta de POST /diagnostico é implementada. Os
schemas de autenticação (login, tokens) ficam para quando o login do
dashboard for implementado.

Relação com o resto do sistema:
- Usado por app/api/routes/diagnostico.py para tipar a resposta.
"""

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
