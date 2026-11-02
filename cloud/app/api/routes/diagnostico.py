"""
cloud/app/api/routes/diagnostico.py

Endpoint principal de ingestão: POST /diagnostico
Recebe do Raspberry Pi (edge/) a imagem comprimida + leituras de sensores,
roda a inferência e persiste tudo no Supabase.

Fluxo completo, conforme Blueprint v3.0 Seção 4.2:
1. Autenticar a requisição pela credencial daquele dispositivo (ver
   app/api/dispositivo_auth.py e ADR 0009).
2. Checar se já existe um registro com essa idempotency_key. Se existir,
   é um reenvio: devolve o diagnóstico já existente sem reprocessar
   (ver "Idempotência" abaixo).
3. Ler a imagem recebida em memória (BytesIO), nunca gravar em disco.
4. Redimensionar para 224x224 com NEAREST, rodar inferência TFLite
   (app/core/inference.py). NÃO normalizar aqui: o modelo normaliza por
   dentro e espera pixels crus de 0 a 255 (ver ADR 0011 para as duas
   armadilhas desse contrato). Devolve um resultado placeholder se
   nenhum modelo foi carregado.
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
(o UUID que edge/src/fila/offline_queue.py já gera na captura). Sem
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

# Classes que NÃO geram alerta de doença: "saudavel" (nada a avisar),
# "indisponivel" (placeholder de app/core/inference.py quando não há
# modelo carregado) e "imagem_inadequada" (a foto foi reprovada na
# guarda de qualidade, então não existe diagnóstico a anunciar). Avisar
# o produtor de uma classe que não significa nada seria pior do que
# simplesmente não avisar. A imagem inadequada tem alerta PRÓPRIO, de
# câmera, gerado mais abaixo.
_CLASSES_SEM_ALERTA = {"saudavel", "indisponivel", inference.CLASSE_IMAGEM_INADEQUADA}

# Teto de leituras lidas para a janela de pressão infecciosa. Com
# captura a cada 2h, 14 dias são 168 leituras, então 500 dá folga larga
# para intervalos menores sem virar consulta pesada a cada diagnóstico.
# O teto existe para o custo não crescer com a idade do dispositivo.
_LIMITE_LEITURAS_HISTORICO = 500

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


async def _recomendacao_com_ressalva(
    sessao: AsyncSession,
    device_id: str,
    resultado: dict,
    capturado_em: datetime,
    temperatura_c: float | None,
    umidade_ar_pct: float | None,
) -> str | None:
    """Acrescenta à recomendação a ressalva de plausibilidade ambiental,
    quando houver. Devolve a recomendação original se não houver.

    NUNCA DERRUBA A ROTA: se a consulta ao histórico falhar, o
    diagnóstico segue sem a ressalva. Vale aqui o mesmo princípio de
    app/core/inference.py, que mantém a API de pé mesmo sem modelo:
    uma camada acessória não pode impedir a captura de ser gravada.
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

        # A leitura desta captura ainda não está no banco (a gravação
        # vem depois), então entra aqui à mão. Sem isso a janela perde
        # justamente a amostra mais recente, que é a que mais pesa.
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
    """Recebe imagem + leituras do dispositivo IoT e retorna o diagnóstico."""
    # A autenticação não pode ser uma dependency simples como nas outras
    # rotas: ela precisa do `device_id`, que chega no corpo do formulário
    # e não no header, para conferir se aquela credencial autoriza enviar
    # COMO aquele dispositivo. Ver app/api/dispositivo_auth.py.
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

    # GUARDA DE QUALIDADE, antes de classificar. O modelo não tem uma
    # saída para "isto não é uma folha": ele empurra qualquer entrada
    # para uma das três classes, e no escuro empurra para "saudavel"
    # com confiança altíssima (ver os números medidos em
    # app/core/inference.py). Classificar uma foto preta produziria a
    # afirmação mais perigosa que este sistema pode fazer: "sua planta
    # está saudável", com 95% de confiança, sobre uma imagem onde não
    # dá para ver nada.
    #
    # A captura NÃO é descartada: foto, leituras e alertas ambientais
    # são gravados igual. O que não acontece é afirmar um diagnóstico.
    # O produtor vê a própria imagem no app, junto do motivo, e julga.
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

    # CRUZAMENTO COM O HISTÓRICO DA ESTUFA. O modelo de imagem não sabe
    # duvidar de si mesmo: medido em 2026-11-01, os logits de uma planta
    # com amarelamento nutricional ficam no mesmo patamar dos das
    # classes conhecidas (mediana 1,70 contra 1,89), então ele acusa
    # doença com confiança alta e nada na visão o contradiz.
    #
    # Fungo foliar precisa de molhamento prolongado para infectar. Se o
    # histórico mostra que isso não houve, a suspeita merece uma
    # ressalva. Ver app/core/pressao_infecciosa.py para os três pontos
    # cegos que limitam o que essa ressalva pode afirmar.
    #
    # A ressalva vai junto da RECOMENDAÇÃO, não como alerta separado: é
    # uma qualificação do diagnóstico e só faz sentido grudada nele.
    if resultado["classe"] in CLASSES_FUNGICAS:
        resultado["recomendacao"] = await _recomendacao_com_ressalva(
            sessao, device_id, resultado,
            capturado_em, temperatura_c_valor, umidade_ar_pct_valor,
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

        # Alerta de câmera, em vez do de doença. Severidade média: pede
        # conferência do equipamento, não ação no cultivo, e é o mesmo
        # critério usado para a suspeita de sensor de solo (ADR 0005).
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
