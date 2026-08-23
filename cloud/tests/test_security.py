"""
cloud/tests/test_security.py

O que este arquivo verifica, em português simples:

A Raspberry Pi só pode falar com a API se mandar a "senha" certa (a API
Key) no cabeçalho da requisição. Este teste confere as três situações
possíveis: chave certa (deixa passar), chave errada (barra com 401) e
chave ausente (também barra com 401) — sem isso, qualquer um na
internet poderia mandar fotos falsas pro sistema.
"""

import pytest
from fastapi import HTTPException

from app.config import settings
from app.core.security import validar_api_key_dispositivo


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
