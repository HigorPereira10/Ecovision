"""adiciona nome em usuarios

Nullable para manter válidas as contas existentes.

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
