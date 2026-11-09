"""
Testes de confirmação de cadastro e recuperação de senha.

Confirmação:
1. com envio configurado, a conta nasce pendente e recebe um código;
2. o login é recusado até a confirmação;
3. o código correto confirma a conta;
4. código errado, expirado ou esgotado é recusado com a mesma mensagem;
5. sem envio configurado, a conta nasce ativa.

Recuperação:
6. resposta idêntica para e-mail cadastrado e inexistente;
7. o código troca a senha e a antiga deixa de valer;
8. a nova senha segue as regras do cadastro.

Em todas, o código nunca aparece na resposta da API.
"""

import re
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CodigoEmail, Usuario
from app.db.session import engine
from app.main import app

SENHA_BOA = "Tomate@2026"
SENHA_NOVA = "Alface#2027"


@pytest.fixture
def smtp_ligado(monkeypatch):
    """Simula SMTP configurado e captura o que seria enviado, em vez de
    mandar e-mail de verdade."""
    enviados: list[dict] = []

    def _enviar_falso(destinatario: str, assunto: str, corpo: str) -> bool:
        enviados.append({"para": destinatario, "assunto": assunto, "corpo": corpo})
        return True

    monkeypatch.setattr("app.config.settings.SMTP_HOST", "smtp.teste")
    monkeypatch.setattr("app.config.settings.SMTP_USUARIO", "robo@teste")
    monkeypatch.setattr("app.config.settings.SMTP_SENHA", "segredo")
    monkeypatch.setattr("app.api.routes.auth.emails.enviar", _enviar_falso)
    return enviados


def _codigo_do_email(enviados: list[dict]) -> str:
    """Extrai os 6 dígitos do corpo do último e-mail capturado."""
    assert enviados, "nenhum e-mail foi enviado"
    achado = re.search(r"\b(\d{6})\b", enviados[-1]["corpo"])
    assert achado, f"nenhum código no corpo: {enviados[-1]['corpo'][:200]}"
    return achado.group(1)


def _registrar(client: TestClient, email: str, senha: str = SENHA_BOA):
    return client.post(
        "/auth/register", json={"nome": "Maria da Silva", "email": email, "senha": senha}
    )


def _logar(client: TestClient, email: str, senha: str):
    return client.post("/auth/login", json={"email": email, "senha": senha})


# ------------------------------------------------ confirmação de cadastro

async def test_cadastro_nasce_pendente_e_envia_codigo(smtp_ligado):
    with TestClient(app) as client:
        resposta = _registrar(client, "nova@exemplo.com")

    assert resposta.status_code == 201
    assert resposta.json()["email_verificado"] is False
    assert len(smtp_ligado) == 1
    assert smtp_ligado[0]["para"] == "nova@exemplo.com"
    assert len(_codigo_do_email(smtp_ligado)) == 6


async def test_codigo_nunca_aparece_na_resposta_da_api(smtp_ligado):
    """A proteção central: se o código voltasse aqui, bastaria olhar a
    resposta para ativar (ou assumir) a conta de qualquer pessoa."""
    with TestClient(app) as client:
        resposta = _registrar(client, "sigilo@exemplo.com")
        codigo = _codigo_do_email(smtp_ligado)
        assert codigo not in resposta.text

        pedido = client.post("/auth/forgot-password", json={"email": "sigilo@exemplo.com"})
        assert _codigo_do_email(smtp_ligado) not in pedido.text


async def test_login_recusado_enquanto_email_nao_confirmado(smtp_ligado):
    with TestClient(app) as client:
        _registrar(client, "pendente@exemplo.com")
        resposta = _logar(client, "pendente@exemplo.com", SENHA_BOA)

    assert resposta.status_code == 403
    assert "Confirme seu e-mail" in resposta.json()["detail"]


async def test_codigo_certo_confirma_e_libera_o_login(smtp_ligado):
    with TestClient(app) as client:
        _registrar(client, "confirma@exemplo.com")
        codigo = _codigo_do_email(smtp_ligado)

        verificacao = client.post(
            "/auth/verify-email", json={"email": "confirma@exemplo.com", "codigo": codigo}
        )
        assert verificacao.status_code == 200

        login = _logar(client, "confirma@exemplo.com", SENHA_BOA)
        assert login.status_code == 200
        assert "access_token" in login.json()


async def test_codigo_errado_é_recusado(smtp_ligado):
    with TestClient(app) as client:
        _registrar(client, "errado@exemplo.com")
        resposta = client.post(
            "/auth/verify-email", json={"email": "errado@exemplo.com", "codigo": "000000"}
        )

    assert resposta.status_code == 400
    assert "inválido ou expirado" in resposta.json()["detail"]


