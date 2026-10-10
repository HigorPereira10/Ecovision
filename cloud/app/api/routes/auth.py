"""
cloud/app/api/routes/auth.py

Endpoints de autenticação do PRODUTOR no dashboard/app (não confundir com
a API Key do dispositivo IoT, ver app/core/security.py para a distinção).

Conforme Blueprint v3.0 Seção 4.3 / ADR 0003:
- POST /auth/login: valida email/senha (hash bcrypt) e emite um par de
  tokens: JWT de acesso (24h) + refresh token (30 dias).
- POST /auth/refresh: troca um refresh token válido por um novo JWT de
  acesso (não emite um novo refresh token; a sessão de 30 dias continua
  contada a partir do login original).

A primeira conta de produtor é semeada manualmente (não existe endpoint
de cadastro nesta rodada, decisão do grupo em 2026-09-11): ver
cloud/scripts/seed_usuario_teste.py.

Relação com o resto do sistema:
- Consumido pelo frontend (app/) para autenticar o produtor.
- Depende de app/core/security.py (geração/validação de JWT, verificação
  de hash bcrypt) e app/db/models.py (tabela usuarios).
"""

import logging
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    HASH_DESCARTAVEL,
    criar_access_token,
    criar_refresh_token,
    decodificar_token,
    gerar_hash_senha,
    validar_forca_senha,
    verificar_senha,
)
from app.db.models import TentativaLogin, Usuario
from app.db.schemas import (
    LoginRequest,
    RefreshRequest,
    RegistroRequest,
    TokenResponse,
    UsuarioCriadoOut,
)
from app.db.session import get_session

logger = logging.getLogger("ecovision.cloud.auth")

router = APIRouter()

# Validação de email por expressão regular, a mesma de
# app/src/screens/CadastroScreen.tsx. Regex não cobre todos os casos
# exóticos da RFC 5322, mas rejeita o que interessa (sem @, sem domínio,
# com espaço) sem puxar a dependência `email-validator` para um deploy
# que precisa caber na RAM do Railway.
_EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# Trava contra força bruta de senha. Ver TentativaLogin em
# app/db/models.py para por que o contador é indexado pelo email
# DIGITADO, exista a conta ou não.
_MAX_TENTATIVAS = 5
_BLOQUEIO = timedelta(minutes=15)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


async def _checar_bloqueio(sessao: AsyncSession, email: str) -> None:
    """Recusa a tentativa se este email está em bloqueio temporário.

    Responde 429 com o tempo restante. Isso NÃO denuncia quais emails
    existem, porque o contador vale para qualquer email digitado: um
    endereço inexistente martelado 5 vezes recebe exatamente a mesma
    resposta de um cadastrado."""
    registro = await sessao.get(TentativaLogin, email)
    if registro is None or registro.bloqueado_ate is None:
        return

    bloqueado_ate = registro.bloqueado_ate
    if bloqueado_ate.tzinfo is None:  # SQLite devolve datetime sem fuso
        bloqueado_ate = bloqueado_ate.replace(tzinfo=timezone.utc)

    if bloqueado_ate > _agora():
        faltam = int((bloqueado_ate - _agora()).total_seconds() // 60) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Muitas tentativas. Tente novamente em {faltam} minuto(s).",
        )


async def _registrar_falha(sessao: AsyncSession, email: str) -> None:
    """Soma uma tentativa falha e bloqueia ao atingir o limite."""
    registro = await sessao.get(TentativaLogin, email)
    if registro is None:
        registro = TentativaLogin(email=email, tentativas=0)
        sessao.add(registro)

    registro.tentativas += 1
    registro.atualizado_em = _agora()

    if registro.tentativas >= _MAX_TENTATIVAS:
        registro.bloqueado_ate = _agora() + _BLOQUEIO
        registro.tentativas = 0  # zera o contador junto com o bloqueio
        logger.warning("Email bloqueado por excesso de tentativas: %s", email)

    await sessao.commit()


async def _limpar_falhas(sessao: AsyncSession, email: str) -> None:
    """Zera o contador depois de um login bem-sucedido."""
    registro = await sessao.get(TentativaLogin, email)
    if registro is not None:
        await sessao.delete(registro)
        await sessao.commit()


