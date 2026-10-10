"""
cloud/tests/test_security.py

O que este arquivo verifica, em português simples:

Parte 1 (dispositivo IoT): a Raspberry Pi só pode falar com a API se
mandar a "senha" certa (a API Key) no cabeçalho da requisição. Este
teste confere as três situações possíveis: chave certa (deixa passar),
chave errada (barra com 401) e chave ausente (também barra com 401).
Sem isso, qualquer um na internet poderia mandar fotos falsas para o
sistema.

Parte 2 (dashboard): as peças de autenticação do produtor (ADR 0003)
usadas por app/api/routes/auth.py e como dependency dos demais
endpoints do dashboard: gerar/verificar hash de senha, gerar tokens de
acesso e refresh, e recusar um token errado (expirado, tipo trocado,
sem o prefixo "Bearer", assinado com outra chave).
"""

import time
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from app.config import settings
from app.core.security import (
    criar_access_token,
    criar_refresh_token,
    decodificar_token,
    gerar_hash_senha,
    obter_produtor_atual,
    validar_api_key_dispositivo,
    verificar_senha,
)


def test_chave_correta_nao_levanta_erro():
    validar_api_key_dispositivo(authorization=settings.DEVICE_API_KEY)


def test_chave_incorreta_levanta_401():
    with pytest.raises(HTTPException) as excinfo:
        validar_api_key_dispositivo(authorization="chave-errada")
    assert excinfo.value.status_code == 401


def test_chave_ausente_levanta_401():
    with pytest.raises(HTTPException) as excinfo:
        validar_api_key_dispositivo(authorization=None)
    assert excinfo.value.status_code == 401


def test_hash_de_senha_verifica_corretamente():
    hash_gerado = gerar_hash_senha("tomate123")
    assert verificar_senha("tomate123", hash_gerado) is True
    assert verificar_senha("senha-errada", hash_gerado) is False


def test_access_token_decodifica_com_os_dados_certos():
    token = criar_access_token(usuario_id=7, papel="produtor")
    payload = decodificar_token(token, tipo_esperado="access")
    assert payload["sub"] == "7"
    assert payload["papel"] == "produtor"


def test_refresh_token_nao_passa_como_access_token():
    """Um refresh token NUNCA deve funcionar como access token: são
    tokens de vida útil bem diferente (30 dias vs 24h), então usar um
    no lugar do outro burlaria a expiração curta do access token."""
    refresh = criar_refresh_token(usuario_id=1, papel="produtor")
    with pytest.raises(HTTPException) as excinfo:
        decodificar_token(refresh, tipo_esperado="access")
    assert excinfo.value.status_code == 401


def test_token_expirado_e_recusado():
    token = jwt.encode(
        {
            "sub": "1",
            "papel": "produtor",
            "tipo": "access",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(HTTPException) as excinfo:
        decodificar_token(token, tipo_esperado="access")
    assert excinfo.value.status_code == 401


def test_obter_produtor_atual_exige_prefixo_bearer():
    token = criar_access_token(usuario_id=1, papel="produtor")
    with pytest.raises(HTTPException) as excinfo:
        obter_produtor_atual(authorization=token)  # sem "Bearer "
    assert excinfo.value.status_code == 401


def test_obter_produtor_atual_com_bearer_valido_funciona():
    token = criar_access_token(usuario_id=42, papel="administrador")
    resultado = obter_produtor_atual(authorization=f"Bearer {token}")
    assert resultado == {"usuario_id": 42, "papel": "administrador"}


def test_token_com_relogio_levemente_adiantado_e_aceito():
    """Regressão: sem tolerância de relógio, um token emitido por uma
    máquina alguns segundos adiantada era recusado com 401 "Token
    inválido", sem pista da causa. Aconteceu de verdade ao testar a API
    publicada no Railway a partir de uma máquina 11 segundos à frente."""
    agora = int(time.time())
    adiantado = agora + 10
    token = jwt.encode(
        {"sub": "1", "papel": "produtor", "tipo": "access",
         "iat": adiantado, "exp": adiantado + 3600},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    payload = decodificar_token(token, tipo_esperado="access")
    assert payload["sub"] == "1"


def test_token_muito_adiantado_continua_recusado():
    """A tolerância é de 30s, não um passe livre: um token nascido bem
    no futuro continua sendo recusado."""
    futuro = int(time.time()) + 600
    token = jwt.encode(
        {"sub": "1", "papel": "produtor", "tipo": "access",
         "iat": futuro, "exp": futuro + 3600},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(HTTPException) as erro:
        decodificar_token(token, tipo_esperado="access")
    assert erro.value.status_code == 401
