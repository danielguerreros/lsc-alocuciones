"""Paso 4b: de fotogramas a tramos con intérprete.

Un fotograma cuenta si hay un cuerpo con el tamaño y la posición de un intérprete en su recuadro;
así se descartan las personas de las tomas de apoyo. Se rellenan huecos cortos y se descartan tramos cortos.
"""
import argparse
import csv
import json

from comun import carpeta

HOMBROS = (0.2, 0.4)   # ancho de hombros / ancho de la región
NARIZ_X = (0.25, 0.65)
NARIZ_Y = (0.15, 0.45)


def es_interprete(r: dict) -> bool:
    if r["pose"] != "1":
        return False
    sw, nx, ny = float(r["shoulder_w"]), float(r["nose_x"]), float(r["nose_y"])
    return HOMBROS[0] <= sw <= HOMBROS[1] and NARIZ_X[0] <= nx <= NARIZ_X[1] and NARIZ_Y[0] <= ny <= NARIZ_Y[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video_id")
    ap.add_argument("--hueco", type=int, default=3, help="fotogramas sin detección que se rellenan")
    ap.add_argument("--min-tramo", type=float, default=10.0, help="segundos")
    args = ap.parse_args()
    d = carpeta(args.video_id)
    rows = list(csv.DictReader((d / "deteccion.csv").open()))
    t = [float(r["t"]) for r in rows]
    paso = t[1] - t[0]
    s = [int(es_interprete(r)) for r in rows]

    i = 0
    while i < len(s):  # rellenar huecos cortos entre detecciones
        if s[i]:
            i += 1
            continue
        j = i
        while j < len(s) and not s[j]:
            j += 1
        if 0 < i and j < len(s) and j - i <= args.hueco:
            s[i:j] = [1] * (j - i)
        i = j

    tramos, ini = [], None
    for k, v in enumerate(s + [0]):
        if v and ini is None:
            ini = k
        if not v and ini is not None:
            a = max(0.0, t[ini] - paso / 2)
            b = min(t[k - 1] + paso / 2, t[-1] + paso)
            if b - a >= args.min_tramo:
                tramos.append([round(a, 1), round(b, 1)])
            ini = None
    (d / "tramos.json").write_text(json.dumps(tramos))
    total = sum(b - a for a, b in tramos)
    print(f"{sum(s)} de {len(s)} fotogramas con intérprete | tramos {tramos} | {total:.0f}s")


if __name__ == "__main__":
    main()
