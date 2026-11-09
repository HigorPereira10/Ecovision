"""
Modelos ORM (SQLAlchemy) do banco de dados. As migrações do Alembic
(cloud/alembic/) são derivadas destas classes.

registros_imagem.caminho_arquivo guarda o caminho dentro do bucket, e não
a URL, que é gerada sob demanda e expira. Os IDs são inteiros
autoincrementais, compatíveis com o PostgreSQL e com o SQLite dos testes.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class RegistroImagem(Base):
    """Uma captura recebida de um dispositivo."""

    __tablename__ = "registros_imagem"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # UUID gerado pela fila local do dispositivo; permite descartar
    # reenvios da mesma captura.
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
    """Leituras de temperatura e umidade do ar (DHT22) e de umidade do solo.

    `registro_imagem_id` é opcional: as leituras de 15 minutos chegam sem
    foto. A restrição UNIQUE garante no máximo uma leitura por captura
    (o PostgreSQL admite vários NULL). `device_id` pertence à própria
    leitura, para que leituras sem foto respeitem o escopo por dono. As
    medições são opcionais porque um sensor pode falhar sem interromper o
    ciclo."""

    __tablename__ = "leituras_ambientais"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Sem índice próprio: a migração 0008 cria o índice composto
    # (device_id, criado_em), usado por GET /leituras.
    device_id: Mapped[str] = mapped_column(String, nullable=False)
    registro_imagem_id: Mapped[int | None] = mapped_column(
        ForeignKey("registros_imagem.id"), nullable=True, unique=True
    )
    # Evita duplicar leituras reenviadas; nula nas leituras que chegam
    # junto da foto, cuja chave fica no registro de imagem.
    idempotency_key: Mapped[str | None] = mapped_column(
        String, nullable=True, unique=True
    )
    temperatura_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    umidade_ar_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    umidade_solo_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora_utc)

    registro_imagem: Mapped["RegistroImagem | None"] = relationship(back_populates="leitura")


class Diagnostico(Base):
    """Resultado da classificação de uma captura."""

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
    """Alertas gerados por diagnósticos ou por leituras fora da faixa."""

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
    # "alta" ou "media" (ver app/core/inference.py e alertas_ambientais.py).
    severidade: Mapped[str] = mapped_column(String, nullable=False)
    lido: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora_utc)


class Usuario(Base):
    """Contas de usuário (produtor ou administrador)."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String, nullable=False)
    papel: Mapped[str] = mapped_column(String, nullable=False)  # 'produtor' | 'administrador'

    # Enquanto False, o login é recusado: a conta só é liberada após a
    # confirmação do e-mail. Contas anteriores a esta coluna foram
    # marcadas como verificadas na migração.
    email_verificado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora_utc)


class Dispositivo(Base):
    """Dispositivo: vínculo com o produtor dono e credencial própria.

    `chave_hash` é o hash bcrypt do segredo do dispositivo. O
    `codigo_pareamento` só vale enquanto `usuario_id` for nulo, então um
    dispositivo já vinculado não pode ser reivindicado de novo."""

    __tablename__ = "dispositivos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    nome: Mapped[str | None] = mapped_column(String, nullable=True)
    chave_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    codigo_pareamento: Mapped[str | None] = mapped_column(
        String, nullable=True, unique=True, index=True
    )
    pareado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Metadados exibidos na tela de Perfil. `intervalo_captura_min`
    # espelha CAPTURE_INTERVAL_MINUTES do dispositivo e é definido no
    # provisionamento.
    campo: Mapped[str | None] = mapped_column(String, nullable=True)
    setor: Mapped[str | None] = mapped_column(String, nullable=True)
    intervalo_captura_min: Mapped[int | None] = mapped_column(Integer, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora_utc)


class TentativaLogin(Base):
    """Tentativas de login malsucedidas, para bloqueio por força bruta.

    A chave é o e-mail digitado, exista ou não a conta, para que o
    bloqueio não revele quais e-mails estão cadastrados."""

    __tablename__ = "tentativas_login"

    email: Mapped[str] = mapped_column(String, primary_key=True)
    tentativas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bloqueado_ate: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_agora_utc, onupdate=_agora_utc
    )


class CodigoEmail(Base):
    """Códigos de uso único enviados por e-mail (confirmação de cadastro e
    redefinição de senha).

    Guarda apenas o hash do código, que nunca volta na resposta da API.
    Com 6 dígitos, no máximo 5 tentativas e 15 minutos de validade, a
    chance de acerto por força bruta é de 5 em 1 milhão.
    """

    __tablename__ = "codigos_email"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # "verificacao" (confirmar cadastro) ou "recuperacao" (nova senha)
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    codigo_hash: Mapped[str] = mapped_column(String, nullable=False)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tentativas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    usado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora_utc)
