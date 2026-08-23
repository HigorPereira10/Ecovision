"""schema inicial: registros_imagem, leituras_ambientais, diagnosticos,
alertas, usuarios, dispositivos

Escrita à mão (sem autogenerate, sem conexão real com Postgres
disponível neste momento) espelhando cloud/app/db/models.py. Só as 3
primeiras tabelas são de fato usadas nesta rodada (caminho do
dispositivo); as outras 3 têm o schema pronto para o dashboard, ver
cloud/README.md.

Revision ID: 0001
Revises:
Create Date: 2026-08-22

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "registros_imagem",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.String(), nullable=False),
        sa.Column("caminho_arquivo", sa.String(), nullable=False),
        sa.Column("capturado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_registros_imagem_device_id", "registros_imagem", ["device_id"]
    )

    op.create_table(
        "leituras_ambientais",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "registro_imagem_id",
            sa.Integer(),
            sa.ForeignKey("registros_imagem.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("temperatura_c", sa.Float(), nullable=True),
        sa.Column("umidade_ar_pct", sa.Float(), nullable=True),
        sa.Column("umidade_solo_pct", sa.Float(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "diagnosticos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "registro_imagem_id",
            sa.Integer(),
            sa.ForeignKey("registros_imagem.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("classe_prevista", sa.String(), nullable=False),
        sa.Column("confianca", sa.Float(), nullable=False),
        sa.Column("recomendacao", sa.String(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("senha_hash", sa.String(), nullable=False),
        sa.Column("papel", sa.String(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_usuarios_email", "usuarios", ["email"])

    op.create_table(
        "dispositivos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.String(), nullable=False, unique=True),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("nome", sa.String(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dispositivos_device_id", "dispositivos", ["device_id"])

    op.create_table(
        "alertas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("diagnostico_id", sa.Integer(), sa.ForeignKey("diagnosticos.id"), nullable=True),
        sa.Column(
            "leitura_id", sa.Integer(), sa.ForeignKey("leituras_ambientais.id"), nullable=True
        ),
        sa.Column("titulo", sa.String(), nullable=False),
        sa.Column("descricao", sa.String(), nullable=False),
        sa.Column("lido", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("alertas")
    op.drop_index("ix_dispositivos_device_id", table_name="dispositivos")
    op.drop_table("dispositivos")
    op.drop_index("ix_usuarios_email", table_name="usuarios")
    op.drop_table("usuarios")
    op.drop_table("diagnosticos")
    op.drop_table("leituras_ambientais")
    op.drop_index("ix_registros_imagem_device_id", table_name="registros_imagem")
    op.drop_table("registros_imagem")
