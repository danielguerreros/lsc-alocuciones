"""Paso 3: descarga subtítulos en español (manuales y automáticos) en formato json3."""
import argparse
from pathlib import Path

import yt_dlp

SOURCES = ["presidencia", "caracol", "rcn"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=SOURCES, default="presidencia")
    ap.add_argument("--ids", default=None, help="por defecto data/manifests/<source>/candidate_ids.txt")
    ap.add_argument("--cookies-from-browser", default=None)
    ap.add_argument("--sleep", type=float, default=3.0)
    args = ap.parse_args()
    OUT = Path("data/subs") / args.source

    ids = [l.strip() for l in Path(args.ids or Path("data/manifests") / args.source / "candidate_ids.txt").read_text().splitlines() if l.strip()]
    OUT.mkdir(parents=True, exist_ok=True)
    opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["es.*", "es"],
        "subtitlesformat": "json3",
        "outtmpl": str(OUT / "%(id)s.%(ext)s"),
        "sleep_interval": args.sleep,
        "ignoreerrors": True,
        "quiet": True,
    }
    if args.cookies_from_browser:
        opts["cookiesfrombrowser"] = (args.cookies_from_browser,)
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([f"https://www.youtube.com/watch?v={i}" for i in ids])
    print(f"Subtítulos en {OUT}: {len(list(OUT.glob('*.json3')))} archivos")


if __name__ == "__main__":
    main()
