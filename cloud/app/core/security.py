"""
cloud/app/core/security.py

Implementa as DUAS mecânicas de autenticação decididas no Blueprint v3.0,
Seção 4.3 (ver docs/decisions/0003-autenticacao-dual.md): mecanismos
diferentes para pontas diferentes, deliberadamente.

Nesta rodada só a ponta do dispositivo IoT está implementada:

1. Dispositivo IoT (Raspberry Pi -> API): API Key estática, comparada
   contra o valor definido na variável de ambiente DEVICE_API_KEY,
   enviada CRUA no header Authorization, sem prefixo "Bearer" (é
   exatamente o que edge/src/upload/uploader.py envia). A comparação é
   feita em tempo constante (secrets.compare_digest), pra não vazar a
   chave por um ataque de timing.

   ALERTA DE SEGURANÇA, LIMITAÇÃO CONHECIDA E ACEITA (ADR 0003): é uma
   chave ÚNICA e GLOBAL, não uma chave por dispositivo. Isso significa
   que o campo `device_id` do formulário em /diagnostico NÃO é
   validado contra nenhum cadastro: qualquer requisição com a chave
   certa pode se identificar como QUALQUER device_id. Isso é aceitável
   enquanto existir só 1 dispositivo físico de verdade (o motivo
   original do ADR 0003 é que um JWT rotativo para 1 único device seria
   complexidade desnecessária). Se o projeto crescer para múltiplos
   dispositivos físicos, isso PRECISA virar uma chave por dispositivo
   (a tabela `dispositivos` já existe no schema, mas ainda sem uso)
   antes de qualquer implantação com mais de um Raspberry Pi em campo.

2. Dashboard (login do produtor): JWT + refresh token + bcrypt. Fica
   para quando o login do produtor (app/) for implementado de verdade.

Relação com o resto do sistema:
- validar_api_key_dispositivo() é usada como dependency no endpoint
  /diagnostico (app/api/routes/diagnostico.py).
"""

import secrets

from fastapi import Header, HTTPException, status

from app.config import settings


def validar_api_key_dispositivo(authorization: str | None = Header(default=None)) -> None:
    """Dependency FastAPI: valida o header Authorization contra a API
    Key estática do dispositivo. Levanta 401 se ausente ou incorreta."""
    if authorization is None or not secrets.compare_digest(authorization, settings.DEVICE_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key do dispositivo ausente ou inválida.",
        )


# --- Dashboard (JWT + bcrypt): TODO, rodada futura, quando app/ for implementado ---

# def criar_access_token(dados: dict) -> str:
#     """Gera um JWT de acesso de curta duração (24h)."""
#     raise NotImplementedError

# def criar_refresh_token(dados: dict) -> str:
#     """Gera um refresh token de longa duração (30 dias)."""
#     raise NotImplementedError

# def verificar_senha(senha_texto_puro: str, hash_bcrypt: str) -> bool:
#     """Verifica a senha do produtor contra o hash bcrypt armazenado."""
#     raise NotImplementedError
