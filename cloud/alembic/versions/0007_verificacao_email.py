"""verificação de e-mail e códigos de uso único

1. usuarios.email_verificado: enquanto False, o login é recusado.
2. codigos_email: códigos de uso único, guardados como hash, para
   confirmar o cadastro e redefinir a senha.

As contas existentes são marcadas como verificadas.

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
    # Padrão 'true' para que as linhas existentes nasçam verificadas...
    op.add_column(
        "usuarios",
        sa.Column(
            "email_verificado", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
    )
    # ...e 'false' a partir daqui, para contas novas.
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
