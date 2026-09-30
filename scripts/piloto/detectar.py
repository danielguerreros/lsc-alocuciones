"""Paso 4a: un fotograma cada --paso s, recortado a la región del intérprete, pasado por MediaPipe Holistic.

Salida: deteccion.csv (persona, manos, cara, posición de la nariz y ancho de hombros por fotograma)
y crops/ (un recorte cada 20 s, para revisar a ojo).
"""
import argparse
import csv
import time

import cv2
import mediapipe as mp

from comun import carpeta, config


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video_id")
    ap.add_argument("--paso", type=float, default=2.0, help="segundos entre fotogramas")
    args = ap.parse_args()
    d = carpeta(args.video_id)
    x, y, w, h = config(d)["region"]
    (d / "crops").mkdir(exist_ok=True)

    holistic = mp.solutions.holistic.Holistic(static_image_mode=True, model_complexity=1)
    cap = cv2.VideoCapture(str(d / "video_720p.mp4"))
    dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
    rows, t, t0 = [], 0.0, time.time()
    while t < dur:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            break
        crop = frame[y:y + h, x:x + w]
        r = holistic.process(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
        row = {"t": t, "pose": int(r.pose_landmarks is not None),
               "lhand": int(r.left_hand_landmarks is not None),
               "rhand": int(r.right_hand_landmarks is not None), "face": int(r.face_landmarks is not None)}
        if r.pose_landmarks:
            p = r.pose_landmarks.landmark
            row["nose_x"], row["nose_y"] = round(p[0].x, 3), round(p[0].y, 3)
            row["shoulder_w"] = round(abs(p[11].x - p[12].x), 3)  # fracción del ancho de la región
        rows.append(row)
        if int(t) % 20 == 0:
            cv2.imwrite(str(d / "crops" / f"{int(t):04d}.jpg"), crop)
        t += args.paso

    fields = ["t", "pose", "lhand", "rhand", "face", "nose_x", "nose_y", "shoulder_w"]
    with (d / "deteccion.csv").open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=fields)
        wr.writeheader()
        wr.writerows(rows)
    print(f"{len(rows)} fotogramas en {time.time() - t0:.0f}s -> {d / 'deteccion.csv'}")


if __name__ == "__main__":
    main()
