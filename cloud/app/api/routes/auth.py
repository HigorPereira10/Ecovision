"""
Rotas de autenticação dos usuários do aplicativo.

- POST /auth/register: cadastro aberto, sempre com papel "produtor" e
  e-mail pendente de confirmação.
- POST /auth/verify-email e /auth/resend-code: confirmação por código de
  6 dígitos.
- POST /auth/login: verifica e-mail e senha e emite token de acesso (24 h)
  e de renovação (30 dias).
- POST /auth/forgot-password e /auth/reset-password: redefinição de senha
  por código.
- POST /auth/refresh: novo token de acesso a partir do token de renovação.

Proteções: as respostas não revelam se um e-mail tem conta, inclusive no
tempo de resposta; o código enviado por e-mail nunca volta na API e é
guardado como hash; tentativas de login são limitadas por e-mail digitado.
"""

import logging
import re
import secrets
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
from app.config import settings
from app.core import emails
from app.db.models import CodigoEmail, TentativaLogin, Usuario
from app.db.schemas import (
    EsqueciSenhaRequest,
    LoginRequest,
    MensagemOut,
    RedefinirSenhaRequest,
    RefreshRequest,
    ReenviarCodigoRequest,
    RegistroRequest,
    TokenResponse,
    UsuarioCriadoOut,
    VerificarEmailRequest,
)
from app.db.session import get_session

logger = logging.getLogger("ecovision.cloud.auth")

router = APIRouter()

# Validação de e-mail por expressão regular, igual à do aplicativo; recusa
# os casos comuns (sem @, sem domínio, com espaço) sem dependência extra.
_EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# Bloqueio por força bruta, contado por e-mail digitado (ver TentativaLogin).
_MAX_TENTATIVAS = 5
_BLOQUEIO = timedelta(minutes=15)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


async def _checar_bloqueio(sessao: AsyncSession, email: str) -> None:
    """Recusa a tentativa se o e-mail está bloqueado, com 429 e o tempo
    restante. Vale para qualquer e-mail digitado, exista ou não a conta."""
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


# --- Códigos enviados por e-mail ---

_VALIDADE_CODIGO = timedelta(minutes=15)
_MAX_TENTATIVAS_CODIGO = 5

# Intervalo mínimo entre reenvios para o mesmo e-mail, para proteger a cota
# diária do serviço de e-mail.
_INTERVALO_REENVIO = timedelta(seconds=60)

TIPO_VERIFICACAO = "verificacao"
TIPO_RECUPERACAO = "recuperacao"


def _gerar_codigo() -> str:
    """Código numérico de 6 dígitos. Validade de 15 minutos, uso único e
    limite de tentativas tornam a força bruta inviável."""
    return f"{secrets.randbelow(1_000_000):06d}"


async def _criar_codigo(sessao: AsyncSession, email: str, tipo: str) -> str:
    """Gera um código, grava o hash e devolve o código em claro para envio.

    Invalida os códigos anteriores do mesmo tipo."""
    anteriores = await sessao.execute(
        select(CodigoEmail).where(
            CodigoEmail.email == email,
            CodigoEmail.tipo == tipo,
            CodigoEmail.usado_em.is_(None),
        )
    )
    for antigo in anteriores.scalars().all():
        antigo.usado_em = _agora()

    codigo = _gerar_codigo()
    sessao.add(
        CodigoEmail(
            email=email,
            tipo=tipo,
            codigo_hash=gerar_hash_senha(codigo),
            expira_em=_agora() + _VALIDADE_CODIGO,
        )
    )
    await sessao.commit()
    return codigo


async def _consumir_codigo(sessao: AsyncSession, email: str, tipo: str, codigo: str) -> bool:
    """Confere o código e o marca como usado. Devolve False para código
    errado, expirado, já usado ou com tentativas esgotadas; a resposta ao
    usuário não diferencia esses casos."""
    registro = await sessao.scalar(
        select(CodigoEmail)
        .where(
            CodigoEmail.email == email,
            CodigoEmail.tipo == tipo,
            CodigoEmail.usado_em.is_(None),
        )
        .order_by(CodigoEmail.id.desc())
        .limit(1)
    )

    if registro is None:
        return False

    expira_em = registro.expira_em
    if expira_em.tzinfo is None:  # SQLite devolve datetime sem fuso
        expira_em = expira_em.replace(tzinfo=timezone.utc)

    if expira_em < _agora() or registro.tentativas >= _MAX_TENTATIVAS_CODIGO:
        return False

    if not verificar_senha(codigo, registro.codigo_hash):
        registro.tentativas += 1
        await sessao.commit()
        return False

    registro.usado_em = _agora()
    await sessao.commit()
    return True


