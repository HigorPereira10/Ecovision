"""
cloud/tests/test_cadastro_e_pareamento.py

O que este arquivo verifica, em português simples:

CADASTRO ABERTO (POST /auth/register)
1. Criar conta funciona, e dá para logar com ela em seguida.
2. O papel é sempre 'produtor', mesmo que alguém mande
   papel='administrador' no corpo: senão bastaria um JSON para ganhar
   acesso a todas as estufas.
3. Senha fraca é recusada com 422, listando TODAS as regras que
   falharam, e não só a primeira.
4. Senha acima de 72 bytes vira 422, não erro 500 (o bcrypt levanta
   ValueError nesse caso, e qualquer um poderia disparar isso).
5. E-mail duplicado vira 409, e é normalizado para minúsculas.

BLOQUEIO CONTRA FORÇA BRUTA
6. Cinco senhas erradas bloqueiam o e-mail por tempo.
7. E-mail que NEM EXISTE também é bloqueado: se só contas reais fossem
   bloqueadas, a resposta denunciaria quais e-mails estão cadastrados,
   anulando a proteção anti-enumeração do login.
8. Login bem-sucedido zera o contador.

PAREAMENTO (POST /dispositivos/vincular)
9. Conta nova não enxerga nada até vincular um aparelho.
10. Código válido vincula, e aí os dados aparecem.
11. Código inexistente dá 404; aparelho de outra conta dá 409.

CREDENCIAL POR DISPOSITIVO
12. O Pi autentica com o segredo dele.
13. Segredo errado, ou segredo de OUTRO aparelho, é recusado com 401.
"""

from datetime import datetime, timezone
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import gerar_hash_senha, gerar_segredo_dispositivo
from app.db.models import Dispositivo, RegistroImagem, Usuario
from app.db.session import engine
from app.main import app

SENHA_BOA = "Tomate@2026"


def _registrar(client: TestClient, email: str, senha: str = SENHA_BOA, nome: str = "Maria da Silva"):
    return client.post("/auth/register", json={"nome": nome, "email": email, "senha": senha})


def _logar(client: TestClient, email: str, senha: str):
    return client.post("/auth/login", json={"email": email, "senha": senha})


# ------------------------------------------------------------ cadastro

async def test_cadastro_cria_conta_e_permite_login():
    with TestClient(app) as client:
        resposta = _registrar(client, "maria@exemplo.com")
        assert resposta.status_code == 201, resposta.text
        assert resposta.json()["email"] == "maria@exemplo.com"

        login = _logar(client, "maria@exemplo.com", SENHA_BOA)
        assert login.status_code == 200
        assert "access_token" in login.json()


async def test_cadastro_ignora_papel_enviado_e_força_produtor():
    """Sem isso, bastaria mandar papel='administrador' no JSON para
    enxergar as estufas de todos os produtores."""
    with TestClient(app) as client:
        resposta = client.post(
            "/auth/register",
            json={
                "nome": "Intruso Silva",
                "email": "intruso@exemplo.com",
                "senha": SENHA_BOA,
                "papel": "administrador",
            },
        )
        assert resposta.status_code == 201

    async with AsyncSession(engine) as sessao:
        usuario = await sessao.get(Usuario, resposta.json()["id"])
        assert usuario.papel == "produtor"


async def test_cadastro_recusa_senha_fraca_listando_todas_as_regras():
    with TestClient(app) as client:
        resposta = _registrar(client, "fraca@exemplo.com", senha="abc")

    assert resposta.status_code == 422
    problemas = resposta.json()["detail"]
    assert any("8 caracteres" in p for p in problemas)
    assert any("maiúscula" in p for p in problemas)
    assert any("número" in p for p in problemas)
    assert any("símbolo" in p for p in problemas)


async def test_cadastro_com_senha_acima_do_limite_do_bcrypt_devolve_422():
    """Regressão: o bcrypt recusa mais de 72 BYTES levantando ValueError.
    Sem tratar, o cadastro virava erro 500 que qualquer um podia
    disparar sem autenticação."""
    senha_gigante = "A1@" + ("ç" * 40)  # acentos gastam 2 bytes cada
    with TestClient(app) as client:
        resposta = _registrar(client, "gigante@exemplo.com", senha=senha_gigante)

    assert resposta.status_code == 422
    assert any("72 bytes" in p for p in resposta.json()["detail"])


async def test_cadastro_normaliza_email_e_recusa_duplicado():
    with TestClient(app) as client:
        primeira = _registrar(client, "  Maria@Exemplo.COM  ")
        assert primeira.status_code == 201
        assert primeira.json()["email"] == "maria@exemplo.com"

        segunda = _registrar(client, "maria@exemplo.com")
        assert segunda.status_code == 409

        # e o login funciona com qualquer caixa
        assert _logar(client, "MARIA@exemplo.com", SENHA_BOA).status_code == 200


