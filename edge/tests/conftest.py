"""
edge/tests/conftest.py

Configuração compartilhada dos testes automatizados de edge/src/.

edge/src/config.py exige algumas variáveis de ambiente (URL da API,
chave do dispositivo) assim que é importado. No dispositivo real elas
vêm do arquivo edge/.env. Para os testes rodarem sem precisar desse
arquivo nem de um Raspberry Pi de verdade, este conftest define valores
de teste ANTES de qualquer teste ser coletado.

Como rodar (dentro do WSL/Ubuntu, já que edge/src/queue/offline_queue.py
usa fcntl, um recurso que só existe em Linux/Unix, não no Python do
Windows):

    cd Ecovision
    pip install -r edge/tests/requirements-test.txt
    pytest edge/tests -v
"""

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

os.environ.setdefault("API_BASE_URL", "http://testserver.invalid")
os.environ.setdefault("DEVICE_API_KEY", "chave-de-teste")
os.environ.setdefault("DEVICE_ID", "pi-teste-automatizado")
