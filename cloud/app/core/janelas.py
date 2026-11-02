"""
cloud/app/core/janelas.py

Diagnóstico por JANELA DESLIZANTE, agregado num rótulo só.

POR QUE ISTO EXISTE
-------------------
A câmera entrega 4608x2592 e o caminho atual reduz o quadro inteiro
para 224x224. É uma redução de 20,6 vezes, e o folíolo chega ao modelo
com cerca de 43 px mesmo com o vaso na distância certa de 20 cm. Medido
em 2026-10-29 sobre 249 imagens rotuladas, com o acaso em 33,3%:

    folha com 224 px na entrada .... 80,7% de acurácia
    folha com 112 px ............... 62,7%
    folha com  56 px ............... 47,4%

O quadro inteiro opera na faixa do acaso. A janela de 896 px nativos
reduzida para 224 dá redução de 4 vezes, que é o regime de treino: o
mesmo folíolo chega com 222 px.

O efeito, medido na captura de 2026-11-02 com o modelo de domínio
próprio:

    quadro inteiro ... septoriose 38,9%, e TROCA para estresse_foliar
                       só por mudar o filtro de redimensionamento
    por janela ....... 23 estresse, 12 saudável, 1 fúngica, estável

No quadro inteiro o modelo está indeciso e qualquer perturbação vira
troca de rótulo. Na janela ele é firme.

O CONTRATO NÃO MUDA
-------------------
Esta função devolve o MESMO dicionário que inference.rodar_inferencia:
classe, confianca, recomendacao, severidade. O app continua recebendo
um rótulo só e não precisa de alteração nenhuma.

A contagem de votos vai junto, em `votos`, para quem quiser o mapa
depois sem refazer a conta. O caminho de rótulo único é uma
simplificação consciente: a planta é mista, e o rótulo agregado perde
essa informação. Ver "O QUE ESTA AGREGAÇÃO PERDE" abaixo.

Relação com o resto do sistema:
- Chamado por app/api/routes/diagnostico.py quando
  settings.DIAGNOSTICO_POR_JANELA estiver ligado.
- A geometria (JANELA_NATIVA, PASSO_NATIVO, ESCALA) tem que ser a MESMA
  de ml/src/porta/avaliar.py e ml/src/dataset/extrair_janelas.py, senão
  o modelo recebe uma escala diferente daquela em que foi treinado.
"""

from __future__ import annotations

import io
import logging
from typing import Any

import numpy as np
from PIL import Image

from app.core.inference import (
    BRILHO_MINIMO,
    CLASSE_IMAGEM_INADEQUADA,
    TAMANHO_ENTRADA,
    TEXTURA_MINIMA,
    _CLASSES_DO_MODELO,
    _INFO_POR_CLASSE,
)

logger = logging.getLogger("ecovision.cloud.janelas")

# Mesma geometria de ml/src/porta/avaliar.py. NÃO alterar sem alterar lá.
JANELA_NATIVA = 896
PASSO_NATIVO = 448
ESCALA = 2  # decodifica em metade: economiza memória sem mudar o resultado

# Cobertura mínima de verde para a janela valer diagnóstico. Abaixo
# disso é caule, fundo, vaso ou fruto, e um diagnóstico ali não
# significa nada. Mesmo limiar de ml/src/dataset/extrair_janelas.py.
COBERTURA_VERDE_MINIMA = 0.08

# AGREGAÇÃO POR INCIDÊNCIA, NÃO POR MAIORIA NEM POR MÉDIA
# --------------------------------------------------------
# Uma planta não precisa estar inteira doente para estar doente. Em
# fitopatologia a incidência se mede pela porcentagem de tecido
# afetado, e o limiar de ação é baixo. Esperar que a lesão domine o
# quadro é esperar tarde demais.
#
# Média e maioria falham pelo mesmo motivo: exigem que o problema seja
# a condição DOMINANTE. Medido em 2026-11-02 sobre cinco enquadramentos
# da MESMA planta no mesmo dia, as duas regras davam respostas
# diferentes conforme o ângulo (saudável em C e E, estresse em D e nas
# capturas noturnas). Um diagnóstico que muda com o ângulo da câmera
# não é diagnóstico.
#
# A regra por incidência deu `estresse_foliar` nos cinco, que é a
# resposta certa: é a mesma planta.
ORDEM_SEVERIDADE = ("septoriose", "pinta_preta", "estresse_foliar", "saudavel")

