"""
cloud/app/core/security.py

Implementa as DUAS mecânicas de autenticação decididas no Blueprint v3.0,
Seção 4.3 (ver docs/decisions/0003-autenticacao-dual.md): mecanismos
diferentes para pontas diferentes, deliberadamente.

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

2. Dashboard (login do produtor): JWT de acesso (24h) + refresh token
   (30 dias), senha com hash bcrypt. Payload do JWT carrega `sub`
   (id do usuário, como string, exigência do padrão JWT) e `papel`
   ('produtor' | 'administrador', ver app/db/models.py), mais `tipo`
   ('access' | 'refresh') para impedir que um refresh token seja usado
   diretamente como se fosse um access token em outro endpoint.

   bcrypt é usado diretamente (não via passlib, ver requirements.txt).

Relação com o resto do sistema:
- validar_api_key_dispositivo() é usada como dependency no endpoint
  /diagnostico (app/api/routes/diagnostico.py).
- obter_produtor_atual() é usada como dependency nos endpoints do
  dashboard (app/api/routes/leituras.py, diagnosticos.py, alertas.py).
- criar_access_token()/criar_refresh_token()/verificar_senha() são
  usadas por app/api/routes/auth.py (POST /auth/login, /auth/refresh).
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal

import bcrypt
import jwt
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


# --- Dashboard: senha (bcrypt) ---


def gerar_hash_senha(senha_texto_puro: str) -> str:
    """Gera o hash bcrypt de uma senha, para gravar em
    usuarios.senha_hash. Usado no cadastro/seed de contas, nunca no
    login (login só verifica, ver verificar_senha)."""
    hash_bytes = bcrypt.hashpw(senha_texto_puro.encode("utf-8"), bcrypt.gensalt())
    return hash_bytes.decode("utf-8")


def verificar_senha(senha_texto_puro: str, hash_bcrypt: str) -> bool:
    """Verifica a senha do produtor contra o hash bcrypt armazenado."""
    return bcrypt.checkpw(senha_texto_puro.encode("utf-8"), hash_bcrypt.encode("utf-8"))


# --- Dashboard: tokens JWT ---

_TipoToken = Literal["access", "refresh"]


def _criar_token(usuario_id: int, papel: str, tipo: _TipoToken, expira_em: timedelta) -> str:
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario_id),
        "papel": papel,
        "tipo": tipo,
        "iat": agora,
        "exp": agora + expira_em,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def criar_access_token(usuario_id: int, papel: str) -> str:
    """Gera um JWT de acesso de curta duração (padrão 24h, ver
    settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)."""
    return _criar_token(
        usuario_id, papel, "access",
        timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def criar_refresh_token(usuario_id: int, papel: str) -> str:
    """Gera um refresh token de longa duração (padrão 30 dias, ver
    settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)."""
    return _criar_token(
        usuario_id, papel, "refresh",
        timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decodificar_token(token: str, tipo_esperado: _TipoToken) -> dict:
    """Decodifica e valida um JWT (assinatura, expiração e o campo
    `tipo`). Levanta HTTPException 401 em qualquer problema: token
    ausente, expirado, assinatura inválida, ou do tipo errado (ex.:
    tentar usar um refresh token direto num endpoint que exige access
    token)."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido."
        )

    if payload.get("tipo") != tipo_esperado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Tipo de token incorreto (esperado '{tipo_esperado}').",
        )
    return payload


def obter_produtor_atual(authorization: str | None = Header(default=None)) -> dict:
    """Dependency FastAPI para os endpoints do dashboard: exige um
    access token JWT válido no cabeçalho Authorization: Bearer <token>.
    Retorna um dict com `usuario_id` (int) e `papel` (str). Diferente
    de validar_api_key_dispositivo, aqui o prefixo "Bearer" É exigido
    (é o cabeçalho que app/src/services/api.ts, do dashboard, envia)."""
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso ausente ou em formato inválido.",
        )

    token = authorization.removeprefix("Bearer ").strip()
    payload = decodificar_token(token, tipo_esperado="access")

    try:
        usuario_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido."
        )

    return {"usuario_id": usuario_id, "papel": payload.get("papel", "produtor")}
