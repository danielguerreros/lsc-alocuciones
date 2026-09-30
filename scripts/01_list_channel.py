"""Paso 1: inventario de videos y directos del canal (sin descargar nada)."""
import argparse
import csv
from pathlib import Path

import yt_dlp

CHANNEL = "https://www.youtube.com/@infopresidencia"
OUT = Path("data/manifests/presidencia")
FIELDS = ["id", "title", "upload_date", "duration", "live_status", "tab", "url"]


def list_tab(tab: str) -> list[dict]:
    # Sin lang=es YouTube devuelve títulos auto-traducidos según la región del cliente.
    opts = {
        "extract_flat": "in_playlist", "quiet": True, "skip_download": True,
        "extractor_args": {"youtube": {"lang": ["es"]}},
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"{CHANNEL}/{tab}", download=False)
    rows = []
    for e in info.get("entries") or []:
        if not e or not e.get("id"):
            continue
        rows.append({
            "id": e["id"],
            "title": (e.get("title") or "").replace("\t", " ").replace("\n", " "),
            "upload_date": e.get("upload_date") or "",
            "duration": e.get("duration") or "",
            "live_status": e.get("live_status") or "",
            "tab": tab,
            "url": f"https://www.youtube.com/watch?v={e['id']}",
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tabs", nargs="+", default=["videos", "streams"])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for tab in args.tabs:
        rows = list_tab(tab)
        path = OUT / f"channel_{tab}.tsv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t")
            w.writeheader()
            w.writerows(rows)
        print(f"{tab}: {len(rows)} entradas -> {path}")


if __name__ == "__main__":
    main()
