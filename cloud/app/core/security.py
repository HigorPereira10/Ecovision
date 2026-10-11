"""
cloud/app/core/security.py

Implementa as DUAS mecânicas de autenticação decididas no Blueprint v3.0,
Seção 4.3 (ver docs/decisions/0003-autenticacao-dual.md): mecanismos
diferentes para pontas diferentes, deliberadamente.

1. Dispositivo IoT (Raspberry Pi -> API): credencial POR DISPOSITIVO,
   enviada CRUA no header Authorization, sem prefixo "Bearer" (é
   exatamente o que edge/src/upload/uploader.py envia). Quem confere é
   app/api/dispositivo_auth.py, contra o hash bcrypt guardado em
   `dispositivos.chave_hash`. A comparação é feita em tempo constante
   (secrets.compare_digest no ramo de transição, bcrypt no caminho
   normal), para não vazar a credencial por um ataque de timing.

   Este módulo contribui com a GERAÇÃO dessas credenciais
   (gerar_segredo_dispositivo e gerar_codigo_pareamento, abaixo); a
   verificação mora em app/api/ porque precisa consultar o banco, e
   app/core/ não importa app/db/.

   HISTÓRICO: o ADR 0003 escolheu uma chave única e GLOBAL, com a
   justificativa de que havia "1 único dispositivo". Isso significava
   que qualquer requisição com a chave certa podia se identificar como
   QUALQUER device_id, ou seja, injetar diagnóstico falso na estufa de
   outro produtor. A premissa caiu quando o cadastro foi aberto, e o
   ADR 0009 substituiu o mecanismo. A chave global ainda é aceita num
   ramo de transição explícito, para não derrubar um Pi em campo no
   momento do deploy; cada uso dela gera aviso no log.

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
from collections.abc import Callable
from typing import Literal

import bcrypt
import jwt
from fastapi import Header, HTTPException, status

from app.config import settings


def validar_api_key_dispositivo(authorization: str | None = Header(default=None)) -> None:
    """Dependency FastAPI: valida o header Authorization contra a API
    Key estática do dispositivo. Levanta 401 se ausente ou incorreta.

    A comparação é feita em BYTES, não em texto: secrets.compare_digest
    recusa comparar strings com caracteres não-ASCII e levanta TypeError,
    que escaparia daqui como erro 500 em vez de 401. Como o cabeçalho vem
    de fora, qualquer um poderia derrubar a rota com erro 500 mandando um
    byte acentuado. Comparar bytes aceita qualquer valor e mantém o tempo
    constante.
    """
    if authorization is None or not secrets.compare_digest(
        authorization.encode("utf-8"), settings.DEVICE_API_KEY.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key do dispositivo ausente ou inválida.",
        )



def obter_credencial_dispositivo(authorization: str | None = Header(default=None)) -> str:
    """Dependency FastAPI: extrai a credencial do dispositivo do header
    Authorization, SEM validar contra o banco.

    A validação de verdade acontece em app/api/dispositivo_auth.py,
    porque ela precisa do `device_id`, que chega no corpo do formulário e
    não no header, e precisa consultar o banco. Aqui só garante que
    existe alguma credencial antes de processar o upload da imagem.

    O prefixo "Bearer" é opcional de propósito: o edge/ envia a chave
    crua (ver edge/src/upload/uploader.py), diferente do app/, que usa
    "Bearer <jwt>"."""
    if not authorization or not authorization.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credencial do dispositivo ausente.",
        )
    return authorization.removeprefix("Bearer ").strip()


# --- Dashboard: senha (bcrypt) ---


def gerar_hash_senha(senha_texto_puro: str) -> str:
    """Gera o hash bcrypt de uma senha, para gravar em
    usuarios.senha_hash. Usado no cadastro/seed de contas, nunca no
    login (login só verifica, ver verificar_senha)."""
    hash_bytes = bcrypt.hashpw(senha_texto_puro.encode("utf-8"), bcrypt.gensalt())
    return hash_bytes.decode("utf-8")


def verificar_senha(senha_texto_puro: str, hash_bcrypt: str) -> bool:
    """Verifica a senha do produtor contra o hash bcrypt armazenado.

    Devolve False (em vez de propagar a exceção) quando o bcrypt recusa
    processar a entrada. O caso real é o limite de 72 bytes do bcrypt:
    sem isso, uma tentativa de login com senha longa virava erro 500 em
    vez de 401, e qualquer um podia disparar isso sem autenticação.
    Nenhum usuário legítimo é afetado, porque gerar_hash_senha() recusa
    criar conta com senha acima desse limite; ou seja, uma senha que o
    bcrypt não processa nunca corresponde a um hash armazenado.
    """
    try:
        return bcrypt.checkpw(senha_texto_puro.encode("utf-8"), hash_bcrypt.encode("utf-8"))
    except ValueError:
        return False


# --- Força da senha (cadastro) ---

# Mesmas 5 regras que app/src/screens/CadastroScreen.tsx mostra como
# checklist enquanto o produtor digita. Elas precisam existir AQUI
# também: a validação do app é conveniência de interface, e qualquer um
# pode chamar POST /auth/register direto, sem passar por ela.
_REGRAS_SENHA: list[tuple[str, "Callable[[str], bool]"]] = [
    ("Mínimo de 8 caracteres", lambda s: len(s) >= 8),
    ("Uma letra maiúscula", lambda s: any(c.isupper() for c in s)),
    ("Uma letra minúscula", lambda s: any(c.islower() for c in s)),
    ("Um número", lambda s: any(c.isdigit() for c in s)),
    ("Um símbolo (!@#$%...)", lambda s: any(not c.isalnum() for c in s)),
]

# O bcrypt recusa entradas acima de 72 BYTES (não caracteres: um emoji
# ou letra acentuada gasta mais de um). Sem checar aqui, gerar_hash_senha
# levanta ValueError e o cadastro vira erro 500, que qualquer um pode
# disparar sem autenticação. Ver a nota em verificar_senha.
LIMITE_BYTES_SENHA = 72


def validar_forca_senha(senha: str) -> list[str]:
    """Devolve a lista de regras que a senha NÃO cumpre. Lista vazia
    significa senha aceitável. Devolver todas de uma vez (em vez de
    parar na primeira) deixa o app mostrar o checklist completo."""
    problemas = [texto for texto, teste in _REGRAS_SENHA if not teste(senha)]

    if len(senha.encode("utf-8")) > LIMITE_BYTES_SENHA:
        problemas.append(
            f"No máximo {LIMITE_BYTES_SENHA} bytes "
            "(acentos e emojis contam mais de um caractere)"
        )

    return problemas


# --- Credenciais de dispositivo ---

def gerar_segredo_dispositivo() -> str:
    """Segredo que vai no .env do Pi e autentica aquele aparelho
    específico. Só o hash é guardado no banco."""
    return secrets.token_urlsafe(32)


def gerar_codigo_pareamento() -> str:
    """Código que o agricultor digita no app para reivindicar o
    dispositivo. Formato ECO-XXXX-XXXX, curto para digitar sem errar.

    Usa um alfabeto sem 0/O e 1/I/L, que são os pares mais confundidos
    ao ler de uma etiqueta colada no equipamento. São 32^8 combinações,
    o que torna adivinhar um código inviável, e ele deixa de valer assim
    que o dispositivo é vinculado (ver app/db/models.py, Dispositivo)."""
    alfabeto = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    bloco1 = "".join(secrets.choice(alfabeto) for _ in range(4))
    bloco2 = "".join(secrets.choice(alfabeto) for _ in range(4))
    return f"ECO-{bloco1}-{bloco2}"


# Hash bcrypt de uma senha descartável, usado por app/api/routes/auth.py
# para gastar o mesmo tempo de verificação quando o email não existe.
# Sem isso, o login responde bem mais rápido para email inexistente (a
# verificação bcrypt nem chega a rodar), e dá para descobrir quais emails
# têm conta cronometrando as respostas, o que anula a proteção da
# mensagem de erro genérica.
#
# Fixo em vez de calculado na importação de propósito: gerar um hash
# bcrypt custa algumas centenas de milissegundos, e isso entraria no
# tempo de partida da API (relevante no Railway, que tem cold start).
HASH_DESCARTAVEL = "$2b$12$t2gZxb0YcikcP.rCnwzujOB/1yZwthUuekkJh4ncz0ccdBfRKv2sG"


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


# Tolerância de relógio na validação do JWT, em segundos.
#
# O PyJWT recusa token cujo `iat` esteja no futuro ou cujo `exp` já tenha
# passado, comparando com o relógio de QUEM VALIDA. Sem folga, basta um
# segundo de diferença entre o relógio de quem assinou e o de quem
# confere para o token virar 401 "Token inválido", sem pista nenhuma da
# causa real.
#
# Isso não é hipotético: ao testar a API publicada, tokens gerados numa
# máquina 11 segundos adiantada foram recusados, enquanto os emitidos
# pelo próprio servidor funcionavam. O mesmo acontece em produção quando
# o Railway substitui o container num deploy: um token emitido segundos
# antes pode ser conferido por uma instância nova cujo relógio esteja
# levemente atrasado.
#
# 30 segundos é folga suficiente para desvio de relógio entre máquinas
# sincronizadas por NTP, e curta demais para ter valor para um atacante:
# ela não estende a validade de um token expirado de forma relevante
# (o access token dura 24h) nem permite usar token que ainda não existe.
_TOLERANCIA_RELOGIO_SEGUNDOS = 30


def decodificar_token(token: str, tipo_esperado: _TipoToken) -> dict:
    """Decodifica e valida um JWT (assinatura, expiração e o campo
    `tipo`). Levanta HTTPException 401 em qualquer problema: token
    ausente, expirado, assinatura inválida, ou do tipo errado (ex.:
    tentar usar um refresh token direto num endpoint que exige access
    token).

    Tolera até _TOLERANCIA_RELOGIO_SEGUNDOS de diferença de relógio
    entre quem assinou e quem valida."""
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
