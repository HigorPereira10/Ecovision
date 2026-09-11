"""
cloud/app/core/alertas_dispositivo.py

Detecta quando um dispositivo IoT parou de mandar dados (falha
silenciosa: queda de energia, Wi-Fi fora do ar por muito tempo, cartão
SD cheio, travamento). Ver
docs/decisions/0008-deteccao-dispositivo-inativo.md para a decisão
completa e a justificativa dos múltiplos usados abaixo.

Diferente de alertas_ambientais.py (avaliado a cada requisição de
/diagnostico, a partir de uma leitura nova), esta checagem é
*computada sob demanda* a partir de quanto tempo faz desde a última
captura recebida. Não existe um job/scheduler rodando em background
(Blueprint v3.0: 1 único worker no Railway).

Relação com o resto do sistema:
- Será consumido por GET /alertas (cloud/app/api/routes/alertas.py,
  ainda não implementado) para incluir um item sintético (não
  persistido em `alertas`) quando o dispositivo estiver inativo.
- CAPTURE_INTERVAL_MINUTES é o mesmo nome/conceito de
  edge/src/config.py, mas os dois lados não compartilham o valor
  automaticamente (são processos/máquinas diferentes). Se o intervalo
  do edge mudar, este valor precisa ser atualizado manualmente aqui.
"""

from datetime import datetime, timezone

# Mesmo padrão de edge/src/config.py (CAPTURE_INTERVAL_MINUTES, padrão
# 120 min = 2h). Não importado diretamente do edge/ porque cloud/ e
# edge/ rodam em processos/máquinas separadas.
INTERVALO_CAPTURA_MINUTOS = 120

# Múltiplos do intervalo de captura, não uma fonte agronômica (isso é
# engenharia de sistema). Dão margem para a fila offline do edge
# (edge/src/queue/offline_queue.py) se recuperar sozinha antes de
# alarmar o produtor à toa.
LIMIAR_ATRASO_MEDIA_MINUTOS = INTERVALO_CAPTURA_MINUTOS * 2  # 4h
LIMIAR_ATRASO_ALTA_MINUTOS = INTERVALO_CAPTURA_MINUTOS * 4  # 8h


def avaliar_inatividade_dispositivo(
    ultima_captura_em: datetime | None,
    agora: datetime | None = None,
) -> tuple[str, str, str] | None:
    """Retorna (titulo, descricao, severidade) se o dispositivo estiver
    inativo, ou None se estiver dentro do esperado.

    `ultima_captura_em`: timestamp (`registros_imagem.criado_em`) da
    captura mais recente já recebida daquele device_id. None significa
    que o dispositivo nunca enviou nenhuma captura.

    `agora`: injetável para facilitar teste; usa o horário atual (UTC)
    se omitido.
    """
    if agora is None:
        agora = datetime.now(timezone.utc)

    # SQLite (usado nos testes, ver cloud/tests/conftest.py) nao
    # preserva timezone ao ler de volta uma coluna DateTime(timezone=True):
    # o valor volta "naive". _agora_utc() (app/db/models.py) sempre grava
    # em UTC, entao assumir UTC aqui e seguro tanto no Postgres real
    # quanto nesse caso do SQLite de teste.
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
