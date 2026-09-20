"""
cloud/app/api/routes/usuarios.py

Endpoint de perfil do produtor logado, para a tela de Perfil do
dashboard (app/).

Relação com o resto do sistema:
- Consumido por app/src/services/perfil.ts.
- Depende de app/db/models.py (tabela usuarios) e app/core/security.py
  (obter_produtor_atual, exige login).
"""

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
    """Retorna nome e email do produtor autenticado (usuario_id vem do
    JWT, não de um parâmetro de rota, evitando que um produtor consulte
    o perfil de outro)."""
    usuario = await sessao.get(Usuario, produtor["usuario_id"])
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado."
        )
    return usuario
