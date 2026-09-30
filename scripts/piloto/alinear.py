"""Paso 7: agrupa las palabras de Whisper en oraciones y asigna a cada una su ventana de pose.

La ventana va de audio_ini + --retraso-ini a audio_fin + --retraso-fin, porque el intérprete va detrás
de la voz. Los valores por defecto (1 s y 3 s) son una suposición: falta medir el retraso real.
"""
import argparse
import csv
import json

import numpy as np

from comun import carpeta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video_id")
    ap.add_argument("--retraso-ini", type=float, default=1.0)
    ap.add_argument("--retraso-fin", type=float, default=3.0)
    args = ap.parse_args()
    d = carpeta(args.video_id)
    z = np.load(d / "pose.npz")
    t = z["t"]
    tramos = json.loads((d / "tramos.json").read_text())
    w = json.loads((d / "whisper.json").read_text())

    oraciones, cur = [], []
    for x in (x for s in w["segments"] for x in s["words"]):
        cur.append(x)
        if x["word"].endswith((".", "?", "!")):
            oraciones.append(cur)
            cur = []
    if cur:
        oraciones.append(cur)

    rows = []
    for i, s in enumerate(oraciones):
        a, b = s[0]["start"], s[-1]["end"]
        pa, pb = a + args.retraso_ini, b + args.retraso_fin
        fa, fb = (int(v) for v in np.searchsorted(t, [pa, pb]))
        manos = ~np.isnan(z["left_hand"][fa:fb, 0, 0]) | ~np.isnan(z["right_hand"][fa:fb, 0, 0])
        rows.append({"id": i, "texto": " ".join(x["word"] for x in s),
                     "audio_ini": round(a, 2), "audio_fin": round(b, 2), "pose_ini": round(pa, 2), "pose_fin": round(pb, 2),
                     "frame_ini": fa, "frame_fin": fb,
                     "en_tramo": int(any(ta <= pa and pb <= tb for ta, tb in tramos)),
                     "cobertura_manos": round(float(manos.mean()), 2) if fb > fa else 0.0, "palabras": len(s)})
    with (d / "alineacion.tsv").open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t")
        wr.writeheader()
        wr.writerows(rows)
    ok = [r for r in rows if r["en_tramo"]]
    print(f"{len(rows)} oraciones | {len(ok)} dentro de un tramo con intérprete -> {d / 'alineacion.tsv'}")


if __name__ == "__main__":
    main()
