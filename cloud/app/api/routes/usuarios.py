"""GET /usuarios/me: dados do usuário autenticado."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import obter_produtor_atual
from app.db.models import Usuario
from app.db.schemas import UsuarioOut
from app.db.session import get_session

router = APIRouter()


@router.get("/usuarios/me", response_model=UsuarioOut)
async def obter_perfil(
    produtor: dict = Depends(obter_produtor_atual),
    sessao: AsyncSession = Depends(get_session),
) -> Usuario:
    """Devolve nome, e-mail e papel do usuário autenticado; o id vem do
    token, não da rota."""
    usuario = await sessao.get(Usuario, produtor["usuario_id"])
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado."
        )
    return usuario
