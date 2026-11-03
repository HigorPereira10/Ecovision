"""
cloud/app/api/alertas_de_leitura.py

Transforma uma leitura ambiental já gravada nos alertas que ela merece.

POR QUE ISTO FOI EXTRAÍDO: a geração de alerta ambiental morava dentro
de POST /diagnostico, que era o único lugar por onde leitura entrava no
sistema. Desde a migration 0008 existe um segundo caminho, POST
/leituras, para o Pi mandar sensor sem foto a cada 15 minutos.

Com duas rotas, duplicar as oito linhas significaria que um limiar novo,
ou uma mudança de severidade, passaria a valer em um caminho e não no
outro, sem nada falhar de forma visível: o produtor receberia alerta de
solo seco no ciclo com foto e não no ciclo sem foto, ou vice-versa.

Este módulo mora em app/api/ e não em app/core/ porque constrói objetos
de app/db/, e app/core/ não importa app/db/ (ver o diagrama em
docs/architecture/). O cálculo dos limiares em si continua em
app/core/alertas_ambientais.py, que é puro e testável sem banco.
"""

import logging

from app.core.alertas_ambientais import avaliar_risco_ambiental
from app.db.models import Alerta, LeituraAmbiental

logger = logging.getLogger("ecovision.cloud.alertas_de_leitura")


def montar_alertas_ambientais(leitura: LeituraAmbiental) -> list[Alerta]:
    """Devolve os alertas ambientais de `leitura`, sem adicioná-los à sessão.

    A leitura precisa já ter `id` (ou seja, já ter passado por um flush),
    porque `alertas.leitura_id` é obrigatório. Quem chama decide quando
    adicionar e comitar, para o alerta entrar na mesma transação do
    resto do ciclo.

    Devolve lista vazia quando nada está fora de faixa, que é o caso
    comum: numa estufa saudável esta função não gera nada, e é assim que
    o painel de alertas continua significando alguma coisa.
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