async def test_codigo_expirado_é_recusado(smtp_ligado):
    with TestClient(app) as client:
        _registrar(client, "expirado@exemplo.com")
        codigo = _codigo_do_email(smtp_ligado)

    # empurra a expiração para o passado
    async with AsyncSession(engine) as sessao:
        registro = await sessao.scalar(
            select(CodigoEmail).where(CodigoEmail.email == "expirado@exemplo.com")
        )
        registro.expira_em = datetime.now(timezone.utc) - timedelta(minutes=1)
        await sessao.commit()

    with TestClient(app) as client:
        resposta = client.post(
            "/auth/verify-email", json={"email": "expirado@exemplo.com", "codigo": codigo}
        )

    assert resposta.status_code == 400


async def test_cinco_erros_esgotam_o_codigo_mesmo_com_o_certo_depois(smtp_ligado):
    """O código tem 6 dígitos, ou seja, um milhão de combinações. Sem
    limitar tentativas, dava para testar todas."""
    with TestClient(app) as client:
        _registrar(client, "forca@exemplo.com")
        codigo = _codigo_do_email(smtp_ligado)

        for _ in range(5):
            client.post(
                "/auth/verify-email", json={"email": "forca@exemplo.com", "codigo": "000000"}
            )

        resposta = client.post(
            "/auth/verify-email", json={"email": "forca@exemplo.com", "codigo": codigo}
        )

    assert resposta.status_code == 400


async def test_sem_smtp_a_conta_nasce_ativa():
    """Degradação proposital: sem e-mail configurado, exigir confirmação
    deixaria o produtor preso numa conta que ninguém consegue ativar."""
    with TestClient(app) as client:
        resposta = _registrar(client, "semsmtp@exemplo.com")
        assert resposta.status_code == 201
        assert resposta.json()["email_verificado"] is True

        assert _logar(client, "semsmtp@exemplo.com", SENHA_BOA).status_code == 200


# -------------------------------------------------- recuperação de senha

async def test_resposta_identica_para_email_existente_e_inexistente(smtp_ligado):
    with TestClient(app) as client:
        _registrar(client, "existe@exemplo.com")
        smtp_ligado.clear()

        com_conta = client.post("/auth/forgot-password", json={"email": "existe@exemplo.com"})
        sem_conta = client.post("/auth/forgot-password", json={"email": "fantasma@exemplo.com"})

    assert com_conta.status_code == sem_conta.status_code == 200
    assert com_conta.json() == sem_conta.json()
    # e só um e-mail saiu de verdade, o da conta que existe
    assert len(smtp_ligado) == 1


async def test_recuperacao_troca_a_senha_e_invalida_a_antiga(smtp_ligado):
    with TestClient(app) as client:
        _registrar(client, "troca@exemplo.com")
        codigo_verificacao = _codigo_do_email(smtp_ligado)
        client.post(
            "/auth/verify-email",
            json={"email": "troca@exemplo.com", "codigo": codigo_verificacao},
        )

        client.post("/auth/forgot-password", json={"email": "troca@exemplo.com"})
        codigo = _codigo_do_email(smtp_ligado)

        troca = client.post(
            "/auth/reset-password",
            json={"email": "troca@exemplo.com", "codigo": codigo, "nova_senha": SENHA_NOVA},
        )
        assert troca.status_code == 200

        assert _logar(client, "troca@exemplo.com", SENHA_NOVA).status_code == 200
        assert _logar(client, "troca@exemplo.com", SENHA_BOA).status_code == 401


async def test_recuperacao_exige_senha_forte(smtp_ligado):
    """Senão a recuperação viraria um atalho para contornar as regras de
    senha que o cadastro exige."""
    with TestClient(app) as client:
        _registrar(client, "fraca@exemplo.com")
        client.post("/auth/forgot-password", json={"email": "fraca@exemplo.com"})
        codigo = _codigo_do_email(smtp_ligado)

        resposta = client.post(
            "/auth/reset-password",
            json={"email": "fraca@exemplo.com", "codigo": codigo, "nova_senha": "123"},
        )

    assert resposta.status_code == 422
    assert any("8 caracteres" in p for p in resposta.json()["detail"])


async def test_codigo_de_recuperacao_so_vale_uma_vez(smtp_ligado):
    with TestClient(app) as client:
        _registrar(client, "umavez@exemplo.com")
        client.post("/auth/forgot-password", json={"email": "umavez@exemplo.com"})
        codigo = _codigo_do_email(smtp_ligado)

        corpo = {"email": "umavez@exemplo.com", "codigo": codigo, "nova_senha": SENHA_NOVA}
        assert client.post("/auth/reset-password", json=corpo).status_code == 200
        assert client.post("/auth/reset-password", json=corpo).status_code == 400


