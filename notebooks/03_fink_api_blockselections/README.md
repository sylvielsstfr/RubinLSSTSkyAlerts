# Fink/LSST — Light Curve Analysis for Atmospheric Transparency Calibration

This directory contains two Jupyter notebooks that retrieve, classify, and visualise
photometric light curves from the [Fink](https://fink-portal.org) alert broker for
LSST/Rubin commissioning data, with the goal of identifying stable stellar and
galactic sources suitable for **atmospheric transparency calibration**.

---

## Context

During the Rubin Observatory Science Verification (SV) phase, alert packets are
distributed through the Fink broker, which enriches them with crossmatch metadata
from external catalogues (Gaia DR3, SIMBAD, Legacy Survey DR8, Mangrove).  
The notebooks query the [Fink LSST API](https://api.lsst.fink-portal.org) to
download light curves in the six LSST bands (*u g r i z y*) and measure their
photometric stability (normalised RMS variability σ/⟨f⟩) per source class.

---

## Notebooks

### `01_fink_block_lightcurves.ipynb` — Data retrieval & analysis

**What it does:**

1. **Cone search** each LSST Deep Drilling Field (COSMOS, ELAIS-S1, XMM-LSS,
   ECDFS, EDFS, M49 …) via `POST /api/v1/conesearch` using the `r:` column
   prefix required by the Fink LSST API.
2. **Deduplication** — keeps one entry per `diaObjectId`, retaining only objects
   with at least `NP_MIN = 50` detections.
3. **Classification** — assigns each object to a calibration group based on Fink
   crossmatch columns (`f:xm_gaiadr3_*`, `f:xm_simbad_otype`,
   `f:xm_legacydr8_pstar`, `f:xm_mangrove_*`, `f:is_sso`).  
   Groups include: `gaia_star_stable`, `gaia_star_variable`, `simbad_star`,
   `simbad_galaxy`, `legacy_star`, `legacy_galaxy`, `mangrove_galaxy`,
   `solar_system`, `fink_cataloged`, `unclassified`.
4. **Light curve download** — fetches full diaSources (`/api/v1/sources`) and
   forced photometry (`/api/v1/fp`) for up to 100 objects.
5. **NaN cleaning** — removes rows with missing flux, flux error, or MJD at
   every stage (after SNR filtering, after flux-to-magnitude conversion, and
   before plotting).
6. **Flatness metrics** — computes σ/⟨f⟩ per object per band and stores the
   results in `data_FINK_BLOCK_LC_01/flatness_metrics.csv`.
7. **Visualisations** — boxplot of variability by group and band; light curve
   grids in flux (nJy) and AB magnitude for the top-20 objects per group;
   calibration scatter plot (mean flux vs. median RMS).
8. **Persistence** — saves all filtered light curves to Parquet files
   (`{group}_fp.parquet`, `{group}_src.parquet`) under `data_FINK_BLOCK_LC_01/`.

**Outputs written to disk:**

| Path | Content |
|------|---------|
| `data_FINK_BLOCK_LC_01/{group}_fp.parquet` | Forced-photometry light curves |
| `data_FINK_BLOCK_LC_01/{group}_src.parquet` | Detection-based light curves |
| `data_FINK_BLOCK_LC_01/flatness_metrics.csv` | Per-object, per-band RMS metrics |
| `figs_FINK_BLOCK_LC_01/01_flatness_boxplot_by_group.{pdf,png}` | Variability boxplot |
| `figs_FINK_BLOCK_LC_01/02_lc_{group}_{mode}.{pdf,png}` | Light curve grids |
| `figs_FINK_BLOCK_LC_01/03_calibration_summary.{pdf,png}` | Calibration scatter plot |

---

### `02_fink_block_lightcurves_replot.ipynb` — Offline visualisation

**What it does:**

Reads all Parquet files and the CSV produced by notebook 01 — **no API call is
made** — and reproduces or extends the same set of plots.

1. **Auto-discovery** — scans `data_FINK_BLOCK_LC_01/` with `glob` to find all
   available groups without hard-coding their names.
2. **Cache reconstruction** — loads each `_fp` and `_src` Parquet file and
   rebuilds the `lc_cache[group][oid]` dictionary used by the plotting functions.
   Magnitude columns (`mag`, `mag_err`) are recomputed on-the-fly if absent.
3. **Defensive NaN removal** — applies `dropna` on core columns at load time and
   a finite-value mask just before each `errorbar` call.
4. **Group-level plots** — flux and magnitude grids for all groups (sections 7–8),
   identical layout to notebook 01.
5. **Single-object inspector** (section 9) — detailed flux + magnitude side-by-side
   plot per band for any chosen `TARGET_GROUP` / `TARGET_OID`.
6. **Calibration summary** (section 10) — scatter plot and ranking table read from
   `flatness_metrics.csv`.

**Figures are saved to** `figs_FINK_BLOCK_LC_01_02/`.

---

## Directory layout

```
03_fink_api_blockselections/
├── 01_fink_block_lightcurves.ipynb        # data retrieval & analysis
├── 02_fink_block_lightcurves_replot.ipynb # offline re-visualisation
├── README.md                              # this file
├── data_FINK_BLOCK_LC_01/
│   ├── flatness_metrics.csv
│   ├── gaia_star_stable_fp.parquet
│   ├── gaia_star_stable_src.parquet
│   ├── gaia_star_variable_fp.parquet
│   ├── gaia_star_variable_src.parquet
│   ├── legacy_galaxy_fp.parquet
│   ├── legacy_galaxy_src.parquet
│   ├── legacy_star_fp.parquet
│   ├── legacy_star_src.parquet
│   ├── simbad_galaxy_fp.parquet
│   ├── simbad_galaxy_src.parquet
│   ├── unclassified_fp.parquet
│   └── unclassified_src.parquet
├── figs_FINK_BLOCK_LC_01/                 # figures from notebook 01
└── figs_FINK_BLOCK_LC_01_02/             # figures from notebook 02
```

---

## Requirements

| Package | Purpose |
|---------|---------|
| `requests` | Fink API HTTP calls (notebook 01 only) |
| `pandas ≥ 2.0` | DataFrames, Parquet I/O |
| `numpy` | Numerical computations |
| `matplotlib` | Plotting |
| `pyarrow` or `fastparquet` | Parquet backend for pandas |

Install with:
```bash
pip install requests pandas numpy matplotlib pyarrow
```
or activate the `conda_py3120_fink` environment already configured for this project.

---

## Key API notes (notebook 01)

- The Fink LSST API requires the **`r:` column prefix** in cone-search requests
  (using `i:` causes HTTP 500 errors).
- Block flags (`b_*`) cannot be used as API filters; classification is done
  client-side via `f:xm_*` crossmatch columns returned by the cone search.
- Endpoints used:
  - `POST /api/v1/conesearch` — sky-cone alert search
  - `POST /api/v1/sources`   — full diaSource light curve for one object
  - `POST /api/v1/fp`        — forced-photometry light curve for one object

---

## Authors

Notebook series developed for the Rubin/LSST SV atmospheric transparency
calibration study using the Fink alert broker.
