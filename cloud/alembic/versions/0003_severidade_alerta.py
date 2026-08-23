"""adiciona severidade em alertas

Permite diferenciar risco urgente ("alta") de informativo ("media") na
lista de alertas do dashboard — ver docs/decisions/0005-limiares-ambientais.md
e docs/decisions/0006-recomendacoes-por-diagnostico.md para a origem de
cada valor.

Seguro adicionar como NOT NULL diretamente — a tabela alertas está
vazia neste momento do projeto (confirmado antes de aplicar esta
migration no Supabase real).

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