# DE ONDE SAI ESTE NÚMERO, E POR QUE ELE NÃO PODE SER MEXIDO SOZINHO
# ------------------------------------------------------------------
# A fração tem que ficar acima da taxa de FALSO POSITIVO do modelo,
# senão um punhado de votos positivos é ruído, não sinal.
#
# Medido no conjunto de teste reservado (enquadramentos C e E, 34
# janelas que o modelo nunca viu no treino):
#
#     de 14 janelas realmente saudáveis
#         chamadas de estresse ....  1  (7%)
#         chamadas de doença ......  1  (7%)
#     de 20 janelas realmente com estresse
#         detectadas .............. 12  (60%)
#
# Com 7% de falso positivo, 20% fica três vezes acima do ruído.
#
# AO TROCAR O MODELO, MEÇA A TAXA DE FALSO POSITIVO DE NOVO e ajuste
# esta fração junto. Um modelo mais agressivo precisa de fração maior.
# Mexer num sem o outro transforma ruído em diagnóstico.
FRACAO_MINIMA_INCIDENCIA = 0.20

# A GUARDA DE QUALIDADE PRECISA RODAR POR JANELA, não só no quadro.
#
# Medido por Grad-CAM em 2026-11-02: uma janela quase toda preta, com um
# fruto no canto, saiu como "saudavel" com 90% de confiança. O quadro
# inteiro passou na guarda (brilho médio bom), mas aquela janela
# específica não tinha nada visível. Sem esta checagem, o viés do escuro
# documentado no ADR 0016 volta uma vez por janela.
BRILHO_MINIMO_JANELA = BRILHO_MINIMO
TEXTURA_MINIMA_JANELA = TEXTURA_MINIMA


def _cobertura_verde(recorte: np.ndarray) -> float:
    r, g, b = recorte[..., 0], recorte[..., 1], recorte[..., 2]
    maximo = recorte.max(axis=2)
    minimo = recorte.min(axis=2)
    saturacao = np.where(maximo > 0, (maximo - minimo) / np.maximum(maximo, 1), 0)
    verde = (g > r * 1.06) & (g > b * 1.06) & (saturacao > 0.18) & (maximo > 45)
    return float(verde.mean())


def _janela_aproveitavel(recorte: np.ndarray) -> str | None:
    """Devolve o motivo da recusa, ou None se a janela serve."""
    cinza = recorte.mean(axis=2)
    if float(cinza.mean()) < BRILHO_MINIMO_JANELA:
        return "escura"
    if float(cinza.std()) < TEXTURA_MINIMA_JANELA:
        return "sem detalhe"
    if _cobertura_verde(recorte) < COBERTURA_VERDE_MINIMA:
        return "sem folha"
    return None


