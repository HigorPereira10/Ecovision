"""
cloud/app/db/schemas.py

Schemas Pydantic usados para validação de entrada/saída dos endpoints
FastAPI (app/api/routes/*.py), separados dos modelos ORM (app/db/models.py)
por boa prática (não expor a estrutura de banco diretamente na API).

Relação com o resto do sistema:
- DiagnosticoOut: usado por app/api/routes/diagnostico.py.
- LoginRequest/TokenResponse/RefreshRequest: usados por
  app/api/routes/auth.py.
- LeituraOut: usado por app/api/routes/leituras.py.
- DiagnosticoHistoricoOut: usado por app/api/routes/diagnosticos.py.
- AlertaOut: usado por app/api/routes/alertas.py.
- UsuarioOut: usado por app/api/routes/usuarios.py.
- DispositivoOut: usado por app/api/routes/dispositivos.py.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DiagnosticoOut(BaseModel):
    """Resposta de POST /diagnostico. Espelha o mock
    app/src/mocks/diagnosticos.json do dashboard (campo "resultado" lá
    corresponde a classe_prevista aqui)."""

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

    Sem data de nascimento de propósito: o campo existia na primeira
    versão da tela de cadastro, mas nenhuma funcionalidade do sistema
    usa a idade do produtor, e a LGPD manda coletar só o indispensável
    para a finalidade declarada (princípio da necessidade). Guardar essa
    data criaria obrigação extra sem entregar nada.

    A validação de formato acontece em app/api/routes/auth.py, não aqui,
    para a resposta poder listar TODAS as regras de senha que falharam
    de uma vez, e não só a primeira."""

    nome: str
    email: str
    senha: str


class UsuarioCriadoOut(BaseModel):
    """Resposta de POST /auth/register. Não devolve token: o fluxo da
    tela é criar a conta e voltar para o login (ver CadastroScreen.tsx).
    Fazer login automático aqui obrigaria a emitir sessão para um email
    que ninguém confirmou."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str | None
    email: str


class VincularDispositivoRequest(BaseModel):
    """Corpo de POST /dispositivos/vincular. `codigo` é o que vem na
    etiqueta do aparelho, no formato ECO-XXXX-XXXX."""

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
    """Item de GET /leituras. Nomes de campo mantidos como no schema
    real (temperatura_c, umidade_ar_pct, umidade_solo_pct), diferente
    dos nomes antigos do mock do app/ (temperatura, umidade_ar,
    umidade_solo). A tradução entre os dois acontece no app, em
    app/src/services/leituras.ts, para as telas não precisarem mudar.

    As três medições são opcionais de propósito: quando um sensor falha,
    edge/src/main.py grava None naquele campo e segue o ciclo, para não
    perder a foto por causa de um sensor instável. O app precisa exibir
    isso como ausência de leitura, nunca como zero.

    `device_id` vem de registros_imagem (via join), não da própria
    leitura: o modelo liga leitura -> registro de imagem -> dispositivo.
    É usado pelo filtro por dispositivo da tela de Histórico do app.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    temperatura_c: float | None
    umidade_ar_pct: float | None
    umidade_solo_pct: float | None
    criado_em: datetime


class DiagnosticoHistoricoOut(BaseModel):
    """Item de GET /diagnosticos. `caminho_arquivo` é o caminho dentro
    do bucket do Supabase Storage (não uma URL, útil só para depuração).
    `url_imagem` é a signed URL pronta para exibir na tela (ver
    app/storage/supabase_storage.py e
    infra/supabase/storage_policies.md), válida por um tempo limitado;
    vem None se a geração da URL falhar (a lista não deve quebrar por
    causa de uma imagem)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    classe_prevista: str
    confianca: float
    recomendacao: str | None
    caminho_arquivo: str
    url_imagem: str | None = None
    criado_em: datetime


class AlertaOut(BaseModel):
    """Item de GET /alertas. `id` é None e `sintetico` é True para o
    alerta de dispositivo inativo (ADR 0008), que não corresponde a
    nenhuma linha real da tabela `alertas`: o frontend não deve tentar
    dar PATCH .../lido num item com sintetico=True."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None
    titulo: str
    descricao: str
    severidade: str
    lido: bool = False
    criado_em: datetime
    sintetico: bool = False


class UsuarioOut(BaseModel):
    """Resposta de GET /usuarios/me (tela de Perfil do app).

    `papel` é devolvido porque o app muda o que exibe conforme ele:
    hoje, o botão de notificação de demonstração na tela de Alertas só
    aparece para 'administrador'. Não é informação sensível (o próprio
    JWT do usuário já carrega esse campo assinado, ver
    app/core/security.py), e devolver aqui evita o app ter que decodificar
    o token por conta própria para descobrir algo que já é dele.

    `nome` é opcional porque a coluna nasceu nula na migration 0004,
    quando as contas existentes foram semeadas à mão sem esse dado.
    """

    model_config = ConfigDict(from_attributes=True)

    nome: str | None
    email: str
    papel: str


class DispositivoOut(BaseModel):
    """Item de GET /dispositivos. `status` ('ativo' | 'inativo') é
    computado sob demanda a partir da última captura recebida daquele
    device_id, reaproveitando app/core/alertas_dispositivo.py (ADR
    0008), não é uma coluna gravada no banco.

    `campo`, `setor` e `intervalo_captura_min` eram, até 2026-10-10,
    apenas enfeite no mock do app. Viraram colunas de verdade
    (migration 0006) para a tela de Perfil poder consumir a API real em
    vez de exibir um dispositivo inventado.

    Os `limiar_*` NÃO são configuráveis por dispositivo: são os valores
    que app/core/alertas_ambientais.py realmente usa para decidir se
    gera alerta. Vêm na resposta porque a tela os exibe, e mostrar o
    número verdadeiro é melhor do que mostrar um valor de enfeite que
    não controla nada.

    `limiar_umidade_solo` é o limite INFERIOR (solo seco), enquanto os
    outros dois são limites superiores. A assimetria é proposital: o
    card tem espaço para um valor por medição, e o número sobre o qual o
    produtor age, em estufa irrigada, é quase sempre o da seca. O limite
    superior (solo encharcado) continua existindo na lógica e gerando
    alerta, só não cabe nesta tela."""

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
