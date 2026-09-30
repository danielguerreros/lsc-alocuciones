"""Pasos 1+2 para noticieros: emisiones del mediodía, las únicas con intérprete de LSC.

Las emisiones completas están en listas de reproducción ("Emisiones Noticias <canal> AAAA");
los canales suben además decenas de clips diarios, así que no se listan enteros.
En la revisión manual, las emisiones de la mañana y de la noche no tienen intérprete.
- Caracol: intérprete integrado en el set, presente en todos los fotogramas revisados.
- RCN: recuadro sobre el logo, intermitente (falta en aperturas y algunas pantallas divididas),
  y no se vio en muestras de 2022-2023. El paso 4 debe decidir qué tramos sirven.
"""
import argparse
import csv
import re
import unicodedata
from datetime import date
from pathlib import Path

import yt_dlp

SOURCES = {
    "caracol": {
        "pattern": r"mediodia",
        "playlists": {
            "2025": "PLazv5nJTMUQayFG8AtdHljhWlAyiprHKN",  # empieza el 15 de septiembre de 2025
            "2026": "PLazv5nJTMUQYd6ANhFDqid0t8z58mOPX2",
        },
    },
    "rcn": {
        "pattern": r"12[:.]30|mediodia",
        "playlists": {
            "general": "PLmVsDcVor9k2cadqllEJCj_bsP_Vw7fN8",  # 2022-2023, algunos títulos sin año
            "2023": "PLmVsDcVor9k0NpMc52jOBtQy-lbk7tDU4",
            "2024": "PLmVsDcVor9k1J79uRV2IQFH5iGVNLerbH",
            "2025": "PLmVsDcVor9k1vicMF5OoVCEU9TvDx3cRv",
            "2026": "PLmVsDcVor9k0y7alXsX_W7k1ZlUQUHZVq",
        },
    },
}
MESES = {m: i for i, m in enumerate(
    "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split(), 1)}
FIELDS = ["id", "title", "upload_date", "duration", "live_status", "tab", "url"]


def norm(s: str) -> str:
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()


DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


def date_from_title(title: str, near_year: int | None = None) -> str:
    """'(15 de septiembre 2025)', '/ martes 1 de enero del 2026' -> 'AAAAMMDD'.

    Sin año ('jueves 20 de octubre'), lo deduce del día de la semana entre near_year-1 y near_year+1
    (el año de la emisión vecina en la lista), si hay una única opción.
    """
    t = re.sub(r"\s+", " ", norm(title))
    for d, mes, y in re.findall(r"(\d{1,2}) ?(?:de )+(\w+) (?:del? )?(\d{4})", t):
        if mes in MESES:
            return f"{y}{MESES[mes]:02d}{int(d):02d}"
    if near_year is None:
        return ""
    for dia, d, mes in re.findall(r"(\w+) (\d{1,2}) ?(?:de )+(\w+)", t):
        if dia in DIAS and mes in MESES:
            ys = []
            for y in (near_year - 1, near_year, near_year + 1):
                try:
                    if date(y, MESES[mes], int(d)).weekday() == DIAS.index(dia):
                        ys.append(y)
                except ValueError:
                    pass
            if len(ys) == 1:
                return f"{ys[0]}{MESES[mes]:02d}{int(d):02d}"
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=SOURCES, required=True)
    ap.add_argument("--pattern", default=None, help="regex sobre el título normalizado")
    args = ap.parse_args()
    cfg = SOURCES[args.source]
    out = Path("data/manifests") / args.source
    out.mkdir(parents=True, exist_ok=True)
    pat = re.compile(args.pattern or cfg["pattern"])

    opts = {
        "extract_flat": "in_playlist", "quiet": True, "skip_download": True,
        "extractor_args": {"youtube": {"lang": ["es"]}},
    }
    rows = []
    with yt_dlp.YoutubeDL(opts) as ydl:
        for name, pl in cfg["playlists"].items():
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
                    "tab": f"emisiones_{name}",
                    "url": f"https://www.youtube.com/watch?v={e['id']}",
                })

    # Títulos sin año: usar el año de la emisión con fecha más cercana en la misma lista.
    for k, r in enumerate(rows):
        if r["upload_date"]:
            continue
        for off in range(1, len(rows)):
            near = [rows[n] for n in (k - off, k + off) if 0 <= n < len(rows)]
            near = [x for x in near if x["tab"] == r["tab"] and x["upload_date"]]
            if near:
                r["upload_date"] = date_from_title(r["title"], int(near[0]["upload_date"][:4]))
                break

    seen, cand = set(), []
    for r in rows:
        if r["id"] not in seen and pat.search(norm(r["title"])):
            seen.add(r["id"])
            cand.append(r)
    for name, data in [("channel_emisiones.tsv", rows), ("candidates.tsv", cand)]:
        with (out / name).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t")
            w.writeheader()
            w.writerows(data)
    (out / "candidate_ids.txt").write_text("\n".join(r["id"] for r in cand) + "\n")
    print(f"{len(cand)} emisiones del mediodía de {len(rows)} -> {out/'candidates.tsv'}")


if __name__ == "__main__":
    main()
