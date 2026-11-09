"""
Schemas Pydantic de entrada e saída das rotas, separados dos modelos ORM
para não expor a estrutura do banco na API.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DiagnosticoOut(BaseModel):
    """Resposta de POST /diagnostico, devolvida ao dispositivo.

    `classe_prevista` é uma classe do modelo ou um dos valores especiais
    "indisponivel" (modelo não carregado) e "imagem_inadequada" (foto
    reprovada na verificação de qualidade). Nos dois casos `confianca` é
    0.0; em "imagem_inadequada", `recomendacao` traz o motivo."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    classe_prevista: str
    confianca: float
    recomendacao: str | None


class LoginRequest(BaseModel):
    """Corpo de POST /auth/login."""

    email: str
    senha: str


class RegistroRequest(BaseModel):
    """Corpo de POST /auth/register.

    Coleta apenas os dados necessários (nome, e-mail e senha). As regras
    de senha são validadas em app/api/routes/auth.py, para que a resposta
    liste todas as regras não cumpridas de uma vez."""

    nome: str
    email: str
    senha: str


class UsuarioCriadoOut(BaseModel):
    """Resposta de POST /auth/register. Não devolve token: a sessão só é
    emitida após a confirmação do e-mail."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str | None
    email: str
    # False quando não há envio de e-mail configurado e a conta já nasce
    # ativa; o aplicativo decide se abre a tela de código ou o login.
    email_verificado: bool


class VerificarEmailRequest(BaseModel):
    """Corpo de POST /auth/verify-email."""

    email: str
    codigo: str


class EsqueciSenhaRequest(BaseModel):
    """Corpo de POST /auth/forgot-password."""

    email: str


class ReenviarCodigoRequest(BaseModel):
    """Corpo de POST /auth/resend-code: novo código de confirmação para
    uma conta ainda não confirmada."""

    email: str


class RedefinirSenhaRequest(BaseModel):
    """Corpo de POST /auth/reset-password."""

    email: str
    codigo: str
    nova_senha: str


class MensagemOut(BaseModel):
    """Resposta genérica das rotas de e-mail: não devolve o código nem
    indica se a conta existe."""

    mensagem: str


class VincularDispositivoRequest(BaseModel):
    """Corpo de POST /dispositivos/vincular; `codigo` no formato
    ECO-XXXX-XXXX."""

    codigo: str


class RefreshRequest(BaseModel):
    """Corpo de POST /auth/refresh."""

    refresh_token: str


class TokenResponse(BaseModel):
    """Resposta de POST /auth/login e POST /auth/refresh."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class LeituraOut(BaseModel):
    """Item de GET /leituras.

    As medições são opcionais: um sensor com falha gera campo nulo, que o
    aplicativo exibe como ausência de leitura, nunca como zero.
    `tem_foto` indica se a leitura veio de um ciclo de captura.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    temperatura_c: float | None
    umidade_ar_pct: float | None
    umidade_solo_pct: float | None
    tem_foto: bool
    criado_em: datetime


class LeituraDispositivoIn(BaseModel):
    """Corpo de POST /leituras, o ciclo de leitura sem foto (JSON).

    As medições são opcionais; uma requisição com as três nulas é aceita,
    pois indica que o ciclo ocorreu sem resposta dos sensores.
    `idempotency_key` evita duplicidade em reenvios.
    """

    device_id: str
    idempotency_key: str
    temperatura_c: float | None = None
    umidade_ar_pct: float | None = None
    umidade_solo_pct: float | None = None


class DiagnosticoHistoricoOut(BaseModel):
    """Item de GET /diagnosticos.

    `caminho_arquivo` é o caminho no bucket; `url_imagem` é a URL assinada
    para exibição, com validade limitada, ou None se não puder ser gerada.
    `device_id` vem do registro de imagem classificado. `classe_prevista`
    é o nome técnico da classe; a tradução para texto fica no aplicativo
    (app/src/domain/doencas.ts)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    classe_prevista: str
    confianca: float
    recomendacao: str | None
    caminho_arquivo: str
    url_imagem: str | None = None
    criado_em: datetime


class AlertaOut(BaseModel):
    """Item de GET /alertas. Para o alerta sintético de dispositivo
    inativo, `id` é None e `sintetico` é True; ele não pode ser marcado
    como lido."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None
    titulo: str
    descricao: str
    severidade: str
    lido: bool = False
    criado_em: datetime
    sintetico: bool = False


class UsuarioOut(BaseModel):
    """Resposta de GET /usuarios/me.

    `papel` permite ao aplicativo ajustar a interface (o mesmo valor já
    consta no token). `nome` é opcional para contas antigas.
    """

    model_config = ConfigDict(from_attributes=True)

    nome: str | None
    email: str
    papel: str


class DispositivoOut(BaseModel):
    """Item de GET /dispositivos.

    `status` ("ativo" ou "inativo") é calculado a partir da última captura
    (app/core/alertas_dispositivo.py). Os campos `limiar_*` são os valores
    usados por app/core/alertas_ambientais.py, exibidos na tela de Perfil;
    `limiar_umidade_solo` é o limite inferior (solo seco), e os demais são
    limites superiores."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    nome: str | None
    status: str
    criado_em: datetime

    campo: str | None
    setor: str | None
    intervalo_captura_min: int | None

    limiar_temperatura: float
    limiar_umidade_ar: float
    limiar_umidade_solo: float
