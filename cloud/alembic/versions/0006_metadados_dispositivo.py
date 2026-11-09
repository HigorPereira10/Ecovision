"""metadados de localização e intervalo por dispositivo

Campo, setor e intervalo de captura exibidos na tela de Perfil. Colunas
nullable, preenchidas depois para as linhas existentes.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-10

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("dispositivos", sa.Column("campo", sa.String(), nullable=True))
    op.add_column("dispositivos", sa.Column("setor", sa.String(), nullable=True))
    op.add_column(
        "dispositivos", sa.Column("intervalo_captura_min", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("dispositivos", "intervalo_captura_min")
    op.drop_column("dispositivos", "setor")
    op.drop_column("dispositivos", "campo")