async def test_cadastro_exige_nome_e_sobrenome():
    with TestClient(app) as client:
        resposta = _registrar(client, "so.nome@exemplo.com", nome="Maria")
    assert resposta.status_code == 422
    assert any("sobrenome" in p for p in resposta.json()["detail"])


# ------------------------------------------------- bloqueio forca bruta

async def test_cinco_senhas_erradas_bloqueiam_o_email():
    with TestClient(app) as client:
        _registrar(client, "alvo@exemplo.com")

        for _ in range(5):
            assert _logar(client, "alvo@exemplo.com", "ErradaX@1").status_code == 401

        # a 6a nao chega nem a verificar a senha
        bloqueada = _logar(client, "alvo@exemplo.com", "ErradaX@1")
        assert bloqueada.status_code == 429
        assert "minuto" in bloqueada.json()["detail"]

        # e a senha CERTA tambem fica bloqueada enquanto durar
        assert _logar(client, "alvo@exemplo.com", SENHA_BOA).status_code == 429


async def test_email_inexistente_tambem_e_bloqueado():
    """Anti-enumeração: se o bloqueio valesse só para contas reais, a
    resposta 429 entregaria quais e-mails estão cadastrados."""
    with TestClient(app) as client:
        for _ in range(5):
            assert _logar(client, "fantasma@exemplo.com", "QualquerX@1").status_code == 401

        resposta = _logar(client, "fantasma@exemplo.com", "QualquerX@1")
        assert resposta.status_code == 429


async def test_login_correto_zera_o_contador():
    with TestClient(app) as client:
        _registrar(client, "paciente@exemplo.com")

        for _ in range(4):
            _logar(client, "paciente@exemplo.com", "ErradaX@1")

        assert _logar(client, "paciente@exemplo.com", SENHA_BOA).status_code == 200

        # contador zerado: mais 4 erros ainda nao bloqueiam
        for _ in range(4):
            assert _logar(client, "paciente@exemplo.com", "ErradaX@1").status_code == 401


# ------------------------------------------------------------ pareamento

async def _criar_dispositivo_sem_dono(device_id: str, codigo: str, segredo: str | None = None):
    """Simula o que scripts/provisionar_dispositivo.py faz: cria o
    aparelho SEM dono, com código de pareamento e credencial própria."""
    async with AsyncSession(engine) as sessao:
        sessao.add(
            Dispositivo(
                device_id=device_id,
                nome=f"Estufa {device_id}",
                codigo_pareamento=codigo,
                chave_hash=gerar_hash_senha(segredo) if segredo else None,
            )
        )
        await sessao.commit()


async def _registrar_captura(device_id: str):
    async with AsyncSession(engine) as sessao:
        sessao.add(
            RegistroImagem(
                device_id=device_id,
                idempotency_key=f"captura-{device_id}",
                caminho_arquivo=f"{device_id}/foto.jpg",
                capturado_em=datetime.now(timezone.utc),
            )
        )
        await sessao.commit()


async def test_conta_nova_nao_ve_nada_ate_vincular_um_aparelho():
    await _criar_dispositivo_sem_dono("pi-do-vizinho", "ECO-AAAA-BBBB")
    await _registrar_captura("pi-do-vizinho")

    with TestClient(app) as client:
        _registrar(client, "novata@exemplo.com")
        token = _logar(client, "novata@exemplo.com", SENHA_BOA).json()["access_token"]
        cab = {"Authorization": f"Bearer {token}"}

        assert client.get("/dispositivos", headers=cab).json() == []
        assert client.get("/leituras", headers=cab).json() == []
        assert client.get("/diagnosticos", headers=cab).json() == []


async def test_codigo_valido_vincula_e_os_dados_aparecem():
    await _criar_dispositivo_sem_dono("pi-da-novata", "ECO-CCCC-DDDD")
    await _registrar_captura("pi-da-novata")

    with TestClient(app) as client:
        _registrar(client, "dona@exemplo.com")
        token = _logar(client, "dona@exemplo.com", SENHA_BOA).json()["access_token"]
        cab = {"Authorization": f"Bearer {token}"}

        assert client.get("/dispositivos", headers=cab).json() == []

        vinculo = client.post(
            "/dispositivos/vincular", json={"codigo": "eco-cccc-dddd"}, headers=cab
        )
        assert vinculo.status_code == 200, vinculo.text
        assert vinculo.json()["device_id"] == "pi-da-novata"

        depois = client.get("/dispositivos", headers=cab).json()
        assert [d["device_id"] for d in depois] == ["pi-da-novata"]


