# notebooks/01_download_view_alerts — Fink LSST Alert Analysis Toolkit

Rubin/LSST alert download and visualisation using the
[Fink broker](https://lsst.fink-portal.org) REST API.

All library code has been **packaged** into `rubinlsstskyalerts.fink_tools`
(see `src/rubinlsstskyalerts/fink_tools/`).  The standalone `.py` copies kept
here are legacy references — **import from the package**, not from the local
directory.

---

## Project layout (relative to repo root)

```
RubinLSSTSkyAlerts/
├── src/rubinlsstskyalerts/
│   ├── __init__.py
│   └── fink_tools/                        ← installable library
│       ├── __init__.py                    ← exposes all public symbols
│       ├── fink_alert_lib.py              ← FinkDataset class + plot functions
│       ├── fink_skymap_lib.py             ← sky map plots (Mollweide, rect, HiPS)
│       ├── fink_download_tag_dataset.py   ← CLI download by tag
│       ├── fink_download_alerts_with_cutouts.py
│       └── fink_download_full_cutouts.py
│
├── notebooks/
│   └── 01_download_view_alerts/           ← YOU ARE HERE
│       ├── README.md
│       ├── 01_fink_alert_browser.ipynb
│       ├── 02_fink_skymap.ipynb
│       ├── 03_fink_tag_dataset_browser.ipynb
│       ├── 04_fink_cutout_timeline.ipynb
│       ├── fink_dataset/                  ← downloaded data (git-ignored)
│       └── fullcutouts_<diaObjectId>/     ← single-object cutout timelines
│
└── scripts/
    └── scripts_20260306/                  ← legacy standalone scripts (origin)
        ├── fink_alert_lib.py
        ├── fink_skymap_lib.py
        ├── fink_download_*.py
        └── *.ipynb
```

---

## Installation

The package must be installed in editable mode so that any notebook can
import it regardless of its working directory:

```bash
cd ~/Desktop/RubinLSSTSkyAlerts
pip install -e ".[dev]"
```

After that, from **any notebook or script**:

```python
from rubinlsstskyalerts.fink_tools import (
    FinkDataset,
    plot_alert_detail,
    plot_skymap_combined,
    download_dataset,
    ...
)
```

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
| Spectral band | `i:fid` = 1 or 2 | **value of `r:band`** ∈ {u, g, r, i, z, y} |

> **Column naming warning:** In the LSST schema, the prefix `r:` means
> "field from the diaSource table (table name = r in the LSST DPDD)".
> It has **nothing to do** with the spectral band `r` of Rubin/LSST.
> The spectral band is always the *value* of the column `r:band`.

---

## Pipelines

```
Pipeline A — Multi-object tagged dataset (fixed tag set, hard-coded config)
──────────────────────────────────────────────────────────────────────────────
A1: rubinlsstskyalerts.fink_tools.fink_download_alerts_with_cutouts
    (or legacy: scripts/scripts_20260306/fink_download_alerts_with_cutouts.py)
    ↓  writes to fink_dataset/{cutouts/, lightcurves/, alerts_catalog.parquet}
A2: rubinlsstskyalerts.fink_tools.FinkDataset  (class + all plot functions)
    ↓
A3: 01_fink_alert_browser.ipynb


Pipeline B — Configurable tagged dataset
──────────────────────────────────────────────────────────────────────────────
B1: rubinlsstskyalerts.fink_tools.download_dataset()
    (or CLI: python fink_download_tag_dataset.py --tag <tag> --n <n>)
    ↓  writes to fink_dataset/<tag>/
B2: rubinlsstskyalerts.fink_tools.FinkDataset
    ↓
B3: 03_fink_tag_dataset_browser.ipynb


Pipeline C — Single-object full cutout timeline
──────────────────────────────────────────────────────────────────────────────
C1: rubinlsstskyalerts.fink_tools.download_full_cutouts()
    (or CLI: python fink_download_full_cutouts.py --obj_id <id>)
    ↓  writes to fullcutouts_<diaObjectId>/
C2: 04_fink_cutout_timeline.ipynb


Pipeline D — Sky maps
──────────────────────────────────────────────────────────────────────────────
D1: rubinlsstskyalerts.fink_tools.load_catalog()
    ↓  reads fink_dataset/alerts_catalog.parquet
D2: rubinlsstskyalerts.fink_tools.{plot_skymap_rect,
                                    plot_skymap_mollweide,
                                    plot_skymap_combined}
    ↓
D3: 02_fink_skymap.ipynb
```

---

## Notebook inventory

| Notebook | Pipeline | Description |
|----------|----------|-------------|
| `01_fink_alert_browser.ipynb` | A | Interactive per-object browser: light curves + cutouts + classifiers |
| `02_fink_skymap.ipynb` | D | Sky distribution maps (rectangular + Mollweide, optional HiPS background) |
| `03_fink_tag_dataset_browser.ipynb` | B | Browse datasets downloaded by tag with `download_dataset()` |
| `04_fink_cutout_timeline.ipynb` | C | Full cutout timeline for one diaObject across all bands × epochs |

---

## Library inventory (`rubinlsstskyalerts.fink_tools`)

| Module | Key symbols |
|--------|-------------|
| `fink_alert_lib` | `FinkDataset`, `flux_to_mag`, `plot_lightcurve_flux`, `plot_lightcurve_mag`, `plot_cutouts`, `plot_classifiers`, `plot_alert_overview`, `plot_alert_detail`, `plot_tag_grid`, `plot_tag_loop` |
| `fink_skymap_lib` | `load_catalog`, `catalog_summary`, `plot_skymap_rect`, `plot_skymap_mollweide`, `plot_skymap_combined`, `fetch_hips_image`, `overlay_hips_background`, `draw_radec_grid`, `galactic_plane_radec` |
| `fink_download_tag_dataset` | `download_dataset`, `fetch_latest_alerts`, `fetch_light_curve`, `fetch_cutouts`, `list_tags`, `FINK_TAGS` |
| `fink_download_alerts_with_cutouts` | `fetch_by_tag`, `fetch_lightcurve`, `save_cutouts_npy`, `plot_alert_summary`, `TAGS_CONFIG` |
| `fink_download_full_cutouts` | `download_full_cutouts`, `fetch_sources`, `fetch_single_cutout`, `fetch_all_cutouts` |

All symbols are re-exported directly from `rubinlsstskyalerts.fink_tools`:

```python
# Fine-grained import
from rubinlsstskyalerts.fink_tools import FinkDataset, plot_alert_detail

# Short-cut from package root (most common symbols)
from rubinlsstskyalerts import FinkDataset, plot_skymap_combined
```

---

## Pipeline B — Quick start

### 1. List available tags

```bash
python fink_download_tag_dataset.py --list-tags
```

| Tag | Description |
|-----|-------------|
| `extragalactic_lt20mag_candidate` | Rising, bright (mag < 20), extragalactic |
| `extragalactic_new_candidate` | New (< 48 h first detection), extragalactic |
| `hostless_candidate` | Hostless (ELEPHANT algorithm) |
| `in_tns` | Known counterpart in TNS (AT or confirmed) |
| `sn_near_galaxy_candidate` | SNe-like alert near a galaxy |

### 2. Download

```bash
# 50 extragalactic new-candidate alerts
python fink_download_tag_dataset.py \
    --tag extragalactic_new_candidate --n 50

# 200 SN-near-galaxy alerts into a custom directory
python fink_download_tag_dataset.py \
    --tag sn_near_galaxy_candidate --n 200 \
    --outdir /data/fink_dataset

# Dry-run (no files written)
python fink_download_tag_dataset.py --tag in_tns --n 20 --dry-run
```

Or from Python / a notebook:

```python
from rubinlsstskyalerts.fink_tools import download_dataset
from pathlib import Path

download_dataset(
    tag="extragalactic_new_candidate",
    n=50,
    outdir=Path("fink_dataset"),
)
```

### 3. Output layout (Pipeline B)

```
fink_dataset/
└── extragalactic_new_candidate/
    ├── catalog.parquet
    ├── light_curves/
    │   └── lc_<diaObjectId>.parquet
    └── cutouts/
        └── cutout_<diaObjectId>.npy    # np.load() → dict {Science, Template, Difference}
```

### 4. Output layout (Pipeline A)

```
fink_dataset/
├── alerts_catalog.parquet
├── alerts_catalog.csv
├── lightcurves/
│   └── <diaObjectId>.parquet
└── cutouts/
    └── <diaObjectId>_label<0|1>.npy   # shape (3, H, W)
```

---

## Pipeline C — Single-object cutout timeline

```bash
# Pick a diaObjectId from the browser notebook, then:
python fink_download_full_cutouts.py --obj_id 170032915988086813

# Re-download even if files exist:
python fink_download_full_cutouts.py --obj_id 170032915988086813 --no_skip
```

Output:

```
fullcutouts_170032915988086813/
├── manifest.parquet
├── manifest.csv
└── cutouts/
    └── <diaSourceId>_<band>_{Science,Template,Difference}.npy
```

Then open `04_fink_cutout_timeline.ipynb`.

---

## Dependencies

Declared in `pyproject.toml` and installed automatically with the package:

```
numpy  pandas  matplotlib  astropy  requests
pyarrow      # parquet I/O
astroquery   # HiPS sky background (optional)
Pillow       # fallback JPG decode for HiPS
```

Manual install (if not using the package):

```bash
pip install numpy pandas matplotlib astropy requests pyarrow astroquery Pillow
```

---

## History

| Date | Directory | Notes |
|------|-----------|-------|
| 2026-02-26 | `scripts/scripts_20260226` | First LSST API exploration |
| 2026-02-27 | `scripts/scripts_20260227` | `fink_alert_lib.py` v1 |
| 2026-02-28 | `scripts/scripts_20260228` | Pipeline B (configurable tags) |
| 2026-03-03 | `scripts/scripts_20260303` | Pipeline C (full cutout timeline) |
| 2026-03-06 | `scripts/scripts_20260306` | `fink_skymap_lib.py`, HiPS background |
| 2026-03-07 | `src/rubinlsstskyalerts/fink_tools/` | **Packaged** — all `.py` moved to installable library |
