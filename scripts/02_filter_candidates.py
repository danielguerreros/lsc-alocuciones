"""Paso 2: filtra candidatos a alocución por palabras clave del título y duración."""
import argparse
import re
import unicodedata
from pathlib import Path

import pandas as pd

MAN = Path("data/manifests")
DEFAULT_KW = ["alocucion", "mensaje del presidente", "declaracion", "consejo de ministros", "intervencion"]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return s.lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", nargs="+", default=DEFAULT_KW)
    ap.add_argument("--min-duration", type=int, default=180, help="segundos")
    args = ap.parse_args()

    frames = [pd.read_csv(p, sep="\t", dtype=str) for p in sorted(MAN.glob("channel_*.tsv"))]
    if not frames:
        raise SystemExit("No hay manifiestos. Corre primero scripts/01_list_channel.py")
    df = pd.concat(frames).drop_duplicates("id")
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
