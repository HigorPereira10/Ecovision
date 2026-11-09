"""leitura ambiental independente da foto

1. registro_imagem_id passa a aceitar NULL, para leituras sem foto; o
   UNIQUE continua valendo (o PostgreSQL admite vários NULL).
2. device_id passa a ser coluna da leitura, preenchida a partir de
   registros_imagem nas linhas existentes antes de virar NOT NULL.
3. idempotency_key, nullable e única, evita duplicar leituras reenviadas.
4. Índice em (device_id, criado_em), usado por GET /leituras.

O downgrade recusa executar se houver leituras sem foto, em vez de
apagá-las.

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-03

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "leituras_ambientais",
        "registro_imagem_id",
        existing_type=sa.Integer(),
        nullable=True,
    )

    op.add_column(
        "leituras_ambientais",
        sa.Column("device_id", sa.String(), nullable=True),
    )

    # Preenchimento: toda leitura existente veio de uma captura.
    op.execute(
        """
        UPDATE leituras_ambientais AS l
           SET device_id = r.device_id
          FROM registros_imagem AS r
         WHERE l.registro_imagem_id = r.id
        """
    )

    # Se restar linha sem device_id, o NOT NULL abaixo falha e a migração
    # é abortada.
    op.alter_column(
        "leituras_ambientais",
        "device_id",
        existing_type=sa.String(),
        nullable=False,
    )

    op.add_column(
        "leituras_ambientais",
        sa.Column("idempotency_key", sa.String(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_leituras_idempotency_key", "leituras_ambientais", ["idempotency_key"]
    )

    op.create_index(
        "ix_leituras_device_criado",
        "leituras_ambientais",
        ["device_id", "criado_em"],
    )


def downgrade() -> None:
    conexao = op.get_bind()
    orfas = conexao.execute(
        sa.text(
            "SELECT count(*) FROM leituras_ambientais WHERE registro_imagem_id IS NULL"
        )
    ).scalar_one()
    if orfas:
        raise RuntimeError(
            f"{orfas} leitura(s) sem foto no banco. Reverter exigiria apagar "
            "medicao feita em campo. Decida o que fazer com essas linhas "
            "antes de rodar o downgrade."
        )

    op.drop_index("ix_leituras_device_criado", table_name="leituras_ambientais")
    op.drop_constraint(
        "uq_leituras_idempotency_key", "leituras_ambientais", type_="unique"
    )
    op.drop_column("leituras_ambientais", "idempotency_key")
    op.drop_column("leituras_ambientais", "device_id")
    op.alter_column(
        "leituras_ambientais",
        "registro_imagem_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
