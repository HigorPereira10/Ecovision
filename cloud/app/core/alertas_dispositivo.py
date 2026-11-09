"""
Detecção de dispositivo que parou de enviar dados (queda de energia, rede
fora do ar por muito tempo, cartão cheio ou travamento).

A verificação é calculada sob demanda a partir da última captura recebida,
sem tarefa em segundo plano, e gera um alerta sintético (não gravado em
alertas) nas rotas de alertas e de dispositivos.
"""

from datetime import datetime, timezone

# Intervalo de captura do dispositivo (edge/src/config.py). Os dois lados
# rodam em máquinas diferentes; se o intervalo mudar, atualize aqui também.
INTERVALO_CAPTURA_MINUTOS = 120

# Múltiplos do intervalo de captura, com margem para a fila local do
# dispositivo se recuperar antes de alertar o produtor.
LIMIAR_ATRASO_MEDIA_MINUTOS = INTERVALO_CAPTURA_MINUTOS * 2  # 4h
LIMIAR_ATRASO_ALTA_MINUTOS = INTERVALO_CAPTURA_MINUTOS * 4  # 8h


def avaliar_inatividade_dispositivo(
    ultima_captura_em: datetime | None,
    agora: datetime | None = None,
) -> tuple[str, str, str] | None:
    """Devolve (titulo, descricao, severidade) se o dispositivo estiver
    atrasado ou inativo, ou None.

    `ultima_captura_em`: momento da captura mais recente; None se o
    dispositivo nunca enviou dados. `agora`: injetável para testes.
    """
    if agora is None:
        agora = datetime.now(timezone.utc)

    # O SQLite dos testes devolve datas sem fuso; as datas são gravadas em
    # UTC, então assumir UTC vale nos dois bancos.
    if ultima_captura_em is not None and ultima_captura_em.tzinfo is None:
        ultima_captura_em = ultima_captura_em.replace(tzinfo=timezone.utc)

    if ultima_captura_em is None:
        return (
            "Dispositivo nunca reportou dados",
            "Este dispositivo está cadastrado, mas ainda não enviou "
            "nenhuma captura. Verifique a alimentação, a conexão Wi-Fi "
            "e os logs do Raspberry Pi.",
            "alta",
        )

    minutos_sem_captura = (agora - ultima_captura_em).total_seconds() / 60

    if minutos_sem_captura > LIMIAR_ATRASO_ALTA_MINUTOS:
        horas = minutos_sem_captura / 60
        return (
            "Dispositivo inativo",
            f"Sem novas capturas há {horas:.1f}h (esperado a cada "
            f"{INTERVALO_CAPTURA_MINUTOS // 60}h). Isso vai além do que uma "
            f"reconexão de rede normal explicaria: verifique a alimentação, "
            f"o Wi-Fi e o cartão microSD do dispositivo.",
            "alta",
        )

    if minutos_sem_captura > LIMIAR_ATRASO_MEDIA_MINUTOS:
        horas = minutos_sem_captura / 60
        return (
            "Dispositivo atrasado",
            f"Sem novas capturas há {horas:.1f}h (esperado a cada "
            f"{INTERVALO_CAPTURA_MINUTOS // 60}h). Pode ser uma instabilidade "
            f"passageira de rede, o dispositivo reenvia dados pendentes "
            f"automaticamente assim que a conexão voltar.",
            "media",
        )

    return None