def recortar(bytes_imagem: bytes) -> tuple[list[np.ndarray], list[tuple[int, int, int]]]:
    """Divide a captura em janelas já reduzidas para a entrada do modelo.

    O redimensionamento usa NEAREST, igual a inference.preprocessar_imagem.
    Não trocar: medido em 2026-10-24, com BILINEAR duas de seis imagens
    de campo trocaram de classe, e NEAREST ganha 7 pontos no domínio de
    campo, que é onde este sistema opera.
    """
    imagem = Image.open(io.BytesIO(bytes_imagem))
    imagem.draft("RGB", (imagem.size[0] // ESCALA, imagem.size[1] // ESCALA))
    imagem = imagem.convert("RGB")

    lado = JANELA_NATIVA // ESCALA
    passo = PASSO_NATIVO // ESCALA
    largura, altura = imagem.size
    if lado > min(largura, altura):
        lado = min(largura, altura)
        passo = max(1, lado // 2)

    recortes: list[np.ndarray] = []
    posicoes: list[tuple[int, int, int]] = []
    for topo in range(0, altura - lado + 1, passo):
        for esquerda in range(0, largura - lado + 1, passo):
            pedaco = imagem.crop((esquerda, topo, esquerda + lado, topo + lado))
            recortes.append(
                np.asarray(pedaco.resize(TAMANHO_ENTRADA, Image.Resampling.NEAREST), np.float32)
            )
            posicoes.append((esquerda, topo, lado))
    return recortes, posicoes


def diagnosticar_por_janelas(interpretador: Any, bytes_imagem: bytes) -> dict:
    """Roda o modelo em cada janela aproveitável e agrega num rótulo só.

    Devolve o MESMO contrato de inference.rodar_inferencia, mais
    `votos` e `janelas` para quem quiser a distribuição.

    A agregação é por INCIDÊNCIA: vence a classe mais severa cuja
    fração de votos passe de FRACAO_MINIMA_INCIDENCIA. Ver a nota
    daquela constante para por que não é média nem maioria, e de onde
    sai o número.

    `confianca` continua significando a confiança do MODELO, não a
    incidência: é a probabilidade média da classe vencedora entre as
    janelas que votaram nela. A incidência vai no texto da recomendação
    e em `votos`, porque é ela que diz ao produtor quanto da planta
    está afetado.
    """
    recortes, _posicoes = recortar(bytes_imagem)
    if not recortes:
        return _sem_janela("A foto não pôde ser dividida para análise.")

    aproveitaveis = [r for r in recortes if _janela_aproveitavel(r) is None]
    if not aproveitaveis:
        logger.warning(
            "Nenhuma das %d janelas serve para diagnóstico (escuras, sem "
            "detalhe ou sem folha).", len(recortes),
        )
        return _sem_janela(
            "Não foi possível encontrar folha analisável na foto. Verifique "
            "se a câmera está apontada para a planta e se a iluminação "
            "acendeu na captura."
        )

    entrada = interpretador.get_input_details()[0]["index"]
    saida = interpretador.get_output_details()[0]["index"]
    probabilidades = []
    for recorte in aproveitaveis:
        interpretador.set_tensor(entrada, recorte[None])
        interpretador.invoke()
        probabilidades.append(interpretador.get_tensor(saida)[0].copy())
    probabilidades = np.asarray(probabilidades)

    vencedoras = probabilidades.argmax(axis=1)
    total = len(vencedoras)
    fracoes = {
        nome: float((vencedoras == i).sum()) / total
        for i, nome in enumerate(_CLASSES_DO_MODELO)
    }

    # A classe mais severa que passe do limiar. Se nenhuma passar, cai
    # na mais votada, que nesse caso é necessariamente `saudavel` ou
    # uma classe residual: nada atingiu incidência relevante.
    indice = int(np.bincount(vencedoras, minlength=len(_CLASSES_DO_MODELO)).argmax())
    for nome in ORDEM_SEVERIDADE:
        if nome in _CLASSES_DO_MODELO and fracoes.get(nome, 0.0) >= FRACAO_MINIMA_INCIDENCIA:
            indice = _CLASSES_DO_MODELO.index(nome)
            break

    votantes = probabilidades[vencedoras == indice]
    media = votantes.mean(axis=0) if len(votantes) else probabilidades.mean(axis=0)

    if indice >= len(_CLASSES_DO_MODELO):
        # Mesma proteção de inference.rodar_inferencia: .tflite trocado
        # sem atualizar a lista de classes.
        logger.error(
            "Modelo devolveu indice %d, fora de _CLASSES_DO_MODELO (%d classes).",
            indice, len(_CLASSES_DO_MODELO),
        )
        return {
            "classe": f"classe_{indice}", "confianca": float(media[indice]),
            "recomendacao": None, "severidade": None,
            "votos": {}, "janelas": len(aproveitaveis), "incidencia": 0.0,
        }

    classe = _CLASSES_DO_MODELO[indice]
    recomendacao, severidade = _INFO_POR_CLASSE.get(classe, (None, None))
    votos = {
        nome: int((vencedoras == i).sum())
        for i, nome in enumerate(_CLASSES_DO_MODELO)
        if (vencedoras == i).any()
    }
    incidencia = fracoes[classe]

    # A incidência é o número acionável: diz QUANTO da planta mostra o
    # sinal. Ela entra no texto porque `confianca` significa outra
    # coisa (quanto o modelo confia onde detectou), e trocar o sentido
    # daquele campo quebraria a leitura de quem já usa o app.
    if classe != "saudavel":
        aviso = (
            f"Sinal observado em {int(round(incidencia * total))} de {total} "
            f"regiões analisadas da planta ({incidencia * 100:.0f}%)."
        )
        recomendacao = f"{aviso} {recomendacao}" if recomendacao else aviso

    logger.info(
        "Diagnóstico por janela: %d/%d aproveitadas, votos=%s, "
        "incidência de %s = %.0f%%, confiança %.1f%%",
        len(aproveitaveis), len(recortes), votos, classe,
        incidencia * 100, media[indice] * 100,
    )
    return {
        "classe": classe,
        "confianca": float(media[indice]),
        "recomendacao": recomendacao,
        "severidade": severidade,
        "votos": votos,
        "janelas": len(aproveitaveis),
        "incidencia": float(incidencia),
    }


def _sem_janela(motivo: str) -> dict:
    """Nenhuma janela serviu. Trata como imagem inadequada, que é o
    caminho que o sistema já tem para 'não dá para afirmar nada',
    em vez de inventar um diagnóstico."""
    return {
        "classe": CLASSE_IMAGEM_INADEQUADA,
        "confianca": 0.0,
        "recomendacao": motivo,
        "severidade": None,
        "votos": {},
        "janelas": 0,
        "incidencia": 0.0,
    }
