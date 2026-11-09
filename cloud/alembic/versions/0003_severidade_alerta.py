"""adiciona severidade em alertas

Diferencia risco urgente ("alta") de risco de progressão lenta ("media").
A coluna foi criada como NOT NULL diretamente porque a tabela estava vazia.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-23

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "alertas",
        sa.Column("severidade", sa.String(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("alertas", "severidade")
