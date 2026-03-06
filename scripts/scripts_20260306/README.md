# scripts_20260228 — Fink LSST Alert Analysis Toolkit

Rubin/LSST alert download and visualisation scripts using the
[Fink broker](https://lsst.fink-portal.org) REST API.

---

## Critical API facts (LSST vs ZTF)

| | ZTF portal (`fink-portal.org`) | LSST portal (`api.lsst.fink-portal.org`) |
|---|---|---|
| Base URL | `https://fink-portal.org/api/v1` | `https://api.lsst.fink-portal.org/api/v1` |
| HTTP method | `POST` with JSON body | **`GET` with query-string params** |
| Tag endpoint | `/latests?class=` | **`/tags?tag=`** |
| Light curve endpoint | `/objects?objectId=` | **`/sources?diaObjectId=`** |
| Cutout key | `objectId=` | **`diaSourceId=`** |
| Cutout return format | raw numpy bytes | **JSON array** |
| Bands | `g`, `r` | `u`, `g`, `r`, `i`, `z`, `y` |
| Flux column | `i:magpsf` (mag) | `r:psfFlux` (nJy, not a magnitude) |
| Column prefix `r:` | spectral band r | **diaSource table name** (NOT the band!) |
| Spectral band | `i:fid` = 1 or 2 | **value of `r:band`** ∈ {u,g,r,i,z,y} |

> **Column naming warning:** In the LSST schema, the prefix `r:` means
> "field from the diaSource table (table name = r in the LSST DPDD)".
> It has **nothing to do** with the spectral band `r` of Rubin/LSST.
> The spectral band is always the *value* of the column `r:band`.

---

## Pipelines

```
Pipeline A — Multi-object tagged dataset (original script, hard-coded config)
──────────────────────────────────────────────────────────────────────────────
A1: fink_download_alerts_with_cutouts.py
    ↓  writes to fink_dataset/{cutouts/, lightcurves/}
A2: fink_alert_lib.py                      (FinkDataset class + plot functions)
    ↓
A3: fink_alert_browser.ipynb               (interactive exploration)


Pipeline B — Configurable tagged dataset  [NEW in scripts_20260228]
──────────────────────────────────────────────────────────────────────────────
B1: fink_download_tag_dataset.py           (CLI: --tag + --n of your choice)
    ↓  writes to fink_dataset/<tag>/
B2: fink_alert_lib.py                      (same library, re-used)
    ↓
B3: fink_tag_dataset_browser.ipynb         (browser adapted to tag sub-dirs)


Pipeline C — Single-object full cutout timeline
──────────────────────────────────────────────────────────────────────────────
C1: fink_download_full_cutouts.py          (--obj_id, all bands × epochs)
    ↓  writes to fullcutouts_<obj_id>/
C2: fink_cutout_timeline.ipynb             (timeline + ML dataset builder)
```

---

## File inventory

| File | Role | Pipeline |
|------|------|----------|
| `fink_download_alerts_with_cutouts.py` | Download alerts for a fixed tag set | A1 |
| `fink_download_tag_dataset.py` | **CLI download**: `--tag` + `--n` of your choice | B1 |
| `fink_download_full_cutouts.py` | Download all cutouts for one diaObject | C1 |
| `fink_alert_lib.py` | `FinkDataset` class + all plot functions | A2 / B2 |
| `fink_skymap_lib.py` | Skymap plots (Mollweide, rectangular, HiPS) | — |
| `fink_alert_browser.ipynb` | Interactive browser for Pipeline A datasets | A3 |
| `fink_tag_dataset_browser.ipynb` | Interactive browser for Pipeline B datasets | B3 |
| `fink_cutout_timeline.ipynb` | Timeline visualisation + ML prep | C2 |
| `fink_skymap.ipynb` | Sky distribution maps of alerts | — |

---

## Pipeline B — Quick start

### 1. List available tags

```bash
python fink_download_tag_dataset.py --list-tags
```

| Tag (short name) | Description |
|------------------|-------------|
| `extragalactic_lt20mag_candidate` | Rising, bright (mag < 20), extragalactic |
| `extragalactic_new_candidate` | New (< 48 h) and potentially extragalactic |
| `hostless_candidate` | Hostless according to ELEPHANT |
| `in_tns` | Known TNS counterpart (AT or confirmed) |
| `sn_near_galaxy_candidate` | Consistent with SNe near a galaxy |

### 2. Download a dataset

```bash
# 50 extragalactic new-candidate alerts (output: ./fink_dataset/)
python fink_download_tag_dataset.py \
    --tag extragalactic_new_candidate \
    --n 50

# 200 SN-near-galaxy alerts into a custom directory
python fink_download_tag_dataset.py \
    --tag sn_near_galaxy_candidate \
    --n 200 \
    --outdir /data/fink_dataset

# Dry-run: show what would be done without writing files
python fink_download_tag_dataset.py \
    --tag in_tns --n 20 --dry-run

# Full help
python fink_download_tag_dataset.py --help
```

### 3. Output layout

```
fink_dataset/
└── extragalactic_new_candidate/
    ├── catalog.parquet               # one row per diaObject
    ├── light_curves/
    │   ├── lc_170032915988086813.parquet
    │   └── ...
    └── cutouts/
        ├── cutout_170032915988086813.npy   # dict: Science/Template/Difference
        └── ...
```

### 4. Browse the dataset

Open `fink_tag_dataset_browser.ipynb` and set:

```python
TAG_CONFIG = "extragalactic_new_candidate"
BASE_DIR   = Path("fink_dataset")
```

---

## Pipeline C — Single-object cutout timeline

```bash
# Pick obj_id from the browser notebook, then:
python fink_download_full_cutouts.py --obj_id 170032915988086813
```

Then open `fink_cutout_timeline.ipynb`.

---

## Dependencies

```
numpy pandas matplotlib astropy requests
pyarrow          # for parquet I/O
astroquery       # optional, for HiPS sky background in fink_skymap.ipynb
```

Install:
```bash
pip install numpy pandas matplotlib astropy requests pyarrow astroquery
```
