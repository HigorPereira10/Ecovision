"""
cloud/app/db/models.py

Modelos ORM (SQLAlchemy) que espelham o schema do Supabase Postgres.
Ver infra/supabase/schema.sql para a versão em SQL puro (mesma fonte de
verdade, gerada a partir daqui).

Escopo desta rodada (combinado com o grupo): só o caminho do
dispositivo. `registros_imagem`, `leituras_ambientais` e `diagnosticos`
são de fato gravadas por app/api/routes/diagnostico.py. `alertas`,
`usuarios` e `dispositivos` já têm o schema fechado (para o dashboard
não exigir migration nova depois), mas ficam vazias/não usadas até o
login do produtor (app/) ser implementado.

Decisão de design: `registros_imagem.caminho_arquivo` guarda só o
CAMINHO dentro do bucket (ex.: "pi-teste/2026-08-22T10-00-00.jpg"), não
a URL resolvida. A escolha entre signed URL e bucket público
(infra/supabase/storage_policies.md, ainda em aberto) fica para o lado
que LÊ a imagem depois, sem exigir uma nova migration quando essa
decisão for tomada.

IDs são inteiros autoincremento, não UUID. Isso é proposital: assim o
mesmo modelo funciona tanto no Postgres real do Supabase quanto no
SQLite usado nos testes (cloud/tests/).

Relação com o resto do sistema:
- Consumido por todos os endpoints em app/api/routes/*.py via
  app/db/session.py.
- As migrations (cloud/alembic/) são geradas a partir destas classes.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class RegistroImagem(Base):
    """Uma captura do Pi: uma foto + o dispositivo que a enviou."""

    __tablename__ = "registros_imagem"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # UUID gerado pelo edge/src/queue/offline_queue.py no momento da
    # captura. Usado por app/api/routes/diagnostico.py para detectar
    # reenvios (ex.: a API confirmou 200, mas o edge caiu antes de tirar
    # o item da fila local) e não duplicar o registro.
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    caminho_arquivo: Mapped[str] = mapped_column(String, nullable=False)
    capturado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora_utc)

    leitura: Mapped["LeituraAmbiental | None"] = relationship(
        back_populates="registro_imagem", uselist=False, cascade="all, delete-orphan"
    )
    diagnostico: Mapped["Diagnostico | None"] = relationship(
        back_populates="registro_imagem", uselist=False, cascade="all, delete-orphan"
    )


class LeituraAmbiental(Base):
    """Temperatura/umidade do ar (DHT22) e umidade do solo (ADS1115),
    associadas 1:1 a uma captura, já que o Pi manda os dois juntos no
    mesmo ciclo. Campos nullable porque edge/src/main.py já tolera
    falha de leitura de sensor sem abortar a captura da foto."""

    __tablename__ = "leituras_ambientais"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    registro_imagem_id: Mapped[int] = mapped_column(
        ForeignKey("registros_imagem.id"), nullable=False, unique=True
    )
    temperatura_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    umidade_ar_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    umidade_solo_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora_utc)

    registro_imagem: Mapped["RegistroImagem"] = relationship(back_populates="leitura")


class Diagnostico(Base):
    """Resultado da inferência TFLite para uma captura."""

    __tablename__ = "diagnosticos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    registro_imagem_id: Mapped[int] = mapped_column(
        ForeignKey("registros_imagem.id"), nullable=False, unique=True
    )
    classe_prevista: Mapped[str] = mapped_column(String, nullable=False)
    confianca: Mapped[float] = mapped_column(Float, nullable=False)
    recomendacao: Mapped[str | None] = mapped_column(String, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora_utc)

    registro_imagem: Mapped["RegistroImagem"] = relationship(back_populates="diagnostico")


class Alerta(Base):
    """Alertas derivados de diagnósticos e/ou leituras fora da faixa
    esperada. Schema pronto nesta rodada; a lógica que POPULA esta
    tabela é do dashboard (fora do escopo combinado agora)."""

    __tablename__ = "alertas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    diagnostico_id: Mapped[int | None] = mapped_column(
        ForeignKey("diagnosticos.id"), nullable=True
    )
    leitura_id: Mapped[int | None] = mapped_column(
        ForeignKey("leituras_ambientais.id"), nullable=True
    )
    titulo: Mapped[str] = mapped_column(String, nullable=False)
    descricao: Mapped[str] = mapped_column(String, nullable=False)
    # Valor 'alta' ou 'media'. Ver app/core/inference.py e
    # app/core/alertas_ambientais.py para a origem de cada valor.
    severidade: Mapped[str] = mapped_column(String, nullable=False)
    lido: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora_utc)


class Usuario(Base):
    """Login do dashboard (produtor/administrador). Schema pronto nesta
    rodada; sem uso até o login (JWT/bcrypt) ser implementado."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String, nullable=False)
    papel: Mapped[str] = mapped_column(String, nullable=False)  # 'produtor' | 'administrador'
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora_utc)


class Dispositivo(Base):
    """Vínculo device_id <-> produtor dono. Schema pronto nesta rodada;
    a autenticação do Pi continua sendo a API Key global (ADR 0003),
    não depende desta tabela ainda."""

    __tablename__ = "dispositivos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    nome: Mapped[str | None] = mapped_column(String, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora_utc)
