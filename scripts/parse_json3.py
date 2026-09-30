"""Paso 3b: convierte json3 de YouTube en una tabla de palabras con tiempo de inicio (s)."""
import argparse
import json
from pathlib import Path

SOURCES = ["presidencia", "caracol", "rcn"]


def parse(path: Path) -> list[tuple[float, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    words = []
    for ev in data.get("events", []):
        t0 = ev.get("tStartMs", 0)
        for seg in ev.get("segs") or []:
            w = (seg.get("utf8") or "").strip()
            if w and w != "\n":
                words.append(((t0 + seg.get("tOffsetMs", 0)) / 1000, w))
    return words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=SOURCES, default="presidencia")
    args = ap.parse_args()
    SUBS = Path("data/subs") / args.source
    OUT = Path("data/words") / args.source
    OUT.mkdir(parents=True, exist_ok=True)
    for p in sorted(SUBS.glob("*.json3")):
        vid = p.name.split(".")[0]
        lang = ".".join(p.name.split(".")[1:-1])
        rows = parse(p)
        with (OUT / f"{vid}.{lang}.tsv").open("w", encoding="utf-8") as f:
            f.write("start\tword\n")
            f.writelines(f"{t:.3f}\t{w}\n" for t, w in rows)
        print(f"{p.name}: {len(rows)} palabras")


if __name__ == "__main__":
    main()
