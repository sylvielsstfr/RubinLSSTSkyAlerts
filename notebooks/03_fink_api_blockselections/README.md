# Fink/LSST — Light Curve Analysis for Atmospheric Transparency Calibration

This directory contains a series of Jupyter notebooks that retrieve, classify,
and visualise photometric light curves from the [Fink](https://fink-portal.org)
alert broker for LSST/Rubin commissioning data, with the goal of identifying
stable stellar and galactic sources suitable for **atmospheric transparency calibration**.

---

## Context

During the Rubin Observatory Science Verification (SV) phase, alert packets are
distributed through the Fink broker, which enriches them with crossmatch metadata
from external catalogues (Gaia DR3, SIMBAD, Legacy Survey DR8, Mangrove, VSX, TNS).
The notebooks query the [Fink LSST API](https://api.lsst.fink-portal.org) to
download light curves in the six LSST bands (*u g r i z y*) and measure their
photometric stability (normalised RMS variability σ/⟨f⟩) per source class.

---

## Notebooks

### `01_fink_block_lightcurves.ipynb` — Data retrieval & light-curve analysis

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

### `02_fink_block_lightcurves_replot.ipynb` — Offline re-visualisation

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

### `03_fink_add_visitId.ipynb` — Add visit identifiers to light curve data

**What it does:**

Enriches the per-detection source tables produced by notebook 01 with the
**Rubin visit identifier** (`visitId`) needed to retrieve individual exposures
via the Butler.

1. Reads the `{group}_src.parquet` files from `data_FINK_BLOCK_LC_01/`.
2. Cross-matches the `r:visit` column returned by the Fink API against the
   visit index (`visit_index.csv`) to confirm and normalise visit IDs.
3. Writes back enriched Parquet files and a consolidated visit index.

**Outputs written to disk:**

| Path | Content |
|------|---------|
| `data_FINK_BLOCK_LC_01/visit_index.csv` | Unique visit IDs across all sources |
| `data_FINK_BLOCK_LC_01/{group}_src.parquet` | Source tables with normalised `visitId` |

---

### `04_fink_selectDIAObject_tovisitIddetector.ipynb` — Select objects by visit & detector

**What it does:**

Filters the object catalogue to keep only objects observed in a specific set of
visits and detector numbers, enabling targeted Butler queries.

1. Loads the enriched source tables from notebook 03.
2. Applies a user-defined selection on `visitId` and `detector` number.
3. Exports a filtered object list and a per-visit/detector summary table
   suitable for batch Butler `isr` or `calibrate` calls.

**Outputs written to disk:**

| Path | Content |
|------|---------|
| `data_FINK_BLOCK_LC_01/visit_summary_src.csv` | Per-visit source summary |
| `data_FINK_BLOCK_LC_01/visit_index_fp.csv` | Visit index for forced-photometry data |
| `data_FINK_BLOCK_LC_01/visit_summary_fp.csv` | Per-visit forced-photometry summary |

---

### `05_fink_download_objects.ipynb` — Download object-level aggregate summary

**What it does:**

Downloads **object-level aggregate statistics** from the Fink
`/api/v1/objects` endpoint for every `diaObjectId` in `flatness_metrics.csv`.
These columns (medians, means, global statistics computed across all diaSources)
are distinct from the per-detection and per-epoch data fetched in notebook 01.

1. Loads the unique `diaObjectId` list from `flatness_metrics.csv`
   (the canonical trace of `lc_cache` in notebook 01).
2. Probes the API schema with a single-object query and prints all available columns.
3. Iterates over all objects, querying `/api/v1/objects` with a configurable
   inter-request delay (`API_SLEEP = 0.25 s`).
4. Assembles the results into a single DataFrame, drops duplicate `diaObjectId`
   columns potentially returned by the API, and reports a fill-rate inventory.
5. Saves the result as both Parquet (primary) and CSV.
6. Verifies the output with a read-back check.

**Data flow:**
```
flatness_metrics.csv  →  unique diaObjectId values (objects in lc_cache)
    ↓
POST https://api.lsst.fink-portal.org/api/v1/objects   →  summary per diaObjectId
    ↓
data_FINK_BLOCK_LC_01/objects_all.parquet   (+  objects_all.csv)
```

**Outputs written to disk:**

| Path | Content |
|------|---------|
| `data_FINK_BLOCK_LC_01/objects_all.parquet` | Object-level aggregate summary (primary) |
| `data_FINK_BLOCK_LC_01/objects_all.csv` | Same data in CSV format |

---

### `06_fink_color_color_diagram.ipynb` — Colour-colour diagram (G−R) vs (R−I)

**What it does:**

Reads `objects_all.parquet` produced by notebook 05 and plots a
**colour-colour diagram** in AB magnitudes with error bars on both axes.

- **X-axis**: R − I (AB mag)
- **Y-axis**: G − R (AB mag)
- Error bars on both axes, propagated in quadrature from per-band magnitude uncertainties
- Objects colour-coded by classification group inherited from notebook 01

#### Flux → magnitude conversion

LSST/Fink fluxes are in nanojansky (nJy). The AB magnitude and its uncertainty are:

$$m = -2.5\log_{10}(f_{\rm nJy}) + 31.4, \qquad \sigma_m = \frac{2.5}{\ln 10}\,\frac{\sigma_f}{f}$$

Colour uncertainties are propagated in quadrature:

$$\sigma_{G-R} = \sqrt{\sigma_{m_g}^2 + \sigma_{m_r}^2}, \qquad
\sigma_{R-I} = \sqrt{\sigma_{m_r}^2 + \sigma_{m_i}^2}$$

#### Column-discovery strategy

The notebook automatically searches for per-band photometric columns in
`objects_all.parquet` using keyword pattern matching, with three fallback strategies:

1. **Flux columns found** → compute AB magnitudes from nJy fluxes.
2. **Magnitude columns found directly** → use them as-is.
3. **Fallback** → pivot `flatness_metrics.csv` (mean flux per band per object) and convert.

**Outputs written to disk:**

| Path | Content |
|------|---------|
| `figs_FINK_BLOCK_LC_01_01_02/colour_colour_gr_ri.png/.pdf` | Combined colour-colour diagram (all groups) |
| `figs_FINK_BLOCK_LC_01_01_02/magnitude_histograms_gri.png` | Magnitude distributions per band (g, r, i) |
| `figs_FINK_BLOCK_LC_01_01_02/colour_colour_gr_ri_per_group.png` | Split-panel diagram — one panel per group |

---

## Directory layout

```
03_fink_api_blockselections/
├── 01_fink_block_lightcurves.ipynb          # data retrieval & light-curve analysis
├── 02_fink_block_lightcurves_replot.ipynb   # offline re-visualisation
├── 03_fink_add_visitId.ipynb                # add Rubin visit identifiers
├── 04_fink_selectDIAObject_tovisitIddetector.ipynb  # select objects by visit & detector
├── 05_fink_download_objects.ipynb           # download object-level aggregate summary
├── 06_fink_color_color_diagram.ipynb        # colour-colour diagram (G−R) vs (R−I)
├── README.md                                # this file
├── data_FINK_BLOCK_LC_01/
│   ├── flatness_metrics.csv
│   ├── objects_all.parquet                  # produced by notebook 05
│   ├── objects_all.csv
│   ├── visit_index.csv
│   ├── visit_index_fp.csv
│   ├── visit_summary_src.csv
│   ├── visit_summary_fp.csv
│   ├── gaia_star_stable_fp.parquet
│   ├── gaia_star_stable_src.parquet
│   ├── gaia_star_variable_fp.parquet
│   ├── gaia_star_variable_src.parquet
│   ├── simbad_galaxy_fp.parquet
│   ├── simbad_galaxy_src.parquet
│   ├── simbad_AG?_fp.parquet
│   ├── simbad_AG?_src.parquet
│   ├── simbad_rG_fp.parquet
│   ├── simbad_rG_src.parquet
│   ├── mangrove_galaxy_2mass_fp.parquet
│   ├── mangrove_galaxy_2mass_src.parquet
│   ├── tns_transient_fp.parquet
│   ├── tns_transient_src.parquet
│   ├── vsx_variable_fp.parquet
│   ├── vsx_variable_src.parquet
│   ├── unclassified_fp.parquet
│   └── unclassified_src.parquet
├── figs_FINK_BLOCK_LC_01/                   # figures from notebook 01
├── figs_FINK_BLOCK_LC_01_AUG/              # figures from augmented variant
├── figs_FINK_BLOCK_LC_01_02/               # figures from notebooks 02 & 06
└── figs_FINK_BLOCK_LC_LMCSMC/             # figures for LMC/SMC variant
```

---

## Execution order

The notebooks must be run in order, as each one depends on outputs from the previous:

```
01  →  02  (optional re-plot, no API call)
01  →  03  →  04
01  →  05  →  06
```

---

## Requirements

| Package | Purpose |
|---------|---------|
| `requests` | Fink API HTTP calls (notebooks 01, 05 only) |
| `pandas ≥ 2.0` | DataFrames, Parquet I/O |
| `numpy` | Numerical computations |
| `matplotlib` | Plotting |
| `pyarrow` or `fastparquet` | Parquet backend for pandas |

Install with:
```bash
pip install requests pandas numpy matplotlib pyarrow
```
or activate the `conda_py313` environment already configured for this project.

---

## Key API notes

- The Fink LSST API requires the **`r:` column prefix** in cone-search requests
  (using `i:` causes HTTP 500 errors).
- Block flags (`b_*`) cannot be used as API filters; classification is done
  client-side via `f:xm_*` crossmatch columns returned by the cone search.
- Endpoints used across the notebooks:

| Endpoint | Method | Used in |
|----------|--------|---------|
| `/api/v1/conesearch` | POST | notebook 01 |
| `/api/v1/sources` | POST | notebook 01 |
| `/api/v1/fp` | POST | notebook 01 |
| `/api/v1/objects` | POST | notebook 05 |
| `/api/v1/blocks` | GET | notebook 01 |
| `/api/v1/tags` | GET | notebook 01 |

---

## Authors

Notebook series developed for the Rubin/LSST SV atmospheric transparency
calibration study using the Fink alert broker.
