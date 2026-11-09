"""
Testes de edge/src/config.py: os caminhos da fila e dos logs são
absolutos e ancorados em edge/, e a falta de uma variável obrigatória gera
erro claro na importação.
"""

import os
import subprocess
import sys
from pathlib import Path

from edge.src import config

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_queue_dir_e_absoluto_e_fica_dentro_de_edge():
    assert config.QUEUE_DIR.is_absolute()
    assert config.QUEUE_DIR == _REPO_ROOT / "edge" / "data" / "queue"


def test_logs_dir_e_absoluto_e_fica_dentro_de_edge():
    assert config.LOGS_DIR.is_absolute()
    assert config.LOGS_DIR == _REPO_ROOT / "edge" / "data" / "logs"


def test_queue_file_e_queue_images_dir_ficam_dentro_de_queue_dir():
    assert config.QUEUE_FILE == config.QUEUE_DIR / "fila.jsonl"
    assert config.QUEUE_IMAGES_DIR == config.QUEUE_DIR / "images"


def test_falta_de_variavel_obrigatoria_da_erro_claro():
    """Sem .env, importar config.py falha citando a variável ausente."""
    ambiente_sem_api_url = {
        chave: valor for chave, valor in os.environ.items() if chave != "API_BASE_URL"
    }
    resultado = subprocess.run(
        [sys.executable, "-c", "from edge.src import config"],
        cwd=_REPO_ROOT,
        env=ambiente_sem_api_url,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode != 0
    assert "API_BASE_URL" in resultado.stderr
