# LSC-Alocuciones

Dataset de **Lengua de Señas Colombiana (LSC) → texto en español** construido a partir de las alocuciones presidenciales con intérprete, publicadas en el canal de YouTube [@infopresidencia](https://www.youtube.com/@infopresidencia).

## Pipeline

| Paso | Script | Salida |
|---|---|---|
| 1. Inventario del canal (videos + directos) | `scripts/01_list_channel.py` | `data/manifests/channel_{videos,streams}.tsv` |
| 2. Filtrado de candidatos (título, duración) | `scripts/02_filter_candidates.py` | `data/manifests/candidates.tsv` |
| 3. Descarga de subtítulos de YouTube (json3) | `scripts/03_download_subs.py` | `data/subs/*.json3` |
| 3b. Subtítulos → palabras con tiempos | `scripts/parse_json3.py` | `data/words/*.tsv` |
| 4. Verificación de intérprete en pantalla | _pendiente_ | `data/manifests/verified.tsv` |
| 5. Transcripción con Whisper | _pendiente_ | |
| 6. Recorte del intérprete + pose | _pendiente_ | |
| 7. Alineación oración ↔ segmento de señas | _pendiente_ | |

## Uso

```bash
pip install -r requirements.txt
python scripts/01_list_channel.py
python scripts/02_filter_candidates.py            # --min-duration 180 --keywords ...
python scripts/03_download_subs.py                # --cookies-from-browser firefox si YouTube bloquea
python scripts/parse_json3.py
```

## Política de datos

- En git solo se versionan **código y manifiestos** (IDs, títulos, fechas, timestamps).
- Videos, audio, subtítulos y frames quedan en `data/` y **no se suben** (ver `.gitignore`).
- La versión pública del dataset se distribuirá como **pose + transcripción + URL/timestamps**, sin redistribuir video.

## Consideraciones

- Es LSC **interpretada** desde el español, no LSC espontánea: puede haber omisiones y calcos.
- Hay pocos intérpretes. Las particiones train/test se hacen **por intérprete**.
- La validación del conjunto de test se hará con personas competentes en LSC.
