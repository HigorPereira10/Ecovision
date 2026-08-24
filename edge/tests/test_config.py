"""
edge/tests/test_config.py

O que este arquivo verifica, em português simples:

1. Que os caminhos da fila offline (QUEUE_DIR, QUEUE_FILE, ...) e dos
   logs sempre viram caminhos ABSOLUTOS, ancorados na pasta edge/ do
   próprio repositório, não importa de onde o script é chamado
   (manualmente ou pelo cron). Isso corrige um bug real encontrado em
   revisão: antes, o caminho padrão era relativo e podia apontar para
   uma pasta diferente dependendo de quem chamava o script, fazendo
   fotos e leituras "sumirem" sem nenhum erro visível.
2. Que o programa recusa rodar, com uma mensagem de erro clara dizendo
   qual variável falta, se uma configuração obrigatória (URL da API,
   chave do dispositivo) não estiver definida, em vez de travar de
   forma confusa em algum lugar mais adiante no código.
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
    """Simula esquecer de configurar o .env no dispositivo: importar
    config.py deve falhar imediatamente, citando o nome exato da
    variável que falta, nunca falhar em silêncio ou mais tarde."""
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
