# LSC-Alocuciones

Dataset de **Lengua de Señas Colombiana (LSC) → texto en español** construido a partir de videos de YouTube con intérprete de LSC en pantalla. Cada fuente tiene su propia carpeta (`data/manifests/<fuente>/`, `data/subs/<fuente>/`, `data/words/<fuente>/`):

| Fuente | Canal | Qué se toma | Desde |
|---|---|---|---|
| `presidencia` | [@infopresidencia](https://www.youtube.com/@infopresidencia) | Alocuciones presidenciales y el especial ‘Prevención y Acción’ (COVID-19) | oct. 2016, cuando el intérprete empieza a aparecer en los videos |
| `caracol` | [@NoticiasCaracol](https://www.youtube.com/@NoticiasCaracol) | Emisión del mediodía, entre semana y fin de semana (las emisiones de la mañana y la central no tienen intérprete) | sep. 2025, inicio de las listas "Emisiones Noticias Caracol" |

## Pipeline

| Paso | Script | Salida |
|---|---|---|
| 1. Inventario del canal (videos + directos) — Presidencia | `scripts/01_list_channel.py` | `data/manifests/presidencia/channel_{videos,streams}.tsv` |
| 2. Filtrado de candidatos por título y fecha de corte — Presidencia | `scripts/02_filter_candidates.py` | `data/manifests/presidencia/candidates.tsv` |
| 1+2. Emisiones del mediodía desde las listas anuales — Caracol | `scripts/01_list_caracol.py` | `data/manifests/caracol/candidates.tsv` |
| 2b. Fecha y duración de cada candidato (solo Presidencia: Caracol ya las trae) | `scripts/02b_fetch_metadata.py` | `data/manifests/<fuente>/metadata.tsv` |
| 3. Descarga de subtítulos de YouTube (json3) | `scripts/03_download_subs.py` | `data/subs/<fuente>/*.json3` |
| 3b. Subtítulos → palabras con tiempos | `scripts/parse_json3.py` | `data/words/<fuente>/*.tsv` |
| 4. Verificación de intérprete en pantalla | _pendiente_ | `data/manifests/<fuente>/verified.tsv` |
| 5. Transcripción con Whisper | _pendiente_ | |
| 6. Recorte del intérprete + pose | _pendiente_ | |
| 7. Alineación oración ↔ segmento de señas | _pendiente_ | |

## Uso

```bash
conda env create -f environment.yml               # una vez; actualizar: conda env update -f environment.yml
conda activate lsc-alocuciones

# Presidencia
python scripts/01_list_channel.py
python scripts/02_filter_candidates.py            # --min-duration 180 --keywords ... --since-id ''
python scripts/02b_fetch_metadata.py              # en serie; luego re-correr el paso 2 para filtrar por duración

# Caracol
python scripts/01_list_caracol.py

# Comunes: --source presidencia|caracol
python scripts/03_download_subs.py --source caracol   # --cookies-from-browser chrome si YouTube bloquea
python scripts/parse_json3.py --source caracol
```

## Política de datos

- En git solo se versionan **código y manifiestos** (IDs, títulos, fechas, timestamps).
- Videos, audio, subtítulos y frames quedan en `data/` y **no se suben** (ver `.gitignore`).
- La versión pública del dataset se distribuirá como **pose + transcripción + URL/timestamps**, sin redistribuir video.

## Consideraciones

- Es LSC **interpretada** desde el español, no LSC espontánea: puede haber omisiones y calcos.
- Hay pocos intérpretes. Las particiones train/test se hacen **por intérprete**.
- En Caracol el intérprete está integrado en el set, junto al logo, y ocupa poca pantalla: conviene descargar en la mayor resolución disponible.
- En ‘Prevención y Acción’ y en los noticieros hablan varias personas (presentadores, ministros, invitados, clips), no solo una.
- La validación del conjunto de test se hará con personas competentes en LSC.
