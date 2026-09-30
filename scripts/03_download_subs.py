"""Paso 3: descarga subtítulos en español (manuales y automáticos) en formato json3."""
import argparse
from pathlib import Path

import yt_dlp

MAN = Path("data/manifests")
OUT = Path("data/subs")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default=str(MAN / "candidate_ids.txt"))
    ap.add_argument("--cookies-from-browser", default=None)
    ap.add_argument("--sleep", type=float, default=3.0)
    args = ap.parse_args()

    ids = [l.strip() for l in Path(args.ids).read_text().splitlines() if l.strip()]
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
