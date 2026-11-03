"""leitura ambiental independente da foto

PROBLEMA QUE ESTA MIGRATION RESOLVE

A tabela nasceu com `registro_imagem_id` NOT NULL e UNIQUE, modelando
"uma leitura por captura". Era verdade: o Pi lia os sensores e tirava a
foto no mesmo ciclo, a cada 2 horas, e mandava os dois juntos.

A consequencia nao era obvia. Como leitura nao existia sem foto, a
temperatura na tela inicial do app podia ter ate 2 horas de idade, e a
tela nao tinha como mostrar outra coisa: nao havia leitura mais nova
para buscar. Medir o ambiente de hora em hora e caro por causa da FOTO
(acionar o LED, comprimir 1,2 MB, subir para o Storage, rodar a
inferencia), nao por causa do sensor: ler o DHT22 leva 2 segundos e o
registro ocupa uns 100 bytes.

O QUE MUDA

1. `registro_imagem_id` passa a aceitar NULL. O UNIQUE continua, e
   continua valendo para quem tem foto: no Postgres, UNIQUE permite
   varios NULL, entao leituras sem foto nao colidem entre si.

2. Entra `device_id` na propria leitura. Antes o dispositivo era
   descoberto por JOIN com registros_imagem, e sem foto nao existe
   JOIN: a leitura ficaria orfa, invisivel para o escopo por dono de
   GET /leituras e para o filtro por campo do app.

   A coluna nasce nullable, e preenchida a partir de registros_imagem
   para todas as linhas existentes, e so depois vira NOT NULL. Criar
   NOT NULL direto falharia com a tabela populada, e um server_default
   mentiria sobre a origem das leituras antigas.

3. Entra `idempotency_key`, nullable e unica, pelo mesmo motivo que ela
   existe em registros_imagem: um reenvio depois de falha parcial (a API
   confirma, o processo do Pi cai antes de marcar como enviado) criaria
   uma linha duplicada, que contaria duas vezes no grafico e geraria o
   mesmo alerta ambiental duas vezes.

   Nullable porque as leituras que ja existem nasceram junto da foto e a
   chave delas esta em registros_imagem. Unica porque e exatamente a
   garantia que se quer, e no Postgres o UNIQUE aceita varios NULL.

4. Indice em (device_id, criado_em), que e exatamente como GET /leituras
   consulta: filtra por dispositivo e ordena por data.

REVERSAO

O downgrade recusa rodar se houver leitura sem foto, em vez de apagar
dado medido em campo para caber no schema antigo. Quem precisar reverter
decide o que fazer com essas linhas antes.

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

    # Backfill: toda leitura que existe hoje veio de uma captura, entao
    # o dispositivo dela e o da foto.
    op.execute(
        """
        UPDATE leituras_ambientais AS l
           SET device_id = r.device_id
          FROM registros_imagem AS r
         WHERE l.registro_imagem_id = r.id
        """
    )

    # Se sobrou alguma linha sem device_id, o NOT NULL abaixo falha e a
    # migration aborta inteira, que e o comportamento desejado: melhor
    # nao migrar do que gravar leitura sem dono, que ninguem veria.
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