async def test_pedir_codigo_novo_invalida_o_anterior(smtp_ligado):
    """Um código vazado não pode continuar valendo depois de a pessoa
    pedir outro."""
    with TestClient(app) as client:
        _registrar(client, "renova@exemplo.com")
        client.post("/auth/forgot-password", json={"email": "renova@exemplo.com"})
        primeiro = _codigo_do_email(smtp_ligado)

        client.post("/auth/forgot-password", json={"email": "renova@exemplo.com"})
        segundo = _codigo_do_email(smtp_ligado)
        assert primeiro != segundo

        antigo = client.post(
            "/auth/reset-password",
            json={"email": "renova@exemplo.com", "codigo": primeiro, "nova_senha": SENHA_NOVA},
        )
        assert antigo.status_code == 400

        novo = client.post(
            "/auth/reset-password",
            json={"email": "renova@exemplo.com", "codigo": segundo, "nova_senha": SENHA_NOVA},
        )
        assert novo.status_code == 200


async def test_codigo_fica_guardado_como_hash_e_nao_em_claro(smtp_ligado):
    """Se o banco vazar, ninguém pode assumir uma conta com o que
    estiver lá."""
    with TestClient(app) as client:
        _registrar(client, "hash@exemplo.com")
        codigo = _codigo_do_email(smtp_ligado)

    async with AsyncSession(engine) as sessao:
        registro = await sessao.scalar(
            select(CodigoEmail).where(CodigoEmail.email == "hash@exemplo.com")
        )

    assert registro.codigo_hash != codigo
    assert codigo not in registro.codigo_hash
    assert registro.codigo_hash.startswith("$2b$"), "esperado hash bcrypt"


# ------------------------------------------------------- reenvio de código

async def test_reenvio_manda_codigo_novo_e_invalida_o_antigo(smtp_ligado, monkeypatch):
    """Uma conta pendente pode pedir novo código."""
    # O intervalo mínimo é desativado para o teste não esperar 60 s.
    monkeypatch.setattr("app.api.routes.auth._INTERVALO_REENVIO", timedelta(seconds=0))

    with TestClient(app) as client:
        _registrar(client, "reenvio@exemplo.com")
        primeiro = _codigo_do_email(smtp_ligado)

        resposta = client.post("/auth/resend-code", json={"email": "reenvio@exemplo.com"})
        assert resposta.status_code == 200
        segundo = _codigo_do_email(smtp_ligado)
        assert primeiro != segundo
        assert segundo not in resposta.text

        # Vale o último: o código do primeiro e-mail morreu.
        antigo = client.post(
            "/auth/verify-email", json={"email": "reenvio@exemplo.com", "codigo": primeiro}
        )
        assert antigo.status_code == 400

        novo = client.post(
            "/auth/verify-email", json={"email": "reenvio@exemplo.com", "codigo": segundo}
        )
        assert novo.status_code == 200
        assert _logar(client, "reenvio@exemplo.com", SENHA_BOA).status_code == 200


async def test_reenvio_responde_igual_para_conta_inexistente_e_ja_confirmada(smtp_ligado):
    """Senão esta rota viraria um detector de quais e-mails têm conta e
    quais ainda estão pendentes de confirmação."""
    with TestClient(app) as client:
        _registrar(client, "ativa@exemplo.com")
        codigo = _codigo_do_email(smtp_ligado)
        client.post("/auth/verify-email", json={"email": "ativa@exemplo.com", "codigo": codigo})
        smtp_ligado.clear()

        confirmada = client.post("/auth/resend-code", json={"email": "ativa@exemplo.com"})
        inexistente = client.post("/auth/resend-code", json={"email": "ninguem@exemplo.com"})

    assert confirmada.status_code == inexistente.status_code == 200
    assert confirmada.json() == inexistente.json()
    # E nenhum dos dois casos gastou e-mail.
    assert smtp_ligado == []


async def test_reenvio_respeita_intervalo_minimo(smtp_ligado):
    """Reenvios respeitam o intervalo mínimo, que protege a cota diária de
    e-mails. O próprio cadastro conta como primeiro envio."""
    with TestClient(app) as client:
        _registrar(client, "flood@exemplo.com")
        assert len(smtp_ligado) == 1  # o e-mail do cadastro

        bloqueada = client.post("/auth/resend-code", json={"email": "flood@exemplo.com"})
        assert bloqueada.status_code == 200
        assert len(smtp_ligado) == 1, "reenvio dentro do intervalo nao pode gastar e-mail"

    # Envelhece o último código para além do intervalo, simulando o
    # produtor que esperou antes de tocar em "não recebi o código".
    async with AsyncSession(engine) as sessao:
        registro = await sessao.scalar(
            select(CodigoEmail)
            .where(CodigoEmail.email == "flood@exemplo.com")
            .order_by(CodigoEmail.id.desc())
        )
        registro.criado_em = datetime.now(timezone.utc) - timedelta(minutes=2)
        await sessao.commit()

    with TestClient(app) as client:
        liberada = client.post("/auth/resend-code", json={"email": "flood@exemplo.com"})

    assert liberada.status_code == 200
    # A resposta é idêntica nos dois casos: a trava nunca é anunciada.
    assert liberada.json() == bloqueada.json()
    assert len(smtp_ligado) == 2, "passado o intervalo, o reenvio tem de sair"
