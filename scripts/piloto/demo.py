"""Genera los archivos de la página de demostración (docs/demo/) a partir de data/piloto/<id>/.

- Datos (se versionan): datos.json (detección, audio, transcripción, alineación) y pose.txt
  (pose a 15 fps, 1 byte por coordenada, en base64).
- Medios (no se versionan, ver la política de datos del README): interprete.mp4 con audio y los JPG.

    python scripts/piloto/piloto.py LGNC7_XOC34
    python scripts/piloto/demo.py LGNC7_XOC34
    python -m http.server -d docs/demo      # y abrir http://localhost:8000
"""
import argparse
import base64
import csv
import json
import subprocess
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from comun import carpeta, config
from tramos import es_interprete

H = mp.solutions.holistic
FM = mp.solutions.face_mesh
CARA = {"labios": FM.FACEMESH_LIPS, "ojo_izq": FM.FACEMESH_LEFT_EYE, "ojo_der": FM.FACEMESH_RIGHT_EYE,
        "ceja_izq": FM.FACEMESH_LEFT_EYEBROW, "ceja_der": FM.FACEMESH_RIGHT_EYEBROW}


def ffmpeg(*a):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *map(str, a)], check=True)


def datos(d: Path, out: Path, video_id: str):
    z = np.load(d / "pose.npz")
    t = z["t"]
    # pose compacta: cuerpo (hasta la cadera), manos y cara reducida, a la mitad de fps
    sel = np.arange(0, len(t), 2)
    fidx = sorted({i for g in CARA.values() for e in g for i in e})
    fmap = {v: k for k, v in enumerate(fidx)}
    pts = np.concatenate([z["pose"][sel][:, :25, :2], z["left_hand"][sel][:, :, :2],
                          z["right_hand"][sel][:, :, :2], z["face"][sel][:, fidx, :2]], axis=1)
    q = np.where(np.isnan(pts), 255, np.clip(np.round(pts * 254), 0, 254)).astype(np.uint8)
    (out / "pose.txt").write_text(base64.b64encode(q.tobytes()).decode())
    cobertura = {k: float(np.mean(~np.isnan(z[n][:, 0, 0])))
                 for k, n in [("cuerpo", "pose"), ("mano_izq", "left_hand"), ("mano_der", "right_hand")]}
    pose_meta = {"t0": float(t[0]), "fps": float(z["fps"]) / 2, "frames": int(len(sel)), "pts": int(pts.shape[1]),
                 "offsets": {"cuerpo": 0, "mano_izq": 25, "mano_der": 46, "cara": 67},
                 "edges": {"cuerpo": [[a, b] for a, b in H.POSE_CONNECTIONS if a < 25 and b < 25],
                           "mano": [[a, b] for a, b in H.HAND_CONNECTIONS],
                           "cara": [[fmap[a], fmap[b]] for g in CARA.values() for a, b in g]},
                 "cobertura": cobertura, "frames_total": int(len(t)), "fps_origen": float(z["fps"])}

    det = [{"t": float(r["t"]), "pose": int(r["pose"]), "ok": int(es_interprete(r)),
            "manos": int(r["lhand"]) + int(r["rhand"]), "cara": int(r["face"]),
            "sw": float(r["shoulder_w"]) if r["shoulder_w"] else None}
           for r in csv.DictReader((d / "deteccion.csv").open())]

    audio = next(d.glob("audio.*"))
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(audio), "-f", "s16le", "-ac", "1", "-ar", "8000", "-"],
                         capture_output=True, check=True).stdout
    s = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
    B = 4000  # 0,5 s a 8 kHz
    env = np.sqrt(np.mean(s[:len(s) // B * B].reshape(-1, B) ** 2, axis=1))

    w = json.loads((d / "whisper.json").read_text())
    num = {"audio_ini", "audio_fin", "pose_ini", "pose_fin", "cobertura_manos"}
    ent = {"id", "frame_ini", "frame_fin", "en_tramo", "palabras"}
    oraciones = [{k: float(v) if k in num else int(v) if k in ent else v for k, v in r.items()}
                 for r in csv.DictReader((d / "alineacion.tsv").open(), delimiter="\t")]
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                str(d / "video_720p.mp4")], capture_output=True, text=True).stdout)
    data = {"video": {"id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}", "duracion": round(dur, 2)},
            "region": config(d)["region"], "deteccion": det, "tramos": json.loads((d / "tramos.json").read_text()),
            "envolvente": (env / env.max()).round(3).tolist(), "env_paso": 0.5,
            "whisper": {"segmentos": [{"a": round(g["start"], 2), "b": round(g["end"], 2)} for g in w["segments"]],
                        "palabras": [{"a": round(x["start"], 2), "b": round(x["end"], 2), "w": x["word"]}
                                     for g in w["segments"] for x in g["words"]]},
            "oraciones": oraciones, "pose": pose_meta}
    (out / "datos.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    print(f"datos.json y pose.txt ({q.nbytes / 1e6:.1f} MB de pose) -> {out}")


def dibujar(img, pts, edges, color, grosor=2, radio=2):
    h, w = img.shape[:2]
    P = [None if np.isnan(x) else (int(x * w), int(y * h)) for x, y in pts[:, :2]]
    for a, b in edges:
        if a < len(P) and b < len(P) and P[a] and P[b]:
            cv2.line(img, P[a], P[b], color, grosor)
    for p in P:
        if p:
            cv2.circle(img, p, radio, color, -1)


def medios(d: Path, out: Path, falsos: list, oracion: int, t_region: float):
    x, y, w, h = config(d)["region"]
    tramos = json.loads((d / "tramos.json").read_text())
    a, b = tramos[0][0], tramos[-1][1]
    video, audio = d / "video_720p.mp4", next(d.glob("audio.*"))

    # recorte del intérprete con audio, liviano para la web
    ffmpeg("-ss", a, "-to", b, "-i", video, "-ss", a, "-to", b, "-i", audio, "-map", "0:v", "-map", "1:a",
           "-vf", f"crop={w}:{h}:{x}:{y},fps=15", "-c:v", "libx264", "-crf", "34", "-preset", "slow",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "48k", "-ac", "1", "-movflags", "+faststart",
           out / "interprete.mp4")
    # fotogramas completos con la región marcada: uno con intérprete y uno de la introducción
    caja = f"drawbox=x={x}:y={y}:w={w}:h={h}:color=0xF2B705@0.95:t=4,scale=960:-1"
    ffmpeg("-ss", t_region, "-i", video, "-frames:v", 1, "-vf", caja, "-q:v", 4, out / "fotograma_region.jpg")
    ffmpeg("-ss", min(30, a / 2), "-i", video, "-frames:v", 1, "-vf", caja, "-q:v", 4, out / "fotograma_intro.jpg")

    # hoja de recortes cada 20 s con lo que detectó el modelo
    det = {float(r["t"]): r for r in csv.DictReader((d / "deteccion.csv").open())}
    tiles = []
    for f in sorted((d / "crops").glob("*.jpg")):
        r = det[float(int(f.stem))]
        sw = r["shoulder_w"] if r["pose"] == "1" else "-"
        lab = f"{int(f.stem)}s P{r['pose']} M{int(r['lhand']) + int(r['rhand'])} C{r['face']} sw{sw}"
        tile = cv2.resize(cv2.imread(str(f)), (175, 148))
        bar = np.zeros((24, 175, 3), np.uint8)
        cv2.putText(bar, lab, (4, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 220, 255), 1, cv2.LINE_AA)
        tiles.append(cv2.copyMakeBorder(np.vstack([bar, tile]), 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(255, 255, 255)))
    cols = 8
    tiles += [np.full_like(tiles[0], 255)] * (-len(tiles) % cols)
    cv2.imwrite(str(out / "recortes.jpg"), np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]),
                [cv2.IMWRITE_JPEG_QUALITY, 85])

    # falsos positivos: lo que el modelo "vio" en tomas de apoyo
    holistic = H.Holistic(static_image_mode=True, model_complexity=1)
    du = mp.solutions.drawing_utils
    spec = du.DrawingSpec((0, 183, 242), 2, 2)
    cap = cv2.VideoCapture(str(video))
    for t in falsos:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        _, fr = cap.read()
        c = fr[y:y + h, x:x + w].copy()
        r = holistic.process(cv2.cvtColor(c, cv2.COLOR_BGR2RGB))
        if r.pose_landmarks:
            du.draw_landmarks(c, r.pose_landmarks, H.POSE_CONNECTIONS, spec, spec)
        cv2.imwrite(str(out / f"falso_{t}.jpg"), c, [cv2.IMWRITE_JPEG_QUALITY, 82])

    # hoja de pose de una oración: cada 25 fotogramas, con el esqueleto dibujado
    z = np.load(d / "pose.npz")
    o = list(csv.DictReader((d / "alineacion.tsv").open(), delimiter="\t"))[oracion]
    fa, fb = int(o["frame_ini"]), int(o["frame_fin"])
    body = [(a, b) for a, b in H.POSE_CONNECTIONS if a <= 24 and b <= 24]
    cap = cv2.VideoCapture(str(d / "interprete.mp4"))
    cap.set(cv2.CAP_PROP_POS_FRAMES, fa)
    hoja = []
    for k in range(fa, fb):
        ok, fr = cap.read()
        if not ok or len(hoja) == 8:
            break
        if (k - fa) % 25:
            continue
        dibujar(fr, z["pose"][k], body, (0, 255, 255))
        dibujar(fr, z["left_hand"][k], H.HAND_CONNECTIONS, (0, 255, 0))
        dibujar(fr, z["right_hand"][k], H.HAND_CONNECTIONS, (255, 0, 255))
        for p in z["face"][k][::6]:
            if not np.isnan(p[0]):
                cv2.circle(fr, (int(p[0] * fr.shape[1]), int(p[1] * fr.shape[0])), 1, (255, 255, 255), -1)
        lienzo = np.zeros((fr.shape[0] + 40, fr.shape[1], 3), np.uint8)
        lienzo[40:] = fr
        cv2.putText(lienzo, f"t={z['t'][k]:.1f}s", (5, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        hoja.append(lienzo)
    hoja += [np.zeros_like(hoja[0])] * (8 - len(hoja))
    cv2.imwrite(str(out / "pose_hoja.jpg"), np.vstack([np.hstack(hoja[:4]), np.hstack(hoja[4:])]))
    print(f"medios -> {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video_id")
    ap.add_argument("--out", default="docs/demo")
    ap.add_argument("--falsos", default="28,96,114", help="segundos con falsos positivos para ilustrar")
    ap.add_argument("--oracion", type=int, default=2, help="oración de la hoja de pose")
    ap.add_argument("--t-region", type=float, default=300, help="segundo del fotograma con la región marcada")
    ap.add_argument("--solo-medios", action="store_true", help="no regenerar datos.json ni pose.txt")
    args = ap.parse_args()
    d, out = carpeta(args.video_id), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if not args.solo_medios:
        datos(d, out, args.video_id)
    medios(d, out, [int(v) for v in args.falsos.split(",")], args.oracion, args.t_region)


if __name__ == "__main__":
    main()
