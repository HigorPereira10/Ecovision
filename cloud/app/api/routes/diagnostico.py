"""
cloud/app/api/routes/diagnostico.py

Endpoint principal de ingestão: POST /diagnostico
Recebe do Raspberry Pi (edge/) a imagem comprimida + leituras de sensores,
roda a inferência e persiste tudo no Supabase.

Fluxo completo, conforme Blueprint v3.0 Seção 4.2:
1. Autenticar a requisição via API Key estática (ver app/core/security.py).
2. Checar se já existe um registro com essa idempotency_key. Se existir,
   é um reenvio: devolve o diagnóstico já existente sem reprocessar
   (ver "Idempotência" abaixo).
3. Ler a imagem recebida em memória (BytesIO), nunca gravar em disco.
4. Redimensionar para 224x224, normalizar, rodar inferência TFLite
   (app/core/inference.py). Devolve um resultado placeholder se ainda
   não houver modelo carregado (ver app/core/inference.py).
5. Fazer upload da imagem já comprimida para o Supabase Storage
   (app/storage/supabase_storage.py) e obter o caminho salvo.
6. Persistir no Supabase Postgres (app/db/models.py):
   - registros_imagem (com o caminho_arquivo retornado do Storage)
   - leituras_ambientais (temperatura, umidade do ar, umidade do solo)
   - diagnosticos (classe prevista, confiança, recomendação)
   - alertas: um se o diagnóstico não for "saudavel" nem "indisponivel"
     (ver _deve_gerar_alerta abaixo), e um para cada risco ambiental
     identificado nas leituras (ver app/core/alertas_ambientais.py e
     docs/decisions/0005-limiares-ambientais.md para as fontes de cada
     limiar; nenhum desses números foi inventado no código).
7. Descartar o buffer da imagem da memória.

Idempotência: edge/src/upload/uploader.py manda um `idempotency_key`
(o UUID que edge/src/queue/offline_queue.py já gera na captura). Sem
isso, um reenvio após uma falha parcial (API confirma 200, mas o
processo do Pi cai antes de tirar o registro da fila local) criaria uma
linha duplicada no banco.

Contrato exato assumido do lado do dispositivo (edge/src/upload/uploader.py):
  POST /diagnostico
  Header: Authorization: <DEVICE_API_KEY> (sem prefixo "Bearer")
  multipart/form-data:
    - imagem: arquivo JPEG comprimido
    - device_id, timestamp, idempotency_key: strings
    - temperatura_c, umidade_ar_pct, umidade_solo_pct: opcionais. Podem
      vir ausentes OU como a string "None" (edge/src/main.py grava None
      no JSON quando um sensor falha; ver _campo_float_opcional abaixo).

Relação com o resto do sistema:
- Único endpoint chamado pelo edge/src/upload/uploader.py.
- Depende de app/core/inference.py (modelo carregado em app/main.py no
  startup) e de app/storage/supabase_storage.py.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, status
from PIL import UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import inference
from app.core.alertas_ambientais import avaliar_risco_ambiental
from app.core.security import validar_api_key_dispositivo
from app.db.models import Alerta, Diagnostico, LeituraAmbiental, RegistroImagem
from app.db.schemas import DiagnosticoOut
from app.db.session import get_session
from app.storage.supabase_storage import salvar_imagem

logger = logging.getLogger("ecovision.cloud.diagnostico")

router = APIRouter()

# Classes que NÃO geram alerta automático: "saudavel" (nada a avisar) e
# "indisponivel" (placeholder de app/core/inference.py quando ainda não
# há modelo carregado). Avisar o produtor de uma classe que ainda não
# significa nada seria pior do que simplesmente não avisar.
_CLASSES_SEM_ALERTA = {"saudavel", "indisponivel"}

# ALERTA DE SEGURANÇA (proteção contra negação de serviço): edge/src/
# compress.py mira 150-250KB por foto, então 5MB já é uma margem bem
# generosa (mais de 20x o esperado). Sem esse limite, um dispositivo com
# bug (ou uma requisição forjada, já que o device_id não é validado
# contra nenhum cadastro nesta rodada) poderia mandar um arquivo enorme
# e esgotar a RAM do processo (só 1 worker, decisão do Blueprint) antes
# mesmo de tentar abrir a imagem. Não remover nem aumentar sem motivo.
_TAMANHO_MAXIMO_IMAGEM_BYTES = 5 * 1024 * 1024


def _campo_float_opcional(valor: str | None) -> float | None:
    """edge/src/main.py grava `None` no JSON quando a leitura de um
    sensor falha. Isso pode chegar aqui como campo ausente ou como a
    string literal "None": os dois casos viram None, nunca um erro
    de validação."""
    if valor is None or valor == "" or valor == "None":
        return None
    return float(valor)


def _deve_gerar_alerta(classe_prevista: str) -> bool:
    return classe_prevista not in _CLASSES_SEM_ALERTA


async def _buscar_diagnostico_por_idempotency_key(
    sessao: AsyncSession, idempotency_key: str
) -> Diagnostico | None:
    resultado = await sessao.execute(
        select(Diagnostico)
        .join(RegistroImagem)
        .where(RegistroImagem.idempotency_key == idempotency_key)
    )
    return resultado.scalar_one_or_none()


@router.post("/diagnostico", response_model=DiagnosticoOut, dependencies=[Depends(validar_api_key_dispositivo)])
async def receber_diagnostico(
    request: Request,
    imagem: UploadFile,
    device_id: str = Form(...),
    timestamp: str = Form(...),
    idempotency_key: str = Form(...),
    temperatura_c: str | None = Form(default=None),
    umidade_ar_pct: str | None = Form(default=None),
    umidade_solo_pct: str | None = Form(default=None),
    sessao: AsyncSession = Depends(get_session),
) -> DiagnosticoOut:
    """Recebe imagem + leituras do dispositivo IoT e retorna o diagnóstico."""
    logger.info(
        "Recebido /diagnostico de device_id=%s (idempotency_key=%s)",
        device_id, idempotency_key,
    )

    diagnostico_existente = await _buscar_diagnostico_por_idempotency_key(sessao, idempotency_key)
    if diagnostico_existente is not None:
        logger.info(
            "Reenvio detectado (idempotency_key=%s): devolvendo diagnóstico "
            "já existente sem reprocessar.",
            idempotency_key,
        )
        return DiagnosticoOut.model_validate(diagnostico_existente)

    # ATENÇÃO, BUG JÁ CORRIGIDO AQUI: antes, o timestamp e as leituras
    # eram convertidos só depois do upload da imagem para o Storage, sem
    # tratamento de exceção. Um valor malformado gerava um erro 500 cru
    # E deixava uma imagem órfã no bucket (o upload já tinha acontecido,
    # mas nada era gravado no banco). Por isso todo texto é validado
    # ANTES de gastar a chamada de storage: não inverter essa ordem.
    try:
        capturado_em = datetime.fromisoformat(timestamp)
        temperatura_c_valor = _campo_float_opcional(temperatura_c)
        umidade_ar_pct_valor = _campo_float_opcional(umidade_ar_pct)
        umidade_solo_pct_valor = _campo_float_opcional(umidade_solo_pct)
    except ValueError:
        logger.warning(
            "Campo inválido (timestamp ou leitura de sensor) de device_id=%s "
            "(idempotency_key=%s)",
            device_id, idempotency_key,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="timestamp ou leitura de sensor em formato inválido.",
        )

    bytes_imagem = await imagem.read()

    if len(bytes_imagem) > _TAMANHO_MAXIMO_IMAGEM_BYTES:
        logger.warning(
            "Imagem de %d bytes recusada (limite %d) de device_id=%s",
            len(bytes_imagem), _TAMANHO_MAXIMO_IMAGEM_BYTES, device_id,
        )
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Imagem excede o tamanho máximo aceito.",
        )

    try:
        imagem_preprocessada = inference.preprocessar_imagem(bytes_imagem)
    except UnidentifiedImageError:
        logger.warning(
            "Imagem inválida/corrompida recebida de device_id=%s (idempotency_key=%s)",
            device_id, idempotency_key,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Imagem inválida ou corrompida.",
        )

    interpretador = getattr(request.app.state, "modelo_tflite", None)
    resultado = inference.rodar_inferencia(interpretador, imagem_preprocessada)
    logger.info(
        "Inferência concluída para device_id=%s: classe=%s confianca=%.2f",
        device_id, resultado["classe"], resultado["confianca"],
    )

    try:
        caminho_arquivo = await salvar_imagem(device_id, timestamp, bytes_imagem)
    except Exception:
        logger.error(
            "Falha ao salvar imagem no Supabase Storage (device_id=%s, idempotency_key=%s)",
            device_id, idempotency_key, exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao salvar a imagem no storage.",
        )

    riscos_ambientais = avaliar_risco_ambiental(
        temperatura_c_valor, umidade_ar_pct_valor, umidade_solo_pct_valor
    )

    # ATENÇÃO, BUG JÁ CORRIGIDO AQUI (condição de corrida): a checagem de
    # idempotency_key no início da função e a gravação abaixo não são
    # atômicas. Se duas requisições com a MESMA idempotency_key chegarem
    # quase juntas (ex.: o edge/ reenvia por timeout local logo depois de
    # um envio que na verdade já tinha sido aceito), as duas podem passar
    # pela checagem antes de qualquer uma terminar de gravar. A
    # constraint UNIQUE de registros_imagem.idempotency_key garante que
    # só uma delas vence. Essa violação pode aparecer já no primeiro
    # flush() (não só no commit), por isso todo o bloco de gravação
    # abaixo precisa ficar dentro do mesmo try: não separar em blocos
    # menores sem entender essa consequência.
    try:
        registro = RegistroImagem(
            device_id=device_id,
            idempotency_key=idempotency_key,
            caminho_arquivo=caminho_arquivo,
            capturado_em=capturado_em,
        )
        sessao.add(registro)
        await sessao.flush()  # garante registro.id antes das linhas filhas

        leitura = LeituraAmbiental(
            registro_imagem_id=registro.id,
            temperatura_c=temperatura_c_valor,
            umidade_ar_pct=umidade_ar_pct_valor,
            umidade_solo_pct=umidade_solo_pct_valor,
        )
        sessao.add(leitura)
        await sessao.flush()  # garante leitura.id antes de um possivel alerta ambiental

        diagnostico = Diagnostico(
            registro_imagem_id=registro.id,
            classe_prevista=resultado["classe"],
            confianca=resultado["confianca"],
            recomendacao=resultado["recomendacao"],
        )
        sessao.add(diagnostico)
        await sessao.flush()  # garante diagnostico.id antes do alerta

        if _deve_gerar_alerta(resultado["classe"]):
            descricao_doenca = resultado["recomendacao"] or "Verificar a planta o quanto antes."
            if riscos_ambientais:
                # Correlação simples em texto, isso NÃO é fusão de
                # modelo (ver ADR 0006): apenas avisa que condições
                # ambientais desfavoráveis também foram detectadas no
                # mesmo ciclo, sem alegar que uma causou a outra.
                titulos_ambientais = ", ".join(titulo for titulo, _, _ in riscos_ambientais)
                descricao_doenca += (
                    f" Condições ambientais também fora do ideal neste ciclo "
                    f"({titulos_ambientais}). Corrigir isso pode ajudar na recuperação."
                )
            sessao.add(
                Alerta(
                    diagnostico_id=diagnostico.id,
                    titulo=f"Possível {resultado['classe']} detectado",
                    descricao=descricao_doenca,
                    # resultado["severidade"] só é None no placeholder
                    # "indisponivel", mas esse caso nunca chega aqui
                    # porque _deve_gerar_alerta já filtra essa classe.
                    severidade=resultado["severidade"],
                )
            )
            logger.info("Alerta gerado para device_id=%s (diagnostico_id=%s)", device_id, diagnostico.id)

        for titulo, descricao, severidade in riscos_ambientais:
            sessao.add(
                Alerta(
                    leitura_id=leitura.id,
                    titulo=titulo,
                    descricao=descricao,
                    severidade=severidade,
                )
            )
            logger.info(
                "Alerta ambiental gerado para device_id=%s: %s", device_id, titulo,
            )

        await sessao.commit()
    except IntegrityError:
        await sessao.rollback()
        logger.info(
            "Corrida de idempotency_key=%s detectada: devolvendo o "
            "diagnóstico da requisição que venceu.",
            idempotency_key,
        )
        diagnostico_vencedor = await _buscar_diagnostico_por_idempotency_key(sessao, idempotency_key)
        if diagnostico_vencedor is None:
            raise  # não deveria acontecer; melhor falhar alto do que esconder um bug diferente
        return DiagnosticoOut.model_validate(diagnostico_vencedor)

    await sessao.refresh(diagnostico)

    logger.info(
        "Diagnóstico %s registrado com sucesso para device_id=%s",
        diagnostico.id, device_id,
    )

    return DiagnosticoOut.model_validate(diagnostico)
