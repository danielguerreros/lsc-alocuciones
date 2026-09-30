"""Paso 2 (Presidencia): filtra candidatos a alocución por palabras clave del título y duración."""
import argparse
import re
import unicodedata
from pathlib import Path

import pandas as pd

MAN = Path("data/manifests/presidencia")
DEFAULT_KW = ["alocucion", "prevencion y accion"]  # en la revisión manual, los únicos con intérprete
# Primera alocución (oct. 2016) desde la que el intérprete aparece de forma constante en los videos.
# Antes, lo subido a YouTube era la señal limpia, sin recuadro de LSC.
FIRST_WITH_INTERPRETER = "EIwUgiJD5X0"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return s.lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", nargs="+", default=DEFAULT_KW)
    ap.add_argument("--min-duration", type=int, default=180, help="segundos")
    ap.add_argument("--since-id", default=FIRST_WITH_INTERPRETER,
                    help="descarta videos subidos antes de este ID ('' para no cortar)")
    args = ap.parse_args()

    frames = []
    for p in sorted(MAN.glob("channel_*.tsv")):
        t = pd.read_csv(p, sep="\t", dtype=str)
        # Las pestañas vienen de más nuevo a más antiguo: el corte es la posición del ID ancla.
        if args.since_id and args.since_id in set(t["id"]):
            t = t.iloc[: t.index[t["id"] == args.since_id][0] + 1]
        frames.append(t)
    if not frames:
        raise SystemExit("No hay manifiestos. Corre primero scripts/01_list_channel.py")
    df = pd.concat(frames).drop_duplicates("id")
    meta_path = MAN / "metadata.tsv"  # fecha y duración del paso 2b, si ya se corrió
    if meta_path.exists():
        meta = pd.read_csv(meta_path, sep="\t", dtype=str).drop_duplicates("id").set_index("id")
        for col in ["upload_date", "duration"]:
            df[col] = df["id"].map(meta[col]).fillna(df[col])
    pat = re.compile("|".join(re.escape(norm(k)) for k in args.keywords))
    df["kw_match"] = df["title"].fillna("").map(lambda t: bool(pat.search(norm(t))))
    dur = pd.to_numeric(df["duration"], errors="coerce")
    df["long_enough"] = dur.isna() | (dur >= args.min_duration)  # directos sin duración se conservan
    cand = df[df.kw_match & df.long_enough].drop(columns=["kw_match", "long_enough"])
    cand.to_csv(MAN / "candidates.tsv", sep="\t", index=False)
    (MAN / "candidate_ids.txt").write_text("\n".join(cand["id"]) + "\n")
    print(f"{len(cand)} candidatos de {len(df)} -> {MAN/'candidates.tsv'}")


if __name__ == "__main__":
    main()