@router.post("/auth/login", response_model=TokenResponse)
async def login(dados: LoginRequest, sessao: AsyncSession = Depends(get_session)) -> TokenResponse:
    """Autentica o produtor e retorna JWT de acesso + refresh token.

    Mensagem de erro deliberadamente genérica ("email ou senha
    inválidos") tanto para email inexistente quanto para senha errada:
    diferenciar os dois casos permitiria a um atacante descobrir quais
    emails têm conta cadastrada (enumeração de usuários).

    A verificação contra HASH_DESCARTAVEL quando o email não existe é o
    que faz essa proteção valer na prática. Antes ela era só aparente: o
    `or` em curto-circuito pulava o bcrypt para email inexistente, e a
    resposta voltava em ~0.39s contra ~0.65s para email cadastrado.
    Cronometrando as respostas dava para descobrir quais emails têm
    conta, mesmo com a mensagem idêntica.
    """
    # Normaliza antes de qualquer coisa: o cadastro grava o email em
    # minúsculas, então sem isto quem digitasse "Maria@X.com" no login
    # não acharia a própria conta.
    email = dados.email.strip().lower()

    await _checar_bloqueio(sessao, email)

    resultado = await sessao.execute(select(Usuario).where(Usuario.email == email))
    usuario = resultado.scalar_one_or_none()

    hash_para_verificar = usuario.senha_hash if usuario is not None else HASH_DESCARTAVEL
    senha_confere = verificar_senha(dados.senha, hash_para_verificar)

    if usuario is None or not senha_confere:
        await _registrar_falha(sessao, email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos.",
        )

    await _limpar_falhas(sessao, email)

    return TokenResponse(
        access_token=criar_access_token(usuario.id, usuario.papel),
        refresh_token=criar_refresh_token(usuario.id, usuario.papel),
    )


@router.post(
    "/auth/register", response_model=UsuarioCriadoOut, status_code=status.HTTP_201_CREATED
)
async def registrar(
    dados: RegistroRequest, sessao: AsyncSession = Depends(get_session)
) -> Usuario:
    """Cria uma conta de produtor. Cadastro aberto: qualquer pessoa pode
    se registrar.

    Isso só é seguro porque as rotas de leitura filtram por dono (ver
    app/api/escopo.py): uma conta recém-criada não enxerga nada até
    vincular um dispositivo próprio, pelo código de pareamento que vem
    com o aparelho.

    O papel é SEMPRE 'produtor', ignorando qualquer valor que venha no
    corpo. Sem isso, bastaria mandar papel='administrador' no JSON para
    ganhar acesso irrestrito a todas as estufas do sistema. O papel de
    administrador é concedido apenas por script, com acesso ao banco.
    """
    nome = dados.nome.strip()
    email = dados.email.strip().lower()

    erros: list[str] = []
    if len(nome.split()) < 2:
        erros.append("Informe nome e sobrenome.")
    if not _EMAIL_REGEX.match(email):
        erros.append("Informe um e-mail válido.")

    # Lista todas as regras de senha que falharam, não só a primeira,
    # para o app marcar o checklist inteiro de uma vez.
    erros.extend(validar_forca_senha(dados.senha))

    if erros:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=erros
        )

    # Checagem antecipada só para devolver uma mensagem clara no caso
    # comum. Ela NÃO basta sozinha: dois cadastros simultâneos com o
    # mesmo email passariam os dois por aqui e um quebraria no INSERT.
    # Quem garante de verdade é o índice único da coluna, tratado no
    # except abaixo.
    ja_existe = await sessao.scalar(select(Usuario.id).where(Usuario.email == email))
    if ja_existe is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma conta com este e-mail.",
        )

    usuario = Usuario(
        nome=nome,
        email=email,
        senha_hash=gerar_hash_senha(dados.senha),
        papel="produtor",
    )
    sessao.add(usuario)

    try:
        await sessao.commit()
    except IntegrityError:
        await sessao.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma conta com este e-mail.",
        )

    await sessao.refresh(usuario)
    logger.info("Conta de produtor criada: %s (id=%s)", email, usuario.id)
    return usuario


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(dados: RefreshRequest) -> TokenResponse:
    """Troca um refresh token válido por um novo JWT de acesso. Não
    consulta o banco: o próprio token já carrega usuario_id e papel
    (assinados, não podem ser forjados sem a chave secreta)."""
    payload = decodificar_token(dados.refresh_token, tipo_esperado="refresh")
    usuario_id = int(payload["sub"])
    papel = payload.get("papel", "produtor")

    return TokenResponse(access_token=criar_access_token(usuario_id, papel))
