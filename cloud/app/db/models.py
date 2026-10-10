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
    # UUID gerado pelo edge/src/fila/offline_queue.py no momento da
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
    nome: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String, nullable=False)
    papel: Mapped[str] = mapped_column(String, nullable=False)  # 'produtor' | 'administrador'
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora_utc)


class Dispositivo(Base):
    """Vínculo device_id <-> produtor dono, listado por GET /dispositivos
    (app/api/routes/dispositivos.py), e também a credencial do próprio
    dispositivo.

    Esta tabela passou a ser parte da AUTENTICAÇÃO do Pi, e não só um
    cadastro. O ADR 0003 escolheu uma API Key estática e global com a
    justificativa explícita de que havia "1 único dispositivo"; essa
    premissa caiu quando o cadastro de produtores foi aberto. Com chave
    global, qualquer um que a tivesse poderia enviar captura se passando
    por QUALQUER device_id, ou seja, injetar diagnóstico falso na estufa
    de outro produtor.

    `chave_hash` é o hash bcrypt do segredo daquele Pi específico, nunca
    o segredo em claro: se o banco vazar, as credenciais não servem.

    `codigo_pareamento` é o que o agricultor digita no app para reivindicar
    o dispositivo. Ele só funciona enquanto `usuario_id` for nulo, então
    reivindicar um aparelho já vinculado é impossível, e o código perde
    o valor assim que é usado."""

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

    # Metadados que a tela de Perfil exibe. Existem no banco, e não como
    # texto fixo no app, porque são do aparelho: quem move a estufa de
    # setor precisa que isso mude para todo mundo, não só no celular que
    # editou. `intervalo_captura_min` espelha CAPTURE_INTERVAL_MINUTES do
    # .env do Pi; o backend não tem como descobrir sozinho, então é
    # preenchido no provisionamento.
    campo: Mapped[str | None] = mapped_column(String, nullable=True)
    setor: Mapped[str | None] = mapped_column(String, nullable=True)
    intervalo_captura_min: Mapped[int | None] = mapped_column(Integer, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora_utc)


class TentativaLogin(Base):
    """Contador de tentativas de login malsucedidas, para travar ataque
    de força bruta contra senha.

    A chave é o EMAIL DIGITADO, exista ou não uma conta com ele. Isso é
    proposital: app/api/routes/auth.py protege contra enumeração de
    usuários respondendo exatamente igual para email inexistente e senha
    errada. Se o bloqueio valesse só para contas reais, a própria
    resposta de "muitas tentativas" entregaria quais emails estão
    cadastrados, anulando aquela proteção. Contando por email digitado,
    qualquer endereço martelado recebe o mesmo tratamento.

    Por consequência, esta tabela acumula linhas de emails que nunca
    existiram. São poucos bytes cada e podem ser limpas periodicamente;
    não há informação sensível aqui, só o endereço tentado."""

    __tablename__ = "tentativas_login"

    email: Mapped[str] = mapped_column(String, primary_key=True)
    tentativas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bloqueado_ate: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_agora_utc, onupdate=_agora_utc
    )
