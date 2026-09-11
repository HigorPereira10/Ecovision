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

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import criar_access_token, criar_refresh_token, decodificar_token, verificar_senha
from app.db.models import Usuario
from app.db.schemas import LoginRequest, RefreshRequest, TokenResponse
from app.db.session import get_session

router = APIRouter()


@router.post("/auth/login", response_model=TokenResponse)
async def login(dados: LoginRequest, sessao: AsyncSession = Depends(get_session)) -> TokenResponse:
    """Autentica o produtor e retorna JWT de acesso + refresh token.

    Mensagem de erro deliberadamente genérica ("email ou senha
    inválidos") tanto para email inexistente quanto para senha errada:
    diferenciar os dois casos permitiria a um atacante descobrir quais
    emails têm conta cadastrada (enumeração de usuários)."""
    resultado = await sessao.execute(select(Usuario).where(Usuario.email == dados.email))
    usuario = resultado.scalar_one_or_none()

    if usuario is None or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos.",
        )

    return TokenResponse(
        access_token=criar_access_token(usuario.id, usuario.papel),
        refresh_token=criar_refresh_token(usuario.id, usuario.papel),
    )


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(dados: RefreshRequest) -> TokenResponse:
    """Troca um refresh token válido por um novo JWT de acesso. Não
    consulta o banco: o próprio token já carrega usuario_id e papel
    (assinados, não podem ser forjados sem a chave secreta)."""
    payload = decodificar_token(dados.refresh_token, tipo_esperado="refresh")
    usuario_id = int(payload["sub"])
    papel = payload.get("papel", "produtor")

    return TokenResponse(access_token=criar_access_token(usuario_id, papel))