async def test_codigo_inexistente_devolve_404():
    with TestClient(app) as client:
        _registrar(client, "perdida@exemplo.com")
        token = _logar(client, "perdida@exemplo.com", SENHA_BOA).json()["access_token"]
        resposta = client.post(
            "/dispositivos/vincular",
            json={"codigo": "ECO-ZZZZ-9999"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resposta.status_code == 404


async def test_aparelho_ja_vinculado_a_outra_conta_devolve_409():
    """Quem viu a etiqueta de um aparelho alheio não consegue tomá-lo."""
    await _criar_dispositivo_sem_dono("pi-disputado", "ECO-EEEE-FFFF")

    with TestClient(app) as client:
        _registrar(client, "primeira@exemplo.com")
        t1 = _logar(client, "primeira@exemplo.com", SENHA_BOA).json()["access_token"]
        primeira = client.post(
            "/dispositivos/vincular",
            json={"codigo": "ECO-EEEE-FFFF"},
            headers={"Authorization": f"Bearer {t1}"},
        )
        assert primeira.status_code == 200

        _registrar(client, "segunda@exemplo.com")
        t2 = _logar(client, "segunda@exemplo.com", SENHA_BOA).json()["access_token"]
        segunda = client.post(
            "/dispositivos/vincular",
            json={"codigo": "ECO-EEEE-FFFF"},
            headers={"Authorization": f"Bearer {t2}"},
        )
        assert segunda.status_code == 409


# --------------------------------------------------- credencial do Pi

def _imagem_falsa() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (64, 64), color=(90, 140, 70)).save(buffer, format="JPEG")
    return buffer.getvalue()


async def _salvar_imagem_falso(*args, **kwargs) -> str:
    return "pi-credencial/foto.jpg"


def _enviar(client: TestClient, device_id: str, credencial: str, chave_idem: str):
    return client.post(
        "/diagnostico",
        data={
            "device_id": device_id,
            "timestamp": "2026-10-10T10:00:00+00:00",
            "idempotency_key": chave_idem,
        },
        files={"imagem": ("foto.jpg", BytesIO(_imagem_falsa()), "image/jpeg")},
        headers={"Authorization": credencial},
    )


async def test_pi_autentica_com_o_segredo_proprio(monkeypatch):
    monkeypatch.setattr("app.api.routes.diagnostico.salvar_imagem", _salvar_imagem_falso)
    segredo = gerar_segredo_dispositivo()
    await _criar_dispositivo_sem_dono("pi-credencial", "ECO-GGGG-HHHH", segredo)

    with TestClient(app) as client:
        resposta = _enviar(client, "pi-credencial", segredo, "cap-ok")

    assert resposta.status_code == 200, resposta.text


async def test_segredo_errado_e_recusado(monkeypatch):
    monkeypatch.setattr("app.api.routes.diagnostico.salvar_imagem", _salvar_imagem_falso)
    await _criar_dispositivo_sem_dono("pi-credencial", "ECO-IIII-JJJJ", gerar_segredo_dispositivo())

    with TestClient(app) as client:
        resposta = _enviar(client, "pi-credencial", "segredo-inventado", "cap-ruim")

    assert resposta.status_code == 401


async def test_segredo_de_outro_aparelho_nao_serve(monkeypatch):
    """O ponto central da mudança: antes, com chave global, qualquer Pi
    podia enviar captura se passando por qualquer device_id."""
    monkeypatch.setattr("app.api.routes.diagnostico.salvar_imagem", _salvar_imagem_falso)
    segredo_a = gerar_segredo_dispositivo()
    await _criar_dispositivo_sem_dono("pi-aaa", "ECO-KKKK-LLLL", segredo_a)
    await _criar_dispositivo_sem_dono("pi-bbb", "ECO-MMMM-NNNN", gerar_segredo_dispositivo())

    with TestClient(app) as client:
        # tenta postar COMO pi-bbb usando o segredo do pi-aaa
        resposta = _enviar(client, "pi-bbb", segredo_a, "cap-cruzada")

    assert resposta.status_code == 401


async def test_produtor_sem_dispositivo_nao_recebe_alerta_de_inatividade():
    """Regressão: o alerta sintético de 'dispositivo nunca reportou
    dados' era gerado mesmo para quem não tem aparelho nenhum. Quem
    acabava de se cadastrar via uma instrução para verificar a
    alimentação e o Wi-Fi de um Raspberry Pi que não existe."""
    with TestClient(app) as client:
        _registrar(client, "semaparelho@exemplo.com")
        token = _logar(client, "semaparelho@exemplo.com", SENHA_BOA).json()["access_token"]
        alertas = client.get(
            "/alertas", headers={"Authorization": f"Bearer {token}"}
        ).json()

    assert alertas == [], f"produtor sem dispositivo recebeu {alertas}"
