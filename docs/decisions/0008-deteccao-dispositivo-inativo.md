# ADR 0008: Detecção de dispositivo IoT inativo (falha silenciosa)

**Status:** Decidido (primeira versão).

## Contexto

Revisão da branch `preparacao-api-real` (Amanda) encontrou um tipo de
alerta no mock (`"tipo": "dispositivo"`, "sensor sem reportar leituras
há mais de 6 horas") que não existe em nenhuma lógica do backend. A
ideia tem valor real: hoje, se o Raspberry Pi perder energia, perder
Wi-Fi por muito tempo, tiver o cartão SD cheio ou travar, o produtor
não tem nenhuma forma de saber que o monitoramento parou (é uma falha
silenciosa). (Sera implementado no backend)

Diferente de [ADR 0005](0005-limiares-ambientais.md) (risco ambiental,
avaliado a cada requisição de `/diagnostico`), aqui não há uma nova
leitura chegando para avaliar: o problema é justamente a *ausência*
de novas leituras.

## Decisão

**Definição de "inativo":** tempo decorrido desde a última captura
recebida (`registros_imagem.criado_em` mais recente daquele
`device_id`) comparado a um múltiplo do intervalo de captura esperado
(`CAPTURE_INTERVAL_MINUTES`, `edge/src/config.py`, padrão 120 min = 2h).

Dois níveis, mesma escala de severidade do resto do sistema
(`alta`/`media`, ver ADR 0005 e 0006):

| Tempo sem captura | Severidade | Motivo |
|---|---|---|
| `< 4h` (2x o intervalo) | (sem alerta) | Normal: o edge já reenvia via fila offline (`edge/src/fila/offline_queue.py`) assim que a conexão volta; um atraso de 1 ciclo não é anômalo. |
| `4h` a `8h` (2x a 4x) | **media** | Atraso persistente, mas ainda dentro do que a fila offline local resolveria sozinha ao reconectar; não é necessariamente uma falha grave. |
| `> 8h` (mais de 4x) | **alta** | Muito além do que uma reconexão de rede razoável explicaria: provável falha real (queda de energia, hardware, cartão SD, Wi-Fi fora do ar por muito tempo). |
| Nunca recebeu nenhuma captura | **alta** | Dispositivo cadastrado mas nunca funcionou, ou captura inicial falhando. |

**Múltiplos escolhidos (2x/4x):** convenção prática, não uma fonte
agronômica (isso aqui é engenharia de sistema, não fitossanidade). O
objetivo é dar duas margens de tolerância antes de alarmar: a fila
offline do edge já reenvia sozinha em reconexões curtas, então alertar
no primeiro ciclo perdido geraria alarme falso. Ajustável se a
validação em campo (Sprint 9) mostrar que está sensível demais ou de
menos.

**Onde é calculado:** sob demanda (a cada chamada de `GET /alertas`),
não por um job/scheduler em background. Isso é proposital: o Blueprint
v3.0 já decidiu 1 único worker no Railway;
manter um scheduler rodando separado exigiria um segundo processo, o
que contradiz essa decisão de simplicidade para o escopo de 1
dispositivo. Consequência aceita: se ninguém abrir o dashboard, o
alerta não é "gerado" (não fica registrado em `alertas`) até a próxima
consulta, o que é aceitável porque o valor de calcular isso só existe
quando alguém vai olhar o painel mesmo.

**Não persiste em `alertas`:** ao contrário dos alertas de
doença/ambiente, este é *sintético* (calculado a cada leitura, não
gravado no banco). Não faz sentido guardar histórico de "estava
inativo às 14h32" da mesma forma que se guarda um diagnóstico de
doença.

## Fontes

Nenhuma fonte agronômica aplicável: decisão de engenharia de sistema,
baseada no próprio comportamento documentado do mecanismo de fila
offline do edge (`edge/README.md`, `docs/decisions/*`).

## Implementação

- `cloud/app/core/alertas_dispositivo.py` (função pura de decisão).
- Consumido por `GET /alertas` (`cloud/app/api/routes/alertas.py`).

**Formato do item sintético na resposta (decidido):** `AlertaOut`
(`cloud/app/db/schemas.py`) tem os campos `id: int | None` e
`sintetico: bool`. O item de dispositivo inativo vem com `id: null` e
`sintetico: true`; todos os alertas reais vêm com `sintetico: false`.
`PATCH /alertas/{id}/lido` só aceita um `id` de uma linha real: como o
item sintético nunca tem uma linha na tabela `alertas`, qualquer
tentativa de marcá-lo como lido cai naturalmente num 404.

## Pendências

- Os múltiplos 2x/4x podem precisar de ajuste após a validação em
  campo (Sprint 9).
