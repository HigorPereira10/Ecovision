"""
cloud/app/db/schemas.py

Schemas Pydantic usados para validação de entrada/saída dos endpoints
FastAPI (app/api/routes/*.py), separados dos modelos ORM (app/db/models.py)
por boa prática (não expor a estrutura de banco diretamente na API).

Devem espelhar, em versão "de API", as mesmas entidades de app/db/models.py:
RegistroImagem, LeituraAmbiental, Diagnostico, Alerta, Usuario, Dispositivo,
além dos schemas específicos de autenticação (login, tokens).

Relação com o resto do sistema:
- Usado pelos routers para tipar request/response.
- Depende indiretamente do schema fechado em app/db/models.py.
"""

# from pydantic import BaseModel

# class DiagnosticoOut(BaseModel):
#     """TODO: espelha Diagnostico, incluindo a URL da imagem para exibição no frontend."""
#     raise NotImplementedError

# class LoginRequest(BaseModel):
#     """TODO: email + senha do produtor."""
#     raise NotImplementedError

# class TokenResponse(BaseModel):
#     """TODO: access_token, refresh_token, token_type."""
#     raise NotImplementedError
