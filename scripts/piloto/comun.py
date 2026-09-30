"""Utilidades compartidas por los scripts del piloto (un video en data/piloto/<id>/)."""
import json
from pathlib import Path

PILOTO = Path("data/piloto")
# Región del intérprete (x, y, ancho, alto) en un video 1280x720. Esta es la de Presidencia 2024.
REGION_DEFECTO = [900, 280, 380, 320]


def carpeta(video_id: str) -> Path:
    return PILOTO / video_id


def config(d: Path) -> dict:
    p = d / "config.json"
    cfg = json.loads(p.read_text()) if p.exists() else {}
    cfg.setdefault("region", REGION_DEFECTO)
    return cfg
