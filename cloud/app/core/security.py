"""
Autenticação de dispositivos e de usuários.

1. Dispositivos: credencial própria de cada aparelho, enviada no cabeçalho
   Authorization sem o prefixo "Bearer". A verificação contra o hash bcrypt
   em dispositivos.chave_hash fica em app/api/dispositivo_auth.py, porque
   consulta o banco; aqui ficam a extração do cabeçalho e a geração de
   credenciais e códigos de pareamento. A chave global anterior ainda é
   aceita por compatibilidade, com aviso no log.

2. Usuários do aplicativo: JWT de acesso (24 h) e de renovação (30 dias),
   com senha em hash bcrypt. O payload contém `sub` (id do usuário),
   `papel` e `tipo` ("access" ou "refresh"), o que impede usar um token de
   renovação como token de acesso.
"""

import secrets
from datetime import datetime, timedelta, timezone
from collections.abc import Callable
from typing import Literal

import bcrypt
import jwt
from fastapi import Header, HTTPException, status

from app.config import settings


def validar_api_key_dispositivo(authorization: str | None = Header(default=None)) -> None:
    """Valida o cabeçalho Authorization contra a chave global anterior.
    Levanta 401 se ausente ou incorreta.

    Mantida apenas para compatibilidade: as rotas usam
    autenticar_dispositivo(). A comparação é feita em bytes, em tempo
    constante, para aceitar qualquer valor sem gerar erro 500.
    """
    if authorization is None or not secrets.compare_digest(
        authorization.encode("utf-8"), settings.DEVICE_API_KEY.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key do dispositivo ausente ou inválida.",
        )



def obter_credencial_dispositivo(authorization: str | None = Header(default=None)) -> str:
    """Dependência FastAPI que extrai a credencial do dispositivo do
    cabeçalho Authorization, sem consultar o banco.

    A validação ocorre em app/api/dispositivo_auth.py, que precisa do
    device_id enviado no formulário. O prefixo "Bearer" é opcional."""
    if not authorization or not authorization.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credencial do dispositivo ausente.",
        )
    return authorization.removeprefix("Bearer ").strip()


# --- Usuários: senha (bcrypt) ---


def gerar_hash_senha(senha_texto_puro: str) -> str:
    """Gera o hash bcrypt de uma senha, para usuarios.senha_hash."""
    hash_bytes = bcrypt.hashpw(senha_texto_puro.encode("utf-8"), bcrypt.gensalt())
    return hash_bytes.decode("utf-8")


def verificar_senha(senha_texto_puro: str, hash_bcrypt: str) -> bool:
    """Verifica a senha contra o hash armazenado.

    Devolve False quando o bcrypt recusa a entrada (acima de 72 bytes), em
    vez de gerar erro 500; nenhuma conta é criada com senha desse tamanho.
    """
    try:
        return bcrypt.checkpw(senha_texto_puro.encode("utf-8"), hash_bcrypt.encode("utf-8"))
    except ValueError:
        return False


# --- Força da senha (cadastro) ---

# As mesmas regras exibidas no cadastro do aplicativo; a validação no
# servidor é a que vale, já que a rota pode ser chamada diretamente.
_REGRAS_SENHA: list[tuple[str, "Callable[[str], bool]"]] = [
    ("Mínimo de 8 caracteres", lambda s: len(s) >= 8),
    ("Uma letra maiúscula", lambda s: any(c.isupper() for c in s)),
    ("Uma letra minúscula", lambda s: any(c.islower() for c in s)),
    ("Um número", lambda s: any(c.isdigit() for c in s)),
    ("Um símbolo (!@#$%...)", lambda s: any(not c.isalnum() for c in s)),
]

# O bcrypt recusa entradas acima de 72 bytes (caracteres acentuados e
# emojis ocupam mais de um byte).
LIMITE_BYTES_SENHA = 72


def validar_forca_senha(senha: str) -> list[str]:
    """Devolve as regras que a senha não cumpre; lista vazia significa
    senha aceitável."""
    problemas = [texto for texto, teste in _REGRAS_SENHA if not teste(senha)]

    if len(senha.encode("utf-8")) > LIMITE_BYTES_SENHA:
        problemas.append(
            f"No máximo {LIMITE_BYTES_SENHA} bytes "
            "(acentos e emojis contam mais de um caractere)"
        )

    return problemas


# --- Credenciais de dispositivo ---

def gerar_segredo_dispositivo() -> str:
    """Segredo do dispositivo, gravado no .env do aparelho; o banco guarda
    apenas o hash."""
    return secrets.token_urlsafe(32)


def gerar_codigo_pareamento() -> str:
    """Código de pareamento no formato ECO-XXXX-XXXX.

    O alfabeto exclui 0/O e 1/I/L, fáceis de confundir em uma etiqueta.
    São 32^8 combinações, e o código deixa de valer após o vínculo."""
    alfabeto = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    bloco1 = "".join(secrets.choice(alfabeto) for _ in range(4))
    bloco2 = "".join(secrets.choice(alfabeto) for _ in range(4))
    return f"ECO-{bloco1}-{bloco2}"


# Hash bcrypt de uma senha descartável: o login o verifica quando o e-mail
# não existe, para que o tempo de resposta não revele quais e-mails têm
# conta. É fixo para não acrescentar o custo do bcrypt à inicialização.
HASH_DESCARTAVEL = "$2b$12$t2gZxb0YcikcP.rCnwzujOB/1yZwthUuekkJh4ncz0ccdBfRKv2sG"


# --- Usuários: tokens JWT ---

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
    """Gera o token de acesso (validade em JWT_ACCESS_TOKEN_EXPIRE_MINUTES)."""
    return _criar_token(
        usuario_id, papel, "access",
        timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def criar_refresh_token(usuario_id: int, papel: str) -> str:
    """Gera o token de renovação (validade em JWT_REFRESH_TOKEN_EXPIRE_DAYS)."""
    return _criar_token(
        usuario_id, papel, "refresh",
        timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )


# Tolerância de relógio na validação dos tokens, em segundos. Sem folga,
# pequenas diferenças de relógio entre máquinas tornam tokens válidos
# inválidos; 30 s não estende de forma relevante a validade de um token.
_TOLERANCIA_RELOGIO_SEGUNDOS = 30


def decodificar_token(token: str, tipo_esperado: _TipoToken) -> dict:
    """Decodifica e valida um JWT (assinatura, expiração e `tipo`).

    Levanta 401 para token ausente, expirado, com assinatura inválida ou
    do tipo errado. Tolera _TOLERANCIA_RELOGIO_SEGUNDOS de diferença de
    relógio."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            leeway=_TOLERANCIA_RELOGIO_SEGUNDOS,
        )
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
    """Dependência FastAPI que exige um token de acesso válido em
    Authorization: Bearer <token>. Devolve {"usuario_id", "papel"}."""
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