async def _limpar_falhas(sessao: AsyncSession, email: str) -> None:
    """Zera o contador após um login bem-sucedido."""
    registro = await sessao.get(TentativaLogin, email)
    if registro is not None:
        await sessao.delete(registro)
        await sessao.commit()


@router.post("/auth/login", response_model=TokenResponse)
async def login(dados: LoginRequest, sessao: AsyncSession = Depends(get_session)) -> TokenResponse:
    """Autentica o usuário e devolve token de acesso e de renovação.

    A mensagem de erro é a mesma para e-mail inexistente e senha errada, e
    a verificação contra HASH_DESCARTAVEL iguala o tempo de resposta nos
    dois casos.
    """
    # O cadastro grava o e-mail em minúsculas.
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

    # A exigência de confirmação só é informada depois de a senha conferir,
    # para não revelar a existência da conta.
    if not usuario.email_verificado:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Confirme seu e-mail para entrar. Verifique a caixa de entrada e o spam.",
        )

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
    """Cria uma conta de produtor (cadastro aberto).

    Uma conta nova não vê nenhum dado até vincular um dispositivo. O papel
    é sempre "produtor", independentemente do corpo da requisição; o papel
    de administrador só é concedido por script.
    """
    nome = dados.nome.strip()
    email = dados.email.strip().lower()

    erros: list[str] = []
    if len(nome.split()) < 2:
        erros.append("Informe nome e sobrenome.")
    if not _EMAIL_REGEX.match(email):
        erros.append("Informe um e-mail válido.")

    # Devolve todas as regras de senha não cumpridas de uma vez.
    erros.extend(validar_forca_senha(dados.senha))

    if erros:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=erros
        )

    # Verificação antecipada para uma mensagem clara; a garantia contra
    # cadastros simultâneos é o índice único, tratado abaixo.
    ja_existe = await sessao.scalar(select(Usuario.id).where(Usuario.email == email))
    if ja_existe is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma conta com este e-mail.",
        )

    # Sem envio de e-mail configurado, a conta nasce ativa, para não ficar
    # impossível de confirmar.
    pode_enviar_email = settings.email_configurado
    if not pode_enviar_email:
        logger.warning(
            "SMTP nao configurado: conta %s criada JA VERIFICADA, sem confirmacao.", email
        )

    usuario = Usuario(
        nome=nome,
        email=email,
        senha_hash=gerar_hash_senha(dados.senha),
        papel="produtor",
        email_verificado=not pode_enviar_email,
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

    if pode_enviar_email:
        codigo = await _criar_codigo(sessao, email, TIPO_VERIFICACAO)
        assunto, corpo = emails.montar_email_verificacao(nome, codigo)
        if not emails.enviar(email, assunto, corpo):
            # Falha no envio: a conta é liberada e o erro fica no log.
            logger.error(
                "Conta %s criada mas o email de verificacao falhou. "
                "Liberando a conta para nao prender o produtor.",
                email,
            )
            usuario.email_verificado = True
            await sessao.commit()
            await sessao.refresh(usuario)

    return usuario


@router.post("/auth/verify-email", response_model=MensagemOut)
async def verificar_email(
    dados: VerificarEmailRequest, sessao: AsyncSession = Depends(get_session)
) -> MensagemOut:
    """Confirma o cadastro com o código de 6 dígitos enviado por e-mail."""
    email = dados.email.strip().lower()

    if not await _consumir_codigo(sessao, email, TIPO_VERIFICACAO, dados.codigo.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou expirado. Peça um novo código.",
        )

    usuario = await sessao.scalar(select(Usuario).where(Usuario.email == email))
    if usuario is not None:
        usuario.email_verificado = True
        await sessao.commit()
        logger.info("Email confirmado: %s", email)

    return MensagemOut(mensagem="E-mail confirmado. Agora é só entrar.")


@router.post("/auth/resend-code", response_model=MensagemOut)
async def reenviar_codigo(
    dados: ReenviarCodigoRequest, sessao: AsyncSession = Depends(get_session)
) -> MensagemOut:
    """Envia um novo código de confirmação para uma conta pendente.

    Responde sempre da mesma forma, exista ou não a conta, e o novo código
    invalida o anterior.
    """
    email = dados.email.strip().lower()
    resposta = MensagemOut(
        mensagem="Se houver um cadastro pendente para este e-mail, o código foi reenviado."
    )

    usuario = await sessao.scalar(select(Usuario).where(Usuario.email == email))
    if usuario is None or usuario.email_verificado:
        logger.info(
            "Reenvio ignorado para %s (conta inexistente ou ja confirmada).", email
        )
        return resposta

    if not settings.email_configurado:
        logger.error("SMTP nao configurado: reenvio de codigo indisponivel para %s", email)
        return resposta

    ultimo_envio = await sessao.scalar(
        select(CodigoEmail.criado_em)
        .where(CodigoEmail.email == email, CodigoEmail.tipo == TIPO_VERIFICACAO)
        .order_by(CodigoEmail.id.desc())
        .limit(1)
    )
    if ultimo_envio is not None:
        if ultimo_envio.tzinfo is None:  # SQLite devolve datetime sem fuso
            ultimo_envio = ultimo_envio.replace(tzinfo=timezone.utc)
        if _agora() - ultimo_envio < _INTERVALO_REENVIO:
            logger.info("Reenvio recusado por intervalo minimo: %s", email)
            return resposta

    codigo = await _criar_codigo(sessao, email, TIPO_VERIFICACAO)
    assunto, corpo = emails.montar_email_verificacao(usuario.nome or "produtor", codigo)
    emails.enviar(email, assunto, corpo)
    logger.info("Codigo de verificacao reenviado: %s", email)
    return resposta


@router.post("/auth/forgot-password", response_model=MensagemOut)
async def esqueci_a_senha(
    dados: EsqueciSenhaRequest, sessao: AsyncSession = Depends(get_session)
) -> MensagemOut:
    """Envia um código de redefinição de senha. Responde sempre da mesma
    forma, exista ou não a conta, e o código só sai por e-mail."""
    email = dados.email.strip().lower()
    resposta = MensagemOut(
        mensagem="Se existir uma conta com este e-mail, o código foi enviado."
    )

    usuario = await sessao.scalar(select(Usuario).where(Usuario.email == email))
    if usuario is None:
        logger.info("Pedido de recuperacao para email inexistente: %s", email)
        return resposta

    if not settings.email_configurado:
        logger.error("SMTP nao configurado: recuperacao de senha indisponivel para %s", email)
        return resposta

    codigo = await _criar_codigo(sessao, email, TIPO_RECUPERACAO)
    assunto, corpo = emails.montar_email_recuperacao(codigo)
    emails.enviar(email, assunto, corpo)
    return resposta


@router.post("/auth/reset-password", response_model=MensagemOut)
async def redefinir_senha(
    dados: RedefinirSenhaRequest, sessao: AsyncSession = Depends(get_session)
) -> MensagemOut:
    """Redefine a senha com o código recebido por e-mail, aplicando as
    mesmas regras de senha do cadastro."""
    email = dados.email.strip().lower()

    problemas = validar_forca_senha(dados.nova_senha)
    if problemas:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=problemas
        )

    if not await _consumir_codigo(sessao, email, TIPO_RECUPERACAO, dados.codigo.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou expirado. Peça um novo código.",
        )

    usuario = await sessao.scalar(select(Usuario).where(Usuario.email == email))
    if usuario is None:
        # Não revela que o código pertence a um e-mail sem conta.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou expirado. Peça um novo código.",
        )

    usuario.senha_hash = gerar_hash_senha(dados.nova_senha)
    # Quem comprovou acesso ao e-mail também tem o endereço confirmado.
    usuario.email_verificado = True
    await sessao.commit()

    # Zera o bloqueio por tentativas anteriores.
    await _limpar_falhas(sessao, email)

    logger.info("Senha redefinida: %s", email)
    return MensagemOut(mensagem="Senha alterada. Agora é só entrar com a nova senha.")


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(dados: RefreshRequest) -> TokenResponse:
    """Troca um token de renovação válido por um novo token de acesso, sem
    consultar o banco (usuario_id e papel vêm assinados no token)."""
    payload = decodificar_token(dados.refresh_token, tipo_esperado="refresh")
    usuario_id = int(payload["sub"])
    papel = payload.get("papel", "produtor")

    return TokenResponse(access_token=criar_access_token(usuario_id, papel))
