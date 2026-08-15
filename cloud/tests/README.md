# cloud/tests

Testes automatizados do backend (pytest + pytest-asyncio sugeridos,
compatíveis com FastAPI + SQLAlchemy async).

Cobertura mínima esperada quando implementado (ver Plano de Execução,
Fase 5 — Integração e campo, do Blueprint v3.0):
- Testes unitários de `app/core/security.py` (API Key, JWT, bcrypt).
- Testes unitários de `app/core/inference.py` (pré-processamento e shape
  de saída, com um modelo `.tflite` de teste).
- Teste de integração do endpoint `/diagnostico` cobrindo o fluxo
  completo (recepção -> inferência -> Storage -> Postgres).
- Simulação de fila offline / retry do lado do dispositivo (ver
  `edge/src/queue/offline_queue.py`), validando que a API é idempotente
  a reenvios.
