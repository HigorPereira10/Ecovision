"""credencial por dispositivo, pareamento e bloqueio de força bruta

1. dispositivos.chave_hash: hash bcrypt do segredo de cada dispositivo,
   em substituição à chave global compartilhada.
2. dispositivos.codigo_pareamento: código para o produtor reivindicar o
   aparelho; vale enquanto usuario_id for nulo.
3. tentativas_login: contador por e-mail digitado, exista ou não a conta.

As colunas novas são nullable, para manter válidas as linhas existentes.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-10

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("dispositivos", sa.Column("chave_hash", sa.String(), nullable=True))
    op.add_column("dispositivos", sa.Column("codigo_pareamento", sa.String(), nullable=True))
    op.add_column(
        "dispositivos", sa.Column("pareado_em", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index(
        "ix_dispositivos_codigo_pareamento",
        "dispositivos",
        ["codigo_pareamento"],
        unique=True,
    )

    op.create_table(
        "tentativas_login",
        sa.Column("email", sa.String(), primary_key=True),
        sa.Column("tentativas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bloqueado_ate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("tentativas_login")
    op.drop_index("ix_dispositivos_codigo_pareamento", table_name="dispositivos")
    op.drop_column("dispositivos", "pareado_em")
    op.drop_column("dispositivos", "codigo_pareamento")
    op.drop_column("dispositivos", "chave_hash")
