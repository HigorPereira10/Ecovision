"""
cloud/app/api/routes/auth.py

Endpoints de autenticação do PRODUTOR no dashboard/app (não confundir com
a API Key do dispositivo IoT, ver app/core/security.py para a distinção).

Conforme Blueprint v3.0 Seção 4.3:
- POST /auth/login: valida email/senha (hash bcrypt) e emite um par de
  tokens: JWT de acesso (24h) + refresh token (30 dias).
- POST /auth/refresh: troca um refresh token válido por um novo JWT de acesso.
- (Opcional/futuro) POST /auth/logout: invalidação de refresh token.

RBAC (Blueprint Seção 4.3): dois papéis, Produtor (leitura dos próprios
dispositivos, escrita limitada) e Administrador (CRUD completo). O token
emitido deve carregar o papel do usuário para os demais endpoints
aplicarem o controle de acesso.

Relação com o resto do sistema:
- Consumido pelo frontend (app/) para autenticar o produtor.
- Depende de app/core/security.py (geração/validação de JWT, verificação
  de hash bcrypt) e app/db/models.py (tabela de usuários).
"""

# from fastapi import APIRouter

# router = APIRouter()

# @router.post("/auth/login")
# async def login(...):
#     """Autentica o produtor e retorna JWT de acesso + refresh token."""
#     raise NotImplementedError

# @router.post("/auth/refresh")
# async def refresh_token(...):
#     """Troca um refresh token válido por um novo JWT de acesso."""
#     raise NotImplementedError
