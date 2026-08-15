"""
cloud/app/api/routes/alertas.py

Endpoints de alertas gerados a partir dos diagnósticos 
(ex.: doença detectada com alta confiança, leitura ambiental fora da faixa esperada).

Conforme RBAC do Blueprint Seção 4.3, o Produtor tem escrita limitada a
marcar seus próprios alertas como lidos; não pode criar/apagar alertas
livremente (isso é derivado automaticamente do pipeline de diagnóstico).

Relação com o resto do sistema:
- Populado indiretamente pelo endpoint /diagnostico (app/api/routes/diagnostico.py)
  quando um diagnóstico dispara um alerta.
- Consumido pelo frontend (app/) na tela de Alertas.
- Depende de app/db/models.py (tabela `alertas`).
"""

# from fastapi import APIRouter

# router = APIRouter()

# TODO: GET /alertas: lista alertas do produtor autenticado
# TODO: PATCH /alertas/{id}/lido: marca um alerta como lido
