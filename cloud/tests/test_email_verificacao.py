"""
cloud/tests/test_email_verificacao.py

O que este arquivo verifica, em português simples:

CONFIRMAÇÃO DE CADASTRO
1. Com SMTP configurado, a conta nasce PENDENTE e um código é enviado.
2. O login é recusado enquanto o e-mail não for confirmado.
3. O código certo confirma a conta e libera o login.
4. Código errado, expirado ou com tentativas esgotadas é recusado, e
   sempre com a MESMA mensagem: diferenciar confirmaria que existe um
   pedido em andamento para aquele endereço.
5. Sem SMTP configurado, a conta nasce ATIVA. Criá-la bloqueada seria
   pior: o produtor ficaria preso numa conta que ninguém consegue
   confirmar, porque o e-mail nunca sairia.

RECUPERAÇÃO DE SENHA
6. A resposta é idêntica para e-mail cadastrado e inexistente, para não
   entregar quais endereços têm conta.
7. O código troca a senha de verdade, e a senha antiga para de valer.
8. A nova senha passa pelas mesmas regras de força do cadastro, senão a
   recuperação viraria um atalho para burlar essa exigência.

EM TODAS
9. O CÓDIGO NUNCA aparece na resposta da API. Se aparecesse, bastaria
   olhar a resposta no navegador para assumir a conta de qualquer um.
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
