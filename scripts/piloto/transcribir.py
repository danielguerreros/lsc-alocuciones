"""Paso 5: transcripción del audio completo con Whisper, con marca de tiempo por palabra.

Corre en un proceso aparte de OpenCV: ambos traen su propia copia de libav y en macOS chocan.
"""
import argparse
import json
import subprocess
import time

import numpy as np
from faster_whisper import WhisperModel

from comun import carpeta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video_id")
    ap.add_argument("--modelo", default="large-v3-turbo")
    args = ap.parse_args()
    d = carpeta(args.video_id)
    audio = next(d.glob("audio.*"))

    t0 = time.time()
    model = WhisperModel(args.modelo, device="cpu", compute_type="int8")
    t1 = time.time()
    # Decodificar con ffmpeg a 16 kHz mono: el lector de PyAV es incompatible con esta versión de faster-whisper.
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(audio), "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    samples = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
    segments, info = model.transcribe(samples, language="es", word_timestamps=True, vad_filter=True)
    segs = [{"start": s.start, "end": s.end, "text": s.text.strip(),
             "words": [{"start": w.start, "end": w.end, "word": w.word.strip(), "p": round(w.probability, 3)}
                       for w in s.words]}
            for s in segments]
    t2 = time.time()
    (d / "whisper.json").write_text(json.dumps(
        {"duration": info.duration, "load_s": t1 - t0, "transcribe_s": t2 - t1, "segments": segs},
        ensure_ascii=False, indent=1))
    print(f"audio {info.duration:.0f}s | carga {t1 - t0:.0f}s | transcripción {t2 - t1:.0f}s | {len(segs)} segmentos")


if __name__ == "__main__":
    main()
