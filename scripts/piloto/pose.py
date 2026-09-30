"""Paso 6: recorta la región del intérprete entre el primer y el último tramo, y extrae la pose de cada fotograma.

Salida: interprete.mp4 (recorte sin audio) y pose.npz con, por fotograma, 33 puntos del cuerpo
(x, y, z, visibilidad), 21 de cada mano y 468 de la cara, en coordenadas normalizadas al recorte (NaN si falta).
"""
import argparse
import json
import subprocess
import time

import cv2
import mediapipe as mp
import numpy as np

from comun import carpeta, config


def arr(lms, n, vis=False):
    if lms is None:
        return np.full((n, 4 if vis else 3), np.nan, np.float32)
    return np.array([[l.x, l.y, l.z] + ([l.visibility] if vis else []) for l in lms.landmark], np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video_id")
    args = ap.parse_args()
    d = carpeta(args.video_id)
    x, y, w, h = config(d)["region"]
    tramos = json.loads((d / "tramos.json").read_text())
    if not tramos:
        raise SystemExit("Sin tramos con intérprete: nada que procesar")
    a, b = tramos[0][0], tramos[-1][1]

    t0 = time.time()
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(a), "-to", str(b), "-i", str(d / "video_720p.mp4"),
                    "-vf", f"crop={w}:{h}:{x}:{y}", "-an", "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
                    str(d / "interprete.mp4")], check=True)
    print(f"recorte {a}-{b}s en {time.time() - t0:.0f}s")

    holistic = mp.solutions.holistic.Holistic(static_image_mode=False, model_complexity=1, refine_face_landmarks=False)
    cap = cv2.VideoCapture(str(d / "interprete.mp4"))
    fps = cap.get(cv2.CAP_PROP_FPS)
    size = np.array([cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)])
    P, L, R, F, T = [], [], [], [], []
    t1 = time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        r = holistic.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        P.append(arr(r.pose_landmarks, 33, True))
        L.append(arr(r.left_hand_landmarks, 21))
        R.append(arr(r.right_hand_landmarks, 21))
        F.append(arr(r.face_landmarks, 468))
        T.append(a + len(T) / fps)
    el = time.time() - t1
    P, L, R = np.stack(P), np.stack(L), np.stack(R)
    np.savez_compressed(d / "pose.npz", t=np.array(T), pose=P, left_hand=L, right_hand=R, face=np.stack(F),
                        fps=fps, frame_size=size)
    print(f"{len(T)} fotogramas a {fps:.2f} fps en {el:.0f}s ({len(T) / el:.1f} fps de proceso) | "
          f"cuerpo {np.mean(~np.isnan(P[:, 0, 0])):.1%} | mano izq {np.mean(~np.isnan(L[:, 0, 0])):.1%} | "
          f"mano der {np.mean(~np.isnan(R[:, 0, 0])):.1%}")


if __name__ == "__main__":
    main()
