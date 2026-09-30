"""Paso 2b: fecha de subida y duración de cada candidato (el listado del canal no las trae).

Consulta video por video, en serie y con pausa, porque YouTube bloquea las ráfagas
("Sign in to confirm you're not a bot"). Es reanudable: los IDs ya presentes en
metadata.tsv no se vuelven a consultar. Después, re-correr el paso 2 aplica --min-duration.
"""
import argparse
import csv
import time
from pathlib import Path

import yt_dlp

SOURCES = ["presidencia", "caracol", "rcn", "canal1"]
FIELDS = ["id", "upload_date", "duration", "title"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=SOURCES, default="presidencia")
    ap.add_argument("--ids", default=None, help="por defecto data/manifests/<source>/candidate_ids.txt")
    ap.add_argument("--cookies-from-browser", default=None, help="p. ej. chrome")
    ap.add_argument("--cookies", default=None, help="archivo cookies.txt (formato Netscape)")
    ap.add_argument("--sleep", type=float, default=3.0)
    args = ap.parse_args()
    man = Path("data/manifests") / args.source
    META = man / "metadata.tsv"

    ids = [l.strip() for l in Path(args.ids or man / "candidate_ids.txt").read_text().splitlines() if l.strip()]
    done = set()
    if META.exists():
        with META.open(encoding="utf-8") as f:
            done = {r["id"] for r in csv.DictReader(f, delimiter="\t")}
    todo = [i for i in ids if i not in done]
    print(f"{len(todo)} por consultar ({len(done)} ya en {META})")

    opts = {"quiet": True, "no_warnings": True, "extractor_args": {"youtube": {"lang": ["es"]}}}
    if args.cookies_from_browser:
        opts["cookiesfrombrowser"] = (args.cookies_from_browser,)
    if args.cookies:
        opts["cookiefile"] = args.cookies

    new_file = not META.exists()
    with META.open("a", newline="", encoding="utf-8") as f, yt_dlp.YoutubeDL(opts) as ydl:
        w = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t")
        if new_file:
            w.writeheader()
        for n, vid in enumerate(todo, 1):
            try:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False, process=False)
            except yt_dlp.utils.DownloadError as e:
                print(f"[{n}/{len(todo)}] {vid}: {e}")
                if "not a bot" in str(e):
                    raise SystemExit("YouTube bloqueó las consultas: usa --cookies-from-browser o --cookies")
                continue
            w.writerow({
                "id": vid,
                "upload_date": info.get("upload_date") or "",
                "duration": info.get("duration") or "",
                "title": (info.get("title") or "").replace("\t", " ").replace("\n", " "),
            })
            f.flush()
            print(f"[{n}/{len(todo)}] {vid} {info.get('upload_date')} {info.get('duration')}s")
            time.sleep(args.sleep)


if __name__ == "__main__":
    main()
