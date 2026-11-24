"""
Mede o tempo do diagnóstico por janela deslizante, por etapa.

Executa o mesmo caminho da API (cloud/app/core/inference.py e
cloud/app/core/janelas.py) sobre capturas do dispositivo em resolução
nativa, sem rede, Storage ou banco: verificação de qualidade, recorte em
janelas, filtro das janelas e inferência em todas as janelas aproveitáveis.
Duas passadas de aquecimento são descartadas.

Uso (na pasta cloud, com o ambiente da API):
    python scripts/medir_latencia_janelas.py <pasta com capturas .jpg> [--saida resultado.json]

As capturas usadas no trabalho estão no conjunto de dados publicado no
Zenodo (DOI 10.5281/zenodo.23646357).
"""

import argparse
import json
import platform
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core import inference, janelas  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
MODELO = RAIZ / "ml" / "models" / "modelo_dominio.tflite"
ETAPAS = ["Verificação de qualidade da imagem", "Recorte em janelas", "Filtro das janelas",
          "Inferência da rede neural, em todas as janelas", "Total"]


def medir_uma(interp, entrada, saida, bytes_imagem):
    t0 = time.perf_counter()
    inference.avaliar_qualidade_imagem(bytes_imagem)
    t1 = time.perf_counter()
    recortes, _ = janelas.recortar(bytes_imagem)
    t2 = time.perf_counter()
    aproveitaveis = [r for r in recortes if janelas._janela_aproveitavel(r) is None]
    t3 = time.perf_counter()
    for recorte in aproveitaveis:
        interp.set_tensor(entrada, recorte[None])
        interp.invoke()
        interp.get_tensor(saida)
    t4 = time.perf_counter()
    tempos = [(t1 - t0) * 1e3, (t2 - t1) * 1e3, (t3 - t2) * 1e3, (t4 - t3) * 1e3, (t4 - t0) * 1e3]
    return tempos, len(recortes), len(aproveitaveis)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("pasta", type=Path)
    parser.add_argument("--repeticoes", type=int, default=20)
    parser.add_argument("--maximo", type=int, default=6, help="número de capturas")
    parser.add_argument("--saida", type=Path, default=None)
    args = parser.parse_args()

    fotos = sorted(args.pasta.glob("*.jpg"))[: args.maximo]
    if not fotos:
        print(f"Nenhuma captura .jpg em {args.pasta}")
        return 1
    dados = [f.read_bytes() for f in fotos]
    interp = inference.carregar_modelo_tflite(str(MODELO))
    entrada = interp.get_input_details()[0]["index"]
    saida = interp.get_output_details()[0]["index"]

    for b in dados:  # aquecimento descartado
        medir_uma(interp, entrada, saida, b)
        medir_uma(interp, entrada, saida, b)

    amostras, aproveitadas = [], []
    for _ in range(args.repeticoes):
        for b in dados:
            tempos, _, aprov = medir_uma(interp, entrada, saida, b)
            amostras.append(tempos)
            aproveitadas.append(aprov)
    arr = np.array(amostras)

    resultado = {
        "maquina": platform.processor(), "python": platform.python_version(),
        "modelo": MODELO.name, "capturas": [f.name for f in fotos],
        "execucoes": len(arr), "janelas_aproveitadas_media": round(statistics.mean(aproveitadas), 1),
        "etapas_ms": {},
    }
    for i, nome in enumerate(ETAPAS):
        c = arr[:, i]
        resultado["etapas_ms"][nome] = {
            "media": round(float(c.mean()), 1), "mediana": round(float(np.percentile(c, 50)), 1),
            "p95": round(float(np.percentile(c, 95)), 1), "maximo": round(float(c.max()), 1)}
        print(f"{nome:48s} média {c.mean():7.1f}  mediana {np.percentile(c, 50):7.1f}"
              f"  p95 {np.percentile(c, 95):7.1f}  máx {c.max():7.1f}")
    if args.saida:
        args.saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
        print("salvo em", args.saida)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
