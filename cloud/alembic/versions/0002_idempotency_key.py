"""adiciona idempotency_key em registros_imagem

Corrige um problema real: o edge/ não mandava nenhum identificador
estável por captura, então a API não conseguia distinguir uma foto nova
de um reenvio (ex.: a API confirma HTTP 200 mas o processo do
Raspberry Pi cai antes de tirar o registro da fila local — no próximo
ciclo o mesmo registro seria enviado de novo e viraria uma linha
duplicada). Ver edge/src/upload/uploader.py e
cloud/app/api/routes/diagnostico.py.

Seguro adicionar como NOT NULL diretamente (sem passo intermediário
nullable + backfill) porque a tabela está vazia neste momento do
projeto — não há linhas de produção pra migrar.

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
