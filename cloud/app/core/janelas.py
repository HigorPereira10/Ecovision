"""
Diagnóstico por janela deslizante, agregado em um único rótulo.

Reduzir o quadro inteiro de 4608 × 2592 para 224 × 224 deixa o folíolo com
cerca de 43 pixels, e a acurácia cai para perto do acaso (80,7% com a
folha a 224 pixels, 47,4% a 56 pixels, em 249 imagens rotuladas). As
janelas de 896 pixels reduzidas para 224 reproduzem a escala do treino.

Devolve o mesmo dicionário de inference.rodar_inferencia (classe,
confianca, recomendacao, severidade), mais `votos` e `janelas`. A
geometria (JANELA_NATIVA, PASSO_NATIVO, ESCALA) deve ser a mesma de
ml/src/porta/avaliar.py e ml/src/dataset/extrair_janelas.py.
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

# Mesma geometria de ml/src/porta/avaliar.py; alterar nos dois lugares.
JANELA_NATIVA = 896
PASSO_NATIVO = 448
ESCALA = 2  # decodifica em metade da resolução, sem alterar o resultado

# Cobertura mínima de verde para uma janela ser aproveitada. Nas janelas
# rotuladas, o percentil 5 é 20,5% para folha sadia e 25,7% para folha com
# estresse; objetos verdes que não são folha (como um pote plástico) ficam
# entre 9% e 12%.
COBERTURA_VERDE_MINIMA = 0.18

# Mínimo de janelas aproveitáveis para afirmar um diagnóstico; com menos,
# um único voto ultrapassaria a fração de incidência sozinho.
JANELAS_MINIMAS = 6

# Agregação por incidência: vence a classe mais severa cuja fração de
# janelas atinge o limiar, mesmo que não seja a maioria. Média e maioria
# exigem que o problema domine o quadro e davam respostas diferentes para
# a mesma planta conforme o enquadramento.
ORDEM_SEVERIDADE = ("septoriose", "pinta_preta", "estresse_foliar", "saudavel")

# A fração precisa ficar acima da taxa de falso positivo do modelo (7% nos
# enquadramentos retidos do treino). Ao trocar o modelo, meça essa taxa de
# novo e ajuste a fração junto.
FRACAO_MINIMA_INCIDENCIA = 0.20

# A verificação de qualidade também roda por janela: uma janela quase toda
# escura pode ser classificada como "saudavel" com alta confiança mesmo
# quando o quadro inteiro passa na verificação.
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
    """Divide a captura em janelas já reduzidas para a entrada do modelo,
    com redimensionamento pelo vizinho mais próximo, como em
    inference.preprocessar_imagem."""
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
    """Classifica cada janela aproveitável e agrega em um rótulo.

    Vence a classe mais severa cuja fração de votos atinge
    FRACAO_MINIMA_INCIDENCIA. `confianca` é a probabilidade média da classe
    vencedora entre as janelas que votaram nela; a incidência vai no texto
    da recomendação e em `votos`.
    """
    recortes, _posicoes = recortar(bytes_imagem)
    if not recortes:
        return _sem_janela("A foto não pôde ser dividida para análise.")

    aproveitaveis = [r for r in recortes if _janela_aproveitavel(r) is None]
    if len(aproveitaveis) < JANELAS_MINIMAS:
        logger.warning(
            "Só %d das %d janelas servem para diagnóstico (mínimo %d). "
            "Nada é afirmado sobre a planta.",
            len(aproveitaveis), len(recortes), JANELAS_MINIMAS,
        )
        return _sem_janela(
            "Não foi possível encontrar folha suficiente na foto para "
            "analisar. Verifique se a câmera está apontada para a planta e "
            "se a iluminação acendeu na captura."
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

    # Classe mais severa acima do limiar; se nenhuma atingir, a mais votada.
    indice = int(np.bincount(vencedoras, minlength=len(_CLASSES_DO_MODELO)).argmax())
    for nome in ORDEM_SEVERIDADE:
        if nome in _CLASSES_DO_MODELO and fracoes.get(nome, 0.0) >= FRACAO_MINIMA_INCIDENCIA:
            indice = _CLASSES_DO_MODELO.index(nome)
            break

    votantes = probabilidades[vencedoras == indice]
    media = votantes.mean(axis=0) if len(votantes) else probabilidades.mean(axis=0)

    if indice >= len(_CLASSES_DO_MODELO):
        # .tflite trocado sem atualizar a lista de classes.
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

    # A incidência indica quanto da planta mostra o sinal e vai no texto;
    # `confianca` mantém o significado de confiança do modelo.
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
    """Nenhuma janela aproveitável: tratado como imagem inadequada, sem
    afirmar diagnóstico."""
    return {
        "classe": CLASSE_IMAGEM_INADEQUADA,
        "confianca": 0.0,
        "recomendacao": motivo,
        "severidade": None,
        "votos": {},
        "janelas": 0,
        "incidencia": 0.0,
    }
