"""
Avalia os modelos exportados nas partições de teste das bases públicas
(PlantVillage e PlantDoc), sem nenhum ajuste.

As partições de teste não participaram do treino de nenhum dos dois
modelos: ajuste_dois_dominios.py e ajuste_dominio_proprio.py usam apenas
as pastas "train". O pré-processamento é o mesmo da API
(cloud/app/core/inference.py): 224 x 224, vizinho mais próximo, pixels de
0 a 255.

Uso:
    python ml/src/training/avaliar_bases_publicas.py
"""

import hashlib
import json
import math
import os
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import numpy as np
import tensorflow as tf
from PIL import Image

RAIZ = Path(__file__).resolve().parents[3]
DADOS = RAIZ / "ml" / "data"
MODELOS = {
    "tres_classes": (RAIZ / "ml" / "models" / "modelo.tflite",
                     ["septoriose", "pinta_preta", "saudavel"]),
    "quatro_classes": (RAIZ / "ml" / "models" / "modelo_dominio.tflite",
                       ["septoriose", "pinta_preta", "saudavel", "estresse_foliar"]),
}
DOMINIOS = {
    "laboratorio": (DADOS / "plantvillage_tomate" / "test",
                    {"mancha_septoria": "septoriose", "pinta_preta": "pinta_preta",
                     "folhas_saudaveis": "saudavel"}),
    "campo": (DADOS / "plantdoc_tomate" / "test",
              {"distrator_septoria": "septoriose", "pinta_preta": "pinta_preta",
               "saudavel": "saudavel"}),
}
VERDADEIRAS = ["septoriose", "pinta_preta", "saudavel"]
SAIDA = RAIZ / "ml" / "models" / "metricas_bases_publicas.json"


def sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def wilson(acertos: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return (float("nan"), float("nan"))
    p = acertos / total
    den = 1 + z * z / total
    centro = (p + z * z / (2 * total)) / den
    margem = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / den
    return (centro - margem, centro + margem)


def preprocessar(caminho: Path) -> np.ndarray:
    imagem = Image.open(caminho).convert("RGB").resize((224, 224), Image.Resampling.NEAREST)
    return np.expand_dims(np.asarray(imagem, dtype=np.float32), axis=0)


def avaliar(modelo: Path, classes: list[str]) -> dict:
    interp = tf.lite.Interpreter(model_path=str(modelo))
    interp.allocate_tensors()
    entrada = interp.get_input_details()[0]["index"]
    saida = interp.get_output_details()[0]["index"]
    resultado = {}
    for dominio, (pasta, mapa) in DOMINIOS.items():
        matriz = {v: {c: 0 for c in classes} for v in VERDADEIRAS}
        for sub, verdadeira in mapa.items():
            for arquivo in sorted((pasta / sub).iterdir()):
                interp.set_tensor(entrada, preprocessar(arquivo))
                interp.invoke()
                prevista = classes[int(np.argmax(interp.get_tensor(saida)[0]))]
                matriz[verdadeira][prevista] += 1
        total = sum(sum(linha.values()) for linha in matriz.values())
        acertos = sum(matriz[v][v] for v in VERDADEIRAS)
        doentes = matriz["septoriose"], matriz["pinta_preta"]
        n_doentes = sum(sum(l.values()) for l in doentes)
        fn = sum(l["saudavel"] for l in doentes)
        n_sadias = sum(matriz["saudavel"].values())
        fp = n_sadias - matriz["saudavel"]["saudavel"] - matriz["saudavel"].get("estresse_foliar", 0)
        resultado[dominio] = {
            "matriz": matriz,
            "acertos": acertos,
            "total": total,
            "acuracia": round(acertos / total, 4),
            "ic95_wilson": [round(x, 4) for x in wilson(acertos, total)],
            "falso_negativo": {"n": fn, "de": n_doentes, "taxa": round(fn / n_doentes, 4),
                               "ic95_wilson": [round(x, 4) for x in wilson(fn, n_doentes)]},
            "falso_positivo_de_doenca": {"n": fp, "de": n_sadias, "taxa": round(fp / n_sadias, 4),
                                         "ic95_wilson": [round(x, 4) for x in wilson(fp, n_sadias)]},
            "previstas_estresse_foliar": sum(l.get("estresse_foliar", 0) for l in matriz.values()),
        }
    return resultado


def main() -> None:
    relatorio = {}
    for nome, (modelo, classes) in MODELOS.items():
        relatorio[nome] = {"arquivo": str(modelo.relative_to(RAIZ)).replace("\\", "/"),
                           "sha256": sha256(modelo), "classes": classes,
                           "dominios": avaliar(modelo, classes)}
        for dominio, r in relatorio[nome]["dominios"].items():
            print(f"{nome:15s} {dominio:12s} {r['acertos']}/{r['total']} = {r['acuracia']:.1%}"
                  f"  FN {r['falso_negativo']['n']}/{r['falso_negativo']['de']}"
                  f"  FP {r['falso_positivo_de_doenca']['n']}/{r['falso_positivo_de_doenca']['de']}"
                  f"  estresse {r['previstas_estresse_foliar']}")
    SAIDA.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")
    print("salvo em", SAIDA.relative_to(RAIZ))


if __name__ == "__main__":
    main()
