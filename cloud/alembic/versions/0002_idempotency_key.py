"""adiciona idempotency_key em registros_imagem

Identificador estável de cada captura, gerado pela fila local do
dispositivo, que permite descartar reenvios. A coluna foi criada como
NOT NULL diretamente porque a tabela estava vazia; com dados existentes,
seria necessário um passo intermediário nullable com preenchimento.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-22

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "registros_imagem",
        sa.Column("idempotency_key", sa.String(), nullable=False),
    )
    op.create_unique_constraint(
        "uq_registros_imagem_idempotency_key", "registros_imagem", ["idempotency_key"]
    )
    op.create_index(
        "ix_registros_imagem_idempotency_key", "registros_imagem", ["idempotency_key"]
    )


def downgrade() -> None:
    op.drop_index("ix_registros_imagem_idempotency_key", table_name="registros_imagem")
    op.drop_constraint(
        "uq_registros_imagem_idempotency_key", "registros_imagem", type_="unique"
    )
    op.drop_column("registros_imagem", "idempotency_key")
