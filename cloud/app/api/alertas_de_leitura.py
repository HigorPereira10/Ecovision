"""
Geração dos alertas ambientais de uma leitura gravada, compartilhada por
POST /diagnostico e POST /leituras para que as regras sejam as mesmas nos
dois caminhos. Os limiares ficam em app/core/alertas_ambientais.py.
"""

import logging

from app.core.alertas_ambientais import avaliar_risco_ambiental
from app.db.models import Alerta, LeituraAmbiental

logger = logging.getLogger("ecovision.cloud.alertas_de_leitura")


def montar_alertas_ambientais(leitura: LeituraAmbiental) -> list[Alerta]:
    """Devolve os alertas ambientais de `leitura`, sem adicioná-los à sessão.

    A leitura precisa ter `id` (já ter passado por flush). Quem chama
    adiciona os alertas na mesma transação do restante do ciclo.
    """
    riscos = avaliar_risco_ambiental(
        leitura.temperatura_c, leitura.umidade_ar_pct, leitura.umidade_solo_pct
    )

    alertas: list[Alerta] = []
    for titulo, descricao, severidade in riscos:
        alertas.append(
            Alerta(
                leitura_id=leitura.id,
                titulo=titulo,
                descricao=descricao,
                severidade=severidade,
            )
        )
        logger.info(
            "Alerta ambiental gerado para device_id=%s: %s", leitura.device_id, titulo
        )

    return alertas
