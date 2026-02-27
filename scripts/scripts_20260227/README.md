# Fink/LSST Alert Dataset — Scripts & Notebooks

> **Context**: This directory contains all the tools needed to download, explore, and
> analyze Rubin/LSST transient alerts brokered by [Fink](https://lsst.fink-portal.org).
> The workflow is organized in two independent pipelines: one for building a
> multi-object dataset (catalog + one cutout per object), and one for a deep
> single-object analysis (all cutouts across all epochs and filters).

---

## API reference

| Resource | URL |
|---|---|
| Fink/LSST portal | <https://lsst.fink-portal.org> |
| REST API | <https://api.lsst.fink-portal.org/api/v1> |
| Swagger spec | <https://api.lsst.fink-portal.org/swagger.json> |

**Column naming convention (LSST DPDD schema)**
- Prefix `r:` → `diaSource` table field — **not** the spectral band `r`
- Prefix `f:` → Fink-computed field (classifiers, cross-matches)
- Spectral band → value of column `r:band` ∈ {`u`, `g`, `r`, `i`, `z`, `y`}

---

## Pipeline A — Multi-object dataset

Use this pipeline to build a labeled dataset of alerts selected by **Fink tag**
(e.g. `sn_near_galaxy_candidate`, `extragalactic_new_candidate`, …).
Each object gets one representative cutout (the most recent diaSource).

```
Step A1                       Step A2                    Step A3
─────────────────────         ────────────────────────   ──────────────────────────────
fink_download_alerts          fink_alert_lib.py          fink_alert_browser.ipynb
  _with_cutouts.py        →   (shared library)       →   (interactive exploration)
                              fink_alert_viewer.ipynb
                              (quick single-object view)
```

### Step A1 — `fink_download_alerts_with_cutouts.py`

**Run first.**

Downloads alerts from the Fink/LSST REST API grouped by tag and saves them to
the `fink_dataset/` directory.

For each tag configured in `TAGS_CONFIG`:
- Fetches up to `N_PER_TAG` alerts via `/api/v1/tags`
- Downloads the complete light curve via `/api/v1/sources`
- Downloads one cutout triplet (Science, Template, Difference) for the most
  recent diaSource via `/api/v1/cutouts`
- Saves cutouts as `.npy` arrays of shape `(3, H, W)`

**Output** — `fink_dataset/`
```
fink_dataset/
  alerts_catalog.parquet    # alert metadata + Fink scores for all objects
  alerts_catalog.csv        # same, human-readable
  cutouts/
    {diaObjectId}_label{0|1}.npy   # shape (3, H, W): [Science, Template, Difference]
  lightcurves/
    {diaObjectId}.parquet          # full multi-band light curve per object
  {diaObjectId}_summary.png        # quick-look plot (one per object)
```

**Usage**
```bash
python fink_download_alerts_with_cutouts.py
```

Edit `TAGS_CONFIG` and `N_PER_TAG` at the top of the file to adjust which tags
and how many alerts per tag to download.

---

### Step A2 — `fink_alert_lib.py`

**Shared library — not run directly.**

Provides all plotting functions used by both notebooks in pipeline A.
Import it in any notebook or script:

```python
from fink_alert_lib import FinkDataset, plot_alert_detail, plot_tag_loop, ...
```

Key components:

| Symbol | Description |
|---|---|
| `FinkDataset` | Dataset loader: indexes catalog, cutouts and light curves |
| `plot_lightcurve_flux` | Multi-band light curve in flux (nJy) |
| `plot_lightcurve_mag` | Multi-band light curve in AB magnitude |
| `plot_cutouts` | Science / Template / Difference cutout panels |
| `plot_classifiers` | Fink classifier scores as horizontal bar chart |
| `plot_alert_overview` | Compact 5-panel portal-style view |
| `plot_alert_detail` | Full 2×3 grid (light curves + classifiers + cutouts) |
| `plot_tag_grid` | Overview thumbnail grid for all alerts of a tag |
| `plot_tag_loop` | Iterate over a tag and display a chosen plot type |
| `flux_to_mag` | Convert psfFlux (nJy) → AB magnitude |

---

### Step A2b — `fink_alert_viewer.ipynb`

**Quick single-object viewer** (lightweight alternative to the browser).

A simpler notebook that can be used as a scratchpad to inspect one alert at a
time without loading the full library. Useful for rapid visual checks just after
the download step.

**Requires**: `fink_dataset/` populated by step A1.

---

### Step A3 — `fink_alert_browser.ipynb`

**Main interactive browser for the multi-object dataset.**

Open this notebook to explore the downloaded dataset. Select any alert by
`TAG` + `INDEX`, then display it with different levels of detail.

Sections:
1. Load `FinkDataset` and print summary statistics
2. **Select an alert** — set `TAG` and `INDEX`; lists all objects in that tag
   with SNR, SNN score, TNS name
3. Print full metadata for the selected `diaObjectId`
4. Portal-style overview (5 panels: flux LC, mag LC, Science, Template, Difference)
5. Full detail view (2×3 grid: LCs + classifier bars + cutouts)
6. Individual plots (flux only / mag only / cutouts only / classifiers only)
7. Tag overview grid — all Science thumbnails for a tag, selected object highlighted
8. **Loop over alerts** — `plot_tag_loop` with configurable `plot_type`
   (`'overview'`, `'detail'`, `'lc_flux'`, `'lc_mag'`, `'cutouts'`)
9. Cross-tag comparison — first alert of every tag side by side
10. Custom layout example using low-level library functions

**Requires**: `fink_dataset/` (step A1) and `fink_alert_lib.py` (step A2).

---

## Pipeline B — Single-object deep analysis

Use this pipeline to study **one specific `diaObjectId`** in depth:
download every cutout for every observation (all epochs, all filters),
then visualize the temporal sequence to watch the transient emerge.

```
Step B1                         Step B2
──────────────────────────      ──────────────────────────────────────
fink_download_full_cutouts  →   fink_cutout_timeline.ipynb
  .py                           (temporal viewer + ML dataset builder)
```

> **Tip**: Pick your `diaObjectId` of interest from `fink_alert_browser.ipynb`
> (pipeline A, step A3) before running step B1.

---

### Step B1 — `fink_download_full_cutouts.py`

**Run before** `fink_cutout_timeline.ipynb`.

For a single `diaObjectId`:
1. Fetches the complete list of diaSources via `/api/v1/sources`
2. For **every** diaSource (every epoch × filter):
   downloads the Science, Template and Difference cutouts separately
3. Saves each cutout as an individual `.npy` file (shape `(H, W)`)
4. Writes a manifest file with all diaSource metadata

**Output** — `fullcutouts_{diaObjectId}/`
```
fullcutouts_{diaObjectId}/
  manifest.parquet        # diaSource metadata + file paths, time-sorted
  manifest.csv            # same, human-readable
  cutouts/
    {diaSourceId}_{band}_Science.npy       # shape (H, W), float32
    {diaSourceId}_{band}_Template.npy
    {diaSourceId}_{band}_Difference.npy
```

**Usage**
```bash
# Basic
python fink_download_full_cutouts.py --obj_id 170032915988086813

# Custom output directory
python fink_download_full_cutouts.py --obj_id 170032915988086813 --outdir ./my_dir

# Force re-download even if files already exist
python fink_download_full_cutouts.py --obj_id 170032915988086813 --no_skip
```

The script is **resumable**: if interrupted, re-run with the same arguments and
already-downloaded files will be skipped (unless `--no_skip` is passed).

---

### Step B2 — `fink_cutout_timeline.ipynb`

**Main notebook for single-object temporal analysis.**

Visualizes the complete sequence of cutouts across all epochs and all filters,
with a **shared color scale per filter** so that flux variations are directly
comparable across time.

Sections:
1. Select `OBJ_ID` and optionally trigger the download from within the notebook
2. Load manifest and print per-band statistics
3. Set visualization parameters:
   - `DISPLAY_MODE`: `'triplet'` (Science + Template + Difference) or `'difference'` (Difference only)
   - `COLORSCALE`: `'shared'` (recommended) or `'zscale'` (independent per epoch)
   - `FILTERS`: restrict to specific bands, e.g. `['g', 'r']`
4. Multi-band light curve (flux and magnitude)
5. **Cutout timeline per filter** — rows = epochs, columns = cutout kinds,
   light curve strip on the left with a marker at the current epoch
6. **Compact difference grid** — rows = filters, columns = epochs; quick overview
7. **Birth sequence mosaic** for one chosen filter — Difference thumbnails in
   temporal order with the band light curve underneath
8. **ML dataset builder** — assembles `X` of shape `(N, 3, H, W)` (center-crop
   or zero-pad to 30×30), saves `X_cutouts.npy` and `y_meta.parquet`
9. Sanity check: mean image per channel and pixel statistics

**Requires**: `fink_download_full_cutouts.py` output (step B1) and `fink_alert_lib.py`.

---

## Pipeline C — Sky map

Visualize the spatial distribution of all downloaded alerts on a sky map.

```
C1: fink_skymap_lib.py  +  fink_dataset/  →  C2: fink_skymap.ipynb
```

> **Requires**: `fink_dataset/` populated by pipeline A (step A1).

### Step C1 — `fink_skymap_lib.py`

**Shared library — not run directly.**

Provides all sky map plotting functions:

| Symbol | Description |
|---|---|
| `load_catalog` | Load and deduplicate the alert catalog |
| `catalog_summary` | Per-tag statistics (counts, RA/Dec range, SNN mean) |
| `plot_skymap_rect` | Rectangular (RA, Dec) projection, zoomable |
| `plot_skymap_mollweide` | Full-sky Mollweide projection |
| `plot_skymap_combined` | Two-panel: Mollweide + rectangular zoom |
| `galactic_plane_radec` | Galactic plane curve in ICRS coordinates |
| `ra_deg_to_hms` | Convert RA degrees → HH:MM string |
| `RUBIN_DDF` | List of Rubin LSST Deep Drilling Fields |
| `TAG_STYLES` | Color/marker scheme per Fink tag |

The library supports:
- Per-tag color coding (blue / green / yellow / red / purple)
- RA axis labels in **HMS** (HH:MM) or **degrees** — user-selectable
- Dec axis in degrees
- Galactic plane (b=0) and optional galactic band (±b°)
- Rubin LSST DDF positions with labels
- RA/Dec grid with configurable step
- Optional real sky background via CDS HiPS tiles (`astroquery` required)

### Step C2 — `fink_skymap.ipynb`

**Sky map notebook.**

Sections:
1. Load catalog and print per-tag statistics
2. Set global parameters (RA unit, grid step, overlays, sky background)
3. Combined view: Mollweide (full sky) + rectangular zoom
4. Mollweide projection only
5. Rectangular zoom on data region
6. Rectangular map with RA in degrees (alternative to HMS)
7. Per-tag individual maps
8. SNR-weighted scatter (marker size ∝ SNR)
9. SNN score color map (continuous colormap)
10. CDS HiPS sky background (DSS2, 2MASS, PanSTARRS…) — requires `astroquery`
11. DDF cross-match and zoom on individual DDFs
12. 2D alert density histogram

**Requires**: `fink_skymap_lib.py` and `fink_dataset/` (pipeline A).

---

## File summary

| File | Type | Purpose | Run order |
|---|---|---|---|
| `fink_download_alerts_with_cutouts.py` | Script | Download multi-object dataset by tag | **A1 — first** |
| `fink_alert_lib.py` | Library | Shared plotting functions for pipeline A | A2 — imported |
| `fink_alert_viewer.ipynb` | Notebook | Quick single-object viewer | A2b — optional |
| `fink_alert_browser.ipynb` | Notebook | Interactive multi-object browser | **A3 — after A1** |
| `fink_download_full_cutouts.py` | Script | Download all cutouts for one object | **B1 — first** |
| `fink_cutout_timeline.ipynb` | Notebook | Temporal viewer + ML dataset builder | **B2 — after B1** |
| `fink_skymap_lib.py` | Library | Sky map plotting functions | C1 — imported |
| `fink_skymap.ipynb` | Notebook | Interactive sky map | **C2 — after A1** |
| `fink_dataset/` | Directory | Output of pipeline A | — |
| `fullcutouts_{id}/` | Directory | Output of pipeline B | — |

---

## Environment

```bash
conda activate conda_py3120_fink   # or your equivalent environment

# Required packages
pip install requests numpy pandas matplotlib astropy pyarrow
```

Python ≥ 3.10 required (uses `X | Y` union types and `match` syntax).

---

## Authors

- dagoret — 2026-02
