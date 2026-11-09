"""
POST /diagnostico: recebe a captura e as leituras de um dispositivo,
classifica a imagem e grava tudo.

1. Autentica a credencial do dispositivo (app/api/dispositivo_auth.py).
2. Se a idempotency_key já existe, devolve o diagnóstico gravado.
3. Valida os campos e lê a imagem em memória.
4. Verifica a qualidade da imagem e classifica por janelas
   (app/core/janelas.py), com recurso ao quadro inteiro em caso de falha.
5. Envia a imagem ao Supabase Storage.
6. Grava registro, leitura, diagnóstico e alertas (de doença, de imagem
   inadequada e ambientais) em uma única transação.

Formato esperado (edge/src/upload/uploader.py): cabeçalho Authorization
com a credencial do dispositivo, sem "Bearer"; multipart/form-data com
imagem, device_id, timestamp, idempotency_key e as leituras opcionais
temperatura_c, umidade_ar_pct e umidade_solo_pct (ausentes ou "None"
quando o sensor falha).
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, status
from PIL import UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core import inference, janelas
from app.api.alertas_de_leitura import montar_alertas_ambientais
from app.core.alertas_ambientais import avaliar_risco_ambiental
from app.core.pressao_infecciosa import (
    CLASSES_FUNGICAS,
    avaliar_plausibilidade,
    calcular_pressao,
)
from app.api.dispositivo_auth import autenticar_dispositivo
from app.core.security import obter_credencial_dispositivo
from app.db.models import Alerta, Diagnostico, LeituraAmbiental, RegistroImagem
from app.db.schemas import DiagnosticoOut
from app.db.session import get_session
from app.storage.supabase_storage import salvar_imagem

logger = logging.getLogger("ecovision.cloud.diagnostico")

router = APIRouter()

# Classes que não geram alerta de doença: "saudavel", "indisponivel"
# (modelo não carregado) e "imagem_inadequada", que tem alerta próprio.
_CLASSES_SEM_ALERTA = {"saudavel", "indisponivel", inference.CLASSE_IMAGEM_INADEQUADA}

# Limite de leituras consultadas para a janela de pressão de infecção,
# para que o custo não cresça com a idade do dispositivo.
_LIMITE_LEITURAS_HISTORICO = 500

# Tamanho máximo da imagem. As capturas têm de 1,3 a 1,5 MB; o limite
# protege a memória do processo contra arquivos muito grandes.
_TAMANHO_MAXIMO_IMAGEM_BYTES = 5 * 1024 * 1024


def _campo_float_opcional(valor: str | None) -> float | None:
    """Converte um campo opcional em float. Campo ausente ou com o texto
    "None" (sensor com falha) vira None, sem erro de validação."""
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


async def _recomendacao_com_ressalva(
    sessao: AsyncSession,
    device_id: str,
    resultado: dict,
    capturado_em: datetime,
    temperatura_c: float | None,
    umidade_ar_pct: float | None,
) -> str | None:
    """Acrescenta à recomendação a ressalva de plausibilidade ambiental,
    quando houver.

    Uma falha na consulta ao histórico não interrompe a rota: o
    diagnóstico segue sem a ressalva.
    """
    recomendacao = resultado.get("recomendacao")
    try:
        linhas = (await sessao.execute(
            select(
                RegistroImagem.capturado_em,
                LeituraAmbiental.temperatura_c,
                LeituraAmbiental.umidade_ar_pct,
            )
            .join(LeituraAmbiental, LeituraAmbiental.registro_imagem_id == RegistroImagem.id)
            .where(RegistroImagem.device_id == device_id)
            .order_by(RegistroImagem.capturado_em.desc())
            .limit(_LIMITE_LEITURAS_HISTORICO)
        )).all()

        # A leitura desta captura ainda não foi gravada; entra aqui para a
        # janela incluir a amostra mais recente.
        leituras = [(m, t, u) for m, t, u in linhas]
        leituras.append((capturado_em, temperatura_c, umidade_ar_pct))

        pressao = calcular_pressao(leituras, ate=capturado_em)
        ressalva = avaliar_plausibilidade(resultado["classe"], pressao)
    except Exception:
        logger.warning(
            "Falha ao cruzar o diagnóstico com o histórico ambiental "
            "(device_id=%s). Seguindo sem a ressalva.",
            device_id, exc_info=True,
        )
        return recomendacao

    if ressalva is None:
        return recomendacao

    _titulo, descricao = ressalva
    logger.info(
        "Ressalva ambiental anexada ao diagnóstico de device_id=%s "
        "(classe=%s, DSV acumulado=%d, cobertura=%.0f%%)",
        device_id, resultado["classe"], pressao.dsv_acumulado, pressao.cobertura * 100,
    )
    return f"{recomendacao}\n\n{descricao}" if recomendacao else descricao


@router.post("/diagnostico", response_model=DiagnosticoOut)
async def receber_diagnostico(
    request: Request,
    imagem: UploadFile,
    device_id: str = Form(...),
    timestamp: str = Form(...),
    idempotency_key: str = Form(...),
    temperatura_c: str | None = Form(default=None),
    umidade_ar_pct: str | None = Form(default=None),
    umidade_solo_pct: str | None = Form(default=None),
    credencial: str = Depends(obter_credencial_dispositivo),
    sessao: AsyncSession = Depends(get_session),
) -> DiagnosticoOut:
    """Recebe imagem e leituras do dispositivo e devolve o diagnóstico."""
    # A autenticação usa o device_id do formulário, por isso não é uma
    # dependência simples (ver app/api/dispositivo_auth.py).
    await autenticar_dispositivo(sessao, device_id, credencial)

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

    # Todos os campos são validados antes do upload, para que um valor
    # inválido não deixe imagem órfã no bucket.
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

    # Verificação de qualidade antes de classificar: o modelo atribui alta
    # confiança a "saudavel" em imagens escuras ou sem conteúdo. A captura
    # reprovada é gravada normalmente, mas sem diagnóstico.
    motivo_imagem_ruim = inference.avaliar_qualidade_imagem(bytes_imagem)

    if motivo_imagem_ruim is not None:
        resultado = {
            "classe": inference.CLASSE_IMAGEM_INADEQUADA,
            "confianca": 0.0,
            "recomendacao": motivo_imagem_ruim,
            "severidade": None,
        }
        logger.warning(
            "Imagem reprovada na guarda de qualidade para device_id=%s: %s",
            device_id, motivo_imagem_ruim,
        )
    else:
        interpretador = getattr(request.app.state, "modelo_tflite", None)
        if interpretador is not None and get_settings().DIAGNOSTICO_POR_JANELA:
            # Em caso de falha no caminho por janelas, classifica o quadro
            # inteiro, para a captura não ficar sem diagnóstico.
            try:
                resultado = janelas.diagnosticar_por_janelas(interpretador, bytes_imagem)
            except Exception:
                logger.warning(
                    "Falha no diagnóstico por janela para device_id=%s. "
                    "Caindo no quadro inteiro.", device_id, exc_info=True,
                )
                resultado = inference.rodar_inferencia(interpretador, imagem_preprocessada)
        else:
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

    # Cruzamento com o histórico ambiental (app/core/pressao_infecciosa.py):
    # quando não houve molhamento foliar suficiente para uma infecção
    # fúngica, a recomendação recebe uma ressalva.
    if resultado["classe"] in CLASSES_FUNGICAS:
        resultado["recomendacao"] = await _recomendacao_com_ressalva(
            sessao, device_id, resultado,
            capturado_em, temperatura_c_valor, umidade_ar_pct_valor,
        )

    # A verificação de idempotency_key no início e a gravação abaixo não
    # são atômicas: duas requisições com a mesma chave podem passar pela
    # verificação. A restrição UNIQUE garante que só uma grava, e a
    # violação pode surgir já no primeiro flush(), por isso toda a
    # gravação fica no mesmo bloco try.
    try:
        registro = RegistroImagem(
            device_id=device_id,
            idempotency_key=idempotency_key,
            caminho_arquivo=caminho_arquivo,
            capturado_em=capturado_em,
        )
        sessao.add(registro)
        await sessao.flush()  # obtém registro.id antes das linhas filhas

        # device_id gravado também na leitura, para que GET /leituras
        # filtre por dispositivo sem depender do registro de imagem.
        leitura = LeituraAmbiental(
            device_id=device_id,
            registro_imagem_id=registro.id,
            temperatura_c=temperatura_c_valor,
            umidade_ar_pct=umidade_ar_pct_valor,
            umidade_solo_pct=umidade_solo_pct_valor,
        )
        sessao.add(leitura)
        await sessao.flush()  # obtém leitura.id para eventual alerta ambiental

        diagnostico = Diagnostico(
            registro_imagem_id=registro.id,
            classe_prevista=resultado["classe"],
            confianca=resultado["confianca"],
            recomendacao=resultado["recomendacao"],
        )
        sessao.add(diagnostico)
        await sessao.flush()  # obtém diagnostico.id antes do alerta

        if _deve_gerar_alerta(resultado["classe"]):
            descricao_doenca = resultado["recomendacao"] or "Verificar a planta o quanto antes."
            if riscos_ambientais:
                # Apenas registra que houve condições ambientais
                # desfavoráveis no mesmo ciclo, sem relação causal.
                titulos_ambientais = ", ".join(titulo for titulo, _, _ in riscos_ambientais)
                descricao_doenca += (
                    f" Condições ambientais também fora do ideal neste ciclo "
                    f"({titulos_ambientais}). Corrigir isso pode ajudar na recuperação."
                )
            sessao.add(
                Alerta(
                    diagnostico_id=diagnostico.id,
                    # O título descreve o sinal observado; a incidência
                    # medida vai na descrição.
                    titulo=f"Sinal de {inference.rotulo_para_produtor(resultado['classe'])} na planta",
                    descricao=descricao_doenca,
                    # severidade só é None em "indisponivel", já filtrado
                    # por _deve_gerar_alerta.
                    severidade=resultado["severidade"],
                )
            )
            logger.info("Alerta gerado para device_id=%s (diagnostico_id=%s)", device_id, diagnostico.id)

        # Imagem inadequada gera alerta de verificação do equipamento, com
        # severidade média.
        if resultado["classe"] == inference.CLASSE_IMAGEM_INADEQUADA:
            sessao.add(
                Alerta(
                    diagnostico_id=diagnostico.id,
                    titulo="Não foi possível analisar a foto",
                    descricao=(
                        f"{motivo_imagem_ruim} A imagem foi guardada no histórico "
                        "para você conferir o que aconteceu."
                    ),
                    severidade="media",
                )
            )
            logger.info(
                "Alerta de qualidade de imagem gerado para device_id=%s (diagnostico_id=%s)",
                device_id, diagnostico.id,
            )

        # Mesma regra de POST /leituras (app/api/alertas_de_leitura.py).
        for alerta_ambiental in montar_alertas_ambientais(leitura):
            sessao.add(alerta_ambiental)

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
            raise  # violação inesperada: propagar em vez de ocultar
        return DiagnosticoOut.model_validate(diagnostico_vencedor)

    await sessao.refresh(diagnostico)

    logger.info(
        "Diagnóstico %s registrado com sucesso para device_id=%s",
        diagnostico.id, device_id,
    )

    return DiagnosticoOut.model_validate(diagnostico)
