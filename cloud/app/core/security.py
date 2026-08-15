"""
cloud/app/core/security.py

Implementa as DUAS mecânicas de autenticação decididas no Blueprint v3.0,
Seção 4.3: mecanismos diferentes para pontas diferentes, deliberadamente:

1. Dispositivo IoT (Raspberry Pi -> API): API Key estática, comparada
   contra o valor definido na variável de ambiente DEVICE_API_KEY,
   enviada no header Authorization. Escolhida por ser suficiente para
   autenticar 1 único dispositivo sem o over-engineering de JWT rotativo
   embarcado.

2. Dashboard (login do produtor): JWT de curta duração (24h) + refresh
   token (30 dias) + hash de senha com bcrypt. Inclui o papel do usuário
   (Produtor/Administrador) no payload do token para suportar RBAC.

Relação com o resto do sistema:
- validar_api_key_dispositivo() é usada como dependency no endpoint
  /diagnostico (app/api/routes/diagnostico.py).
- As funções de JWT/bcrypt são usadas em app/api/routes/auth.py e como
  dependency nos demais endpoints autenticados por usuário.
"""

# from app.config import settings

# def validar_api_key_dispositivo(api_key: str) -> bool:
#     """Compara a API Key recebida do Pi com DEVICE_API_KEY."""
#     raise NotImplementedError

# def criar_access_token(dados: dict) -> str:
#     """Gera um JWT de acesso de curta duração (24h)."""
#     raise NotImplementedError

# def criar_refresh_token(dados: dict) -> str:
#     """Gera um refresh token de longa duração (30 dias)."""
#     raise NotImplementedError

# def verificar_senha(senha_texto_puro: str, hash_bcrypt: str) -> bool:
#     """Verifica a senha do produtor contra o hash bcrypt armazenado."""
#     raise NotImplementedError
