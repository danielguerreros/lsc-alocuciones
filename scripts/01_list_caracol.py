"""Pasos 1+2 para Noticias Caracol: emisiones del mediodía (con intérprete de LSC en el set).

Las emisiones completas están en listas de reproducción anuales ("Emisiones Noticias Caracol AAAA");
el canal sube además decenas de clips diarios, así que no se lista el canal entero.
En la revisión manual solo la emisión del mediodía (entre semana y fin de semana) tiene intérprete;
la de la mañana y la central no.
"""
import argparse
import csv
import re
import unicodedata
from pathlib import Path

import yt_dlp

OUT = Path("data/manifests/caracol")
PLAYLISTS = {
    "2025": "PLazv5nJTMUQayFG8AtdHljhWlAyiprHKN",  # empieza el 15 de septiembre de 2025
    "2026": "PLazv5nJTMUQYd6ANhFDqid0t8z58mOPX2",
}
MESES = {m: i for i, m in enumerate(
    "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split(), 1)}
FIELDS = ["id", "title", "upload_date", "duration", "live_status", "tab", "url"]


def norm(s: str) -> str:
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()


def date_from_title(title: str) -> str:
    """'(15 de septiembre 2025)' o '(1 de enero de 2026)' -> '20250915'."""
    m = re.search(r"\((\d{1,2}) de (\w+) (?:de )?(\d{4})\)", norm(title))
    if not m or m.group(2) not in MESES:
        return ""
    return f"{m.group(3)}{MESES[m.group(2)]:02d}{int(m.group(1)):02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pattern", default="mediodia", help="regex sobre el título normalizado")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    pat = re.compile(args.pattern)

    opts = {
        "extract_flat": "in_playlist", "quiet": True, "skip_download": True,
        "extractor_args": {"youtube": {"lang": ["es"]}},
    }
    rows = []
    with yt_dlp.YoutubeDL(opts) as ydl:
        for year, pl in PLAYLISTS.items():
            info = ydl.extract_info(f"https://www.youtube.com/playlist?list={pl}", download=False)
            for e in info.get("entries") or []:
                if not e or not e.get("id"):
                    continue
                rows.append({
                    "id": e["id"],
                    "title": (e.get("title") or "").replace("\t", " ").replace("\n", " "),
                    "upload_date": e.get("upload_date") or date_from_title(e.get("title") or ""),
                    "duration": e.get("duration") or "",
                    "live_status": e.get("live_status") or "",
                    "tab": f"emisiones_{year}",
                    "url": f"https://www.youtube.com/watch?v={e['id']}",
                })

    seen, cand = set(), []
    for r in rows:
        if r["id"] not in seen and pat.search(norm(r["title"])):
            seen.add(r["id"])
            cand.append(r)
    for name, data in [("channel_emisiones.tsv", rows), ("candidates.tsv", cand)]:
        with (OUT / name).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t")
            w.writeheader()
            w.writerows(data)
    (OUT / "candidate_ids.txt").write_text("\n".join(r["id"] for r in cand) + "\n")
    print(f"{len(cand)} emisiones del mediodía de {len(rows)} -> {OUT/'candidates.tsv'}")


if __name__ == "__main__":
    main()
