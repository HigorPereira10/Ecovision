"""
cloud/app/api/routes/dispositivos.py

CRUD de dispositivos IoT (Raspberry Pi cadastrados) associados a um
produtor/estufa. Acesso restrito por RBAC (Blueprint Seção 4.3):
Produtor vê/gerencia os próprios dispositivos; Administrador tem CRUD
irrestrito, incluindo gestão do modelo de IA associado a cada dispositivo.

Relação com o resto do sistema:
- Consumido pelo frontend (app/) para exibir/gerenciar os dispositivos
  vinculados ao produtor autenticado.
- Depende de app/db/models.py (tabela de dispositivos) e
  app/core/security.py (JWT + verificação de papel).
"""

# from fastapi import APIRouter

# router = APIRouter()

# TODO: GET /dispositivos — lista os dispositivos do produtor autenticado
# TODO: POST /dispositivos — cadastra um novo dispositivo (Administrador)
# TODO: GET /dispositivos/{id} — detalhe de um dispositivo
