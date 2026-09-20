"""adiciona nome em usuarios

Necessario para GET /usuarios/me (tela de Perfil do app) ter um nome
para exibir, alem do email. Nullable porque o usuario de teste ja
existente (scripts/seed_usuario_teste.py) precisa continuar valido sem
precisar recriar a linha.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-14

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("nome", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "nome")
