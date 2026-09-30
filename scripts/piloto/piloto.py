"""Corre el pipeline completo sobre un video: descarga, pasos 4 a 7.

    python scripts/piloto/piloto.py LGNC7_XOC34 --region 900,280,380,320

Cada paso corre en su propio proceso (OpenCV y faster-whisper no pueden convivir en el mismo en macOS)
y puede volver a correrse por separado: scripts/piloto/{detectar,tramos,transcribir,pose,alinear}.py <id>.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from comun import REGION_DEFECTO, carpeta

AQUI = Path(__file__).parent
PASOS = ["detectar", "tramos", "transcribir", "pose", "alinear"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video_id")
    ap.add_argument("--region", default=",".join(map(str, REGION_DEFECTO)), help="x,y,ancho,alto en 1280x720")
    ap.add_argument("--desde", choices=PASOS, default=PASOS[0], help="saltar la descarga y los pasos anteriores")
    ap.add_argument("--cookies-from-browser", default=None)
    args = ap.parse_args()
    d = carpeta(args.video_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "config.json").write_text(json.dumps({"region": [int(v) for v in args.region.split(",")]}))

    if args.desde == PASOS[0]:
        url = f"https://www.youtube.com/watch?v={args.video_id}"
        extra = ["--cookies-from-browser", args.cookies_from_browser] if args.cookies_from_browser else []
        for fmt, name in [("bv*[height<=720][ext=mp4]", "video_720p.%(ext)s"), ("ba[ext=webm]/ba", "audio.%(ext)s")]:
            subprocess.run(["yt-dlp", "-q", "--no-warnings", *extra, "-f", fmt, "-o", str(d / name), url], check=True)

    for paso in PASOS[PASOS.index(args.desde):]:
        print(f"== {paso}")
        subprocess.run([sys.executable, str(AQUI / f"{paso}.py"), args.video_id], check=True)


if __name__ == "__main__":
    main()
