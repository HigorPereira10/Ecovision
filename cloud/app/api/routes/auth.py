"""
cloud/app/api/routes/auth.py

Endpoints de autenticação do PRODUTOR no dashboard/app (não confundir com
a API Key do dispositivo IoT, ver app/core/security.py para a distinção).

Rotas, conforme ADR 0003 (JWT do produtor) e ADR 0010 (cadastro aberto
e confirmação por e-mail):
- POST /auth/register: cria conta de produtor. Cadastro ABERTO, com
  papel sempre 'produtor' e e-mail pendente de confirmação.
- POST /auth/verify-email: confirma a conta com o código de 6 dígitos.
- POST /auth/resend-code: reenvia o código de uma conta pendente.
- POST /auth/login: valida email/senha (hash bcrypt) e emite um par de
  tokens: JWT de acesso (24h) + refresh token (30 dias).
- POST /auth/forgot-password e POST /auth/reset-password: recuperação
  de senha pelo mesmo mecanismo de código por e-mail.
- POST /auth/refresh: troca um refresh token válido por um novo JWT de
  acesso (não emite um novo refresh token; a sessão de 30 dias continua
  contada a partir do login original).

HISTÓRICO: até 2026-10-10 não existia cadastro, e a única conta de
produtor era semeada à mão por cloud/scripts/seed_usuario_teste.py. O
script continua existindo para popular ambiente de teste, mas não é
mais o caminho normal de criar conta.

TRÊS PROTEÇÕES QUE PARECEM DETALHE E NÃO SÃO:
1. Anti-enumeração: login, recuperação e reenvio respondem igual para
   e-mail cadastrado e inexistente, inclusive no tempo de resposta
   (ver HASH_DESCARTAVEL em app/core/security.py).
2. O código enviado por e-mail nunca aparece em nenhuma resposta da
   API, e no banco fica apenas o hash bcrypt dele.
3. Força bruta de senha é travada por e-mail digitado, não por conta
   existente (ver TentativaLogin em app/db/models.py).

Relação com o resto do sistema:
- Consumido pelo frontend (app/) para autenticar o produtor.
- Depende de app/core/security.py (geração/validação de JWT, verificação
  de hash bcrypt), app/core/emails.py (envio do código) e
  app/db/models.py (tabelas usuarios, codigos_email, tentativas_login).
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


# --- Códigos enviados por email ---

_VALIDADE_CODIGO = timedelta(minutes=15)
_MAX_TENTATIVAS_CODIGO = 5

# Intervalo minimo entre dois reenvios de codigo para o mesmo email.
# Nao e protecao contra invasao (o reenvio nao revela nada e so manda
# email para o proprio dono do endereco): e protecao de RECURSO. O
# plano gratuito do Brevo da 300 emails por dia, e um botao de
# "reenviar" sem trava permitiria esgotar a cota do dia em segundos,
# derrubando o cadastro de todo mundo. 60 segundos tambem cobre o caso
# honesto de quem toca duas vezes porque o email demorou a chegar.
_INTERVALO_REENVIO = timedelta(seconds=60)

TIPO_VERIFICACAO = "verificacao"
TIPO_RECUPERACAO = "recuperacao"


def _gerar_codigo() -> str:
    """Código numérico de 6 dígitos, fácil de ler do email e digitar.

    São apenas um milhão de combinações, o que isoladamente seria
    fraco. O que torna isso seguro é a soma de três limites:
    validade de 15 minutos, uso único, e no máximo
    _MAX_TENTATIVAS_CODIGO tentativas. A chance de acerto por força
    bruta fica em 5 por milhão."""
    return f"{secrets.randbelow(1_000_000):06d}"


async def _criar_codigo(sessao: AsyncSession, email: str, tipo: str) -> str:
    """Gera um código, guarda o HASH e devolve o código em claro para
    quem vai enviá-lo por email.

    Invalida os códigos anteriores do mesmo tipo: pedir um código novo
    tem que derrubar o antigo, senão um código vazado continuaria
    valendo mesmo depois de a pessoa pedir outro."""
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
    """Confere o código e o marca como usado. Devolve False para
    código errado, expirado, já usado ou com tentativas esgotadas.

    Quem chama NÃO deve diferenciar esses casos na resposta: dizer
    "código expirado" em vez de "código inválido" confirma que existe
    um pedido em andamento para aquele email."""
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

    # Só aqui, depois de a senha conferir. Avisar antes revelaria que o
    # email existe para quem nem sabe a senha. Quem chegou até este
    # ponto já provou conhecer a credencial, então a mensagem pode ser
    # específica e dizer o que fazer.
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

    # Sem SMTP configurado a conta nasce ATIVA. Criá-la bloqueada seria
    # pior do que não verificar: o produtor ficaria preso numa conta que
    # ninguém consegue confirmar, porque o email de código nunca sairia.
    # Mesma filosofia de app/core/inference.py: dependência externa
    # ausente degrada o comportamento, não derruba o sistema.
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
            # A conta existe e o email falhou. Deixar o produtor
            # trancado seria o pior resultado, então libera e registra:
            # o log é o que permite descobrir que o SMTP está quebrado.
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
    """Confirma o cadastro com o código de 6 dígitos enviado por email.

    A mensagem de erro é a mesma para código errado, expirado, já usado
    ou com tentativas esgotadas. Diferenciar confirmaria que existe um
    pedido em andamento para aquele endereço.
    """
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
    """Envia um código de confirmação novo para uma conta pendente.

    POR QUE ESTA ROTA EXISTE: sem ela, uma conta cujo e-mail de
    confirmação não chegasse ficava inacessível para sempre. O login
    recusa quem não confirmou (ver login() acima), o cadastro recusa o
    e-mail por já existir, e não havia nenhum caminho para gerar outro
    código. Bastava o e-mail cair no spam e ser apagado.

    Responde SEMPRE a mesma coisa, como /auth/forgot-password: conta
    inexistente, conta já confirmada e código recém-enviado recebem
    resposta idêntica. Diferenciar transformaria esta rota num
    detector de quais e-mails têm conta e quais ainda estão pendentes.

    Um código novo invalida o anterior, porque _criar_codigo() derruba
    os códigos não usados do mesmo tipo. Então quem pedir reenvio e
    depois digitar o código do primeiro e-mail recebe "código
    inválido", o que é o comportamento correto: vale o último.
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
    """Envia um código de redefinição de senha.

    Responde SEMPRE a mesma coisa, exista ou não a conta. Diferenciar
    permitiria descobrir quais emails estão cadastrados simplesmente
    testando endereços, o que anularia a proteção anti-enumeração que o
    login já tem.

    O código nunca volta na resposta: sai apenas pelo email.
    """
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
    """Troca a senha usando o código recebido por email.

    Valida a força da nova senha com as mesmas regras do cadastro: sem
    isto, a recuperação viraria um caminho para contornar a exigência de
    senha forte.
    """
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
        # Código válido para email sem conta não deveria acontecer, mas
        # se acontecer a resposta não entrega essa informação.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou expirado. Peça um novo código.",
        )

    usuario.senha_hash = gerar_hash_senha(dados.nova_senha)
    # Quem provou ter acesso ao email também confirma o endereço.
    usuario.email_verificado = True
    await sessao.commit()

    # Zera o bloqueio por tentativas: quem acabou de redefinir a senha
    # não pode ficar preso pelo contador das tentativas antigas.
    await _limpar_falhas(sessao, email)

    logger.info("Senha redefinida: %s", email)
    return MensagemOut(mensagem="Senha alterada. Agora é só entrar com a nova senha.")


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(dados: RefreshRequest) -> TokenResponse:
    """Troca um refresh token válido por um novo JWT de acesso. Não
    consulta o banco: o próprio token já carrega usuario_id e papel
    (assinados, não podem ser forjados sem a chave secreta)."""
    payload = decodificar_token(dados.refresh_token, tipo_esperado="refresh")
    usuario_id = int(payload["sub"])
    papel = payload.get("papel", "produtor")

    return TokenResponse(access_token=criar_access_token(usuario_id, papel))
