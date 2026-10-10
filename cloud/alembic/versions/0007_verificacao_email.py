"""verificacao de email e codigos de uso unico

Duas mudancas que vem juntas porque usam a mesma infraestrutura de envio
de email:

1. `usuarios.email_verificado`: enquanto False, o login e recusado. Sem
   isso, qualquer um enchia o banco com contas de emails inventados, e
   quem digitasse o proprio email errado ficava trancado para sempre,
   porque nao existia recuperacao de senha.
2. `codigos_email`: codigos de uso unico, guardados como HASH, para
   confirmar cadastro e redefinir senha.

As contas que ja existem entram como verificadas (server_default 'true'
na criacao da coluna, trocado para 'false' em seguida para as novas).
Trancar fora do sistema quem ja estava usando seria o pior resultado
possivel desta migration.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-10

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default 'true' para as linhas EXISTENTES nascerem verificadas
    op.add_column(
        "usuarios",
        sa.Column(
            "email_verificado", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
    )
    # e 'false' daqui em diante, para conta nova precisar confirmar
    op.alter_column("usuarios", "email_verificado", server_default=sa.text("false"))

    op.create_table(
        "codigos_email",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, index=True),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("codigo_hash", sa.String(), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tentativas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("usado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("codigos_email")
    op.drop_column("usuarios", "email_verificado")
