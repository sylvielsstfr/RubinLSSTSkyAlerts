# 04_calib — Photometric Calibration Notebooks

**Author:** Sylvie Dagoret-Campagne (IJCLab / IN2P3 / CNRS)  
**Project:** Rubin LSST — Fink Alert Broker photometric calibration diagnostics  
**Creation date:** 2026-04-02  
**Last update:** 2026-05-13

---

## Overview

This directory contains a pipeline of Jupyter notebooks for photometric calibration
diagnostics using Fink broker alert data from the Rubin LSST Deep Drilling Fields (DDFs).
The pipeline starts from raw Fink API queries, builds enriched light-curve tables,
performs Gaia DR3 cross-matching, and produces a variety of calibration figures —
including relative-flux light curves, PSF/science/template flux comparisons,
zero-point proxies, focal-plane heatmaps, and dipole-residual cutout visualisations.

A key scientific hypothesis tested in the final notebooks is that **dipole PSF-subtraction
residuals** are responsible for triggering spurious Rubin AP alerts on intrinsically
stable Gaia stars (sources that should never appear as transients).

All notebooks use the `conda_py313` kernel (Python 3.13).  
All comments, docstrings, and variable names are in **English**.

---

## Data directories

| Directory | Content |
|---|---|
| `data_FINK_BLOCK_LC_01/` | Raw Fink src/fp parquet files, diaObject catalogues (all groups and Gaia-stable subset), flatness metrics, visit index CSVs |
| `data_FINK_BLOCK_LC_03/` | Enriched alert tables joined with Rubin visit metadata (Butler + consDb) |
| `data_FINK_BLOCK_LC_08/` | Fink–Gaia DR3 cross-match results from notebook 08 (cone-search method) |
| `data_FINK_BLOCK_LC_08b/` | Fink–Gaia DR3 cross-match results from notebook 08b (exact ID join method) |
| `data_FocalPlane/` | LSSTCam focal-plane geometry (`ccd_geometry.csv`) |
| `fullcutouts_{diaObjectId}/` | Downloaded cutout stamps for one Gaia-stable diaObject: `manifest.csv`, `manifest.parquet`, `cutouts/*.npy` |

---

## Notebook descriptions

### `01_fink_block_flatlightcurves.ipynb`

**Purpose:** Download, classify, and catalogue all Fink alert light curves for objects
in the LSST DDFs, enriched with full aggregated object-level statistics from
`/api/v1/objects`.

- Cone-searches on each DDF via `/api/v1/conesearch` (`r:` prefix).
- Classifies objects via Fink crossmatch metadata: Gaia stable stars, variable stars,
  TNS transients, solar-system objects, blazars, YSOs, GCVS/VSX variables, etc.
- Fetches per-band aggregated fluxes from `/api/v1/objects` (psfFluxMean, scienceFluxMean,
  psfFluxSigma, percentiles, etc.).
- Saves per-group parquet files (`{group}_src.parquet`, `{group}_fp.parquet`),
  `diaobj_catalogue.csv`, `diaobj_catalogue_gaia_stable.csv`, and `flatness_metrics.csv`
  to `data_FINK_BLOCK_LC_01/`.

---

### `02_fink_block_lightcurves_replot.ipynb`

**Purpose:** Reload parquet files from notebook 01 and reproduce all light-curve
visualisations without making any API call.

---

### `03_associateFinkAlerts-RubinVisits.ipynb`

**Purpose:** Enrich Fink alert tables with Rubin visit metadata via left-join on
`r:visit` ↔ Butler `id` / consDb `visit_id`.  
**Output:** `data_FINK_BLOCK_LC_03/src_joined_butler.parquet` (used by notebooks 04–09).

---

### `03b_check-RubinVisits.ipynb`

**Purpose:** Diagnostic notebook to inspect and validate Rubin visit metadata tables
before and after the join.

---

### `04_relativeFlux.ipynb` — `04b` — `04c` — `04c02` — `04d` — `04e`

**Purpose:** Relative-flux light curves (`psfFlux / median`) in various projections:
airmass (`04b`), with forced photometry (`04c`, `04c02`), all objects per DDF field
(`04d`), PSF/aperture zero-point proxy (`04e`).

---

### `05_fink_block_AlertsStatistic_PlotFocalPlane.ipynb` — `05b` — `05c`

**Purpose:** LSSTCam focal-plane heatmaps: alert counts (`05`), zero-point proxy per
CCD (`05b`), detection threshold proxy (`05c`).

---

### `06_relativeFlux_science.ipynb`

**Purpose:** Investigate whether DIA variability originates from the science image or
the template by comparing `scienceFlux`, `psfFlux`, and estimated `templateFlux`.

---

### `07_psfFlux_scienceFlux_templateFlux.ipynb` — `07b` — `07c` — `07d` — `07e`

**Purpose:** Raw (non-normalised) `psfFlux`, `scienceFlux`, and `templateFlux` in nJy
for the top-N diaObjects, with catalogue reference lines.  
Variants: colour-coded by airmass (`07b`), detector (`07c`), seeing (`07d`),
focal-plane trajectory (`07e`).

---

### `08_matchFinkAlertswithGaiaDR3.ipynb`

**Purpose:** Cross-match Fink diaObjects with Gaia DR3 by cone-search (5 arcsec).  
**Output:** `data_FINK_BLOCK_LC_08/fink_diaobj_gaia_match_matched.csv`.

---

### `08b_matchFinkAlertswithGaiaDR3.ipynb`

**Purpose:** Associate Fink diaObjects with Gaia DR3 via exact `dr3_source_id` join
(extracted from the Fink `target_name` field).  
**Output:** `data_FINK_BLOCK_LC_08b/fink_diaobj_gaia_join_matched.csv` (used by
notebooks 09b, 12a, 12b).

---

### `09_psfFlux_scienceFlux_templateFlux_GaiaDR3matching.ipynb`

**Purpose:** Same raw-flux display as notebook 07, restricted to Gaia DR3–matched
diaObjects (from notebook 08b, input from `data_FINK_BLOCK_LC_03/`), with Gaia
metadata added to figure titles.

---

### `09b_psfFlux_scienceFlux_templateFlux_GaiaDR3matching.ipynb`

**Purpose:** Variant of notebook 09 using flux data from `data_FINK_BLOCK_LC_01/`
(no Butler/consDb join required). Recovers all 146 Gaia-matched diaObjects via
glob-based parquet discovery (Fix B).

- Produces per-object 7-panel flux figures with Gaia G magnitude, stability class,
  and Fink group in the title.
- **Section 10** writes a summary statistics CSV (median psfFlux / scienceFlux /
  templateFlux per object and band) to:  
  `figs_FINK_BLOCK_LC_09b/median_flux_stats_gaia_all_gaia_groups.csv`  
  This file is the entry point for the cutout download pipeline (notebook 12a).

**Key output:**
- `figs_FINK_BLOCK_LC_09b/median_flux_stats_gaia_all_gaia_groups.csv`

---

### `10_objectmagcurves.ipynb`

**Purpose:** AB-magnitude light curves from the per-band aggregated catalogue fluxes,
using the noise model from Ivezić et al. 2019.

---

### `11_dipole_analysis.ipynb`

**Purpose:** Statistical investigation of the `r:isDipole` flag across Gaia stellar
categories and photometric bands.

- For each of `gaia_star_stable_hq`, `gaia_nophotgstar_stable_unknown_parallax`,
  and `gaia_star_variable`:
  - Histogram of dipole count and dipole fraction vs. scienceFlux (AB mag), per band.
  - Same histograms vs. psfFlux and templateFlux.
  - Comparative summary heatmap across categories.
- **Hypothesis tested:** bright stable stars produce more dipole-flagged DIA detections
  because the PSF subtraction fails when science and template PSFs are mismatched,
  generating a double residual (positive lobe + negative lobe) that triggers alerts.

---

### `12a_downloadAllCutouts.ipynb`

**Purpose:** Download all cutout stamps (Science, Template, Difference) for every
diaSource belonging to the **Gaia-stable** diaObjects identified in notebook 09b.

- Reads the target diaObjectId list from  
  `figs_FINK_BLOCK_LC_09b/median_flux_stats_gaia_all_gaia_groups.csv`,  
  filtered to `gaia_status == "Gaia stable"`.
- Imports and calls `download_full_cutouts()` from `fink_download_full_cutouts.py`
  (in the same directory) for each object.
- Already-downloaded objects are skipped (idempotent re-runs).
- Produces a disk-footprint summary per object.

**Output (one directory per object):**
```
fullcutouts_{diaObjectId}/
    manifest.csv          ← all diaSource metadata incl. dipole columns
    manifest.parquet
    cutouts/
        {diaSourceId}_{band}_Science.npy
        {diaSourceId}_{band}_Template.npy
        {diaSourceId}_{band}_Difference.npy
```

---

### `12b_viewCutouts.ipynb`

**Purpose:** Visualise the image-stamp triplet for every diaSource detection of a
user-selected Gaia-stable diaObject, in order to demonstrate that dipole residuals
generate spurious Rubin AP alerts.

- `DIAOBJECT_ID` is set at the top of the notebook; available objects:
  `313761042226217038`, `313774269803790362`, `313888627193544815`.
- All dipole metadata (`r:isDipole`, `r:dipoleFluxDiff`, `r:dipoleLength`,
  `r:dipoleAngle`, …) is read directly from `manifest.csv` (no parquet join needed).
- **Layout — one row per diaSource, 4 panels:**

| Panel | Image | Annotation |
|-------|-------|------------|
| 1 | **Science** (calexp) | scienceFlux [nJy], mag_AB |
| 2 | **Template** (coadd) | templateFlux [nJy], mag_AB |
| 3 | **Difference** (downloaded) | psfFlux [nJy]; mag_AB if psfFlux > 0 |
| 4 | **Science − Template** (computed) | residual dipole pattern |

- Rows labelled with visit, detector, band, date, SNR.
- Dipole-flagged rows highlighted with a red **🔴 DIPOLE** badge.
- Difference images displayed with the diverging colormap `RdBu_r`
  (red lobe = positive residual, blue lobe = negative residual).
- Figures saved to `figs_FINK_BLOCK_LC_12b/`.
- Section 7 adds a `psfFlux` light curve with dipole detections as red diamonds.

---

## Supporting script

### `fink_download_full_cutouts.py`

Downloads all cutouts (Science + Template + Difference) for a single diaObjectId
across all its diaSources and all filters, via the Fink REST API
(`/api/v1/sources` + `/api/v1/cutouts`).  
Saves `.npy` arrays and a `manifest.csv` with full diaSource metadata including
dipole fit parameters.  
Can be used as a CLI tool (`python fink_download_full_cutouts.py --obj_id <id>`)
or imported as a module (used by notebook 12a).

---

## Pipeline data flow

```
Fink API (/api/v1/conesearch, /api/v1/sources, /api/v1/fp, /api/v1/objects)
   │
   ▼
01_fink_block_flatlightcurves.ipynb
   │  data_FINK_BLOCK_LC_01/  {group}_src.parquet  diaobj_catalogue*.csv
   │
   ├──► 02  (replot)
   ├──► 05, 05b, 05c  (focal-plane heatmaps)  ◄── data_FocalPlane/
   ├──► 08   (Gaia DR3 cone-search match)  →  data_FINK_BLOCK_LC_08/
   └──► 08b  (Gaia DR3 exact-ID join)      →  data_FINK_BLOCK_LC_08b/
                                                fink_diaobj_gaia_join_matched.csv

Butler visitTable + consDb
   └──► 03  →  data_FINK_BLOCK_LC_03/src_joined_butler.parquet
                  │
                  ├──► 04, 04b–04e  (relative flux)
                  ├──► 06  (science vs template)
                  ├──► 07, 07b–07e  (raw flux)
                  └──► 09  (Gaia-matched raw flux)  ◄── data_FINK_BLOCK_LC_08b/

data_FINK_BLOCK_LC_01/ + data_FINK_BLOCK_LC_08b/
   └──► 09b  →  figs_FINK_BLOCK_LC_09b/median_flux_stats_gaia_all_gaia_groups.csv
                  │
                  ├──► 10  (magnitude light curves)
                  ├──► 11  (dipole statistics)
                  │
                  └──► 12a  (download cutouts via fink_download_full_cutouts.py)
                         │   fullcutouts_{diaObjectId}/manifest.csv + cutouts/*.npy
                         │
                         └──► 12b  (visualise cutouts + dipole badges)
                                    figs_FINK_BLOCK_LC_12b/
```

---

## Key conventions

| Convention | Detail |
|---|---|
| **Flux unit** | nJy (nano-Jansky) |
| **AB magnitude** | m = −2.5 log₁₀(f [nJy] / 3631×10⁹) |
| **psfFlux** | Difference-image PSF flux (can be negative) |
| **scienceFlux** | PSF flux on the science calexp (always positive) |
| **templateFlux** | PSF flux on the coadd template |
| **isDipole** | `r:isDipole` flag from the Rubin AP pipeline — True when PSF subtraction produces a double-lobe residual |
| **Gaia stable** | `gaia_star_stable_hq` or `gaia_nophotgstar_stable_unknown_parallax` |
| **Catalog prefix** | `r:` = diaSource/diaObject table fields; `f:` = Fink-computed fields |

---

## Dependencies

```
python >= 3.13
pandas, numpy, matplotlib, astropy, tqdm
requests    (Fink REST API calls — notebooks 01, 12a and fink_download_full_cutouts.py)
ipympl      (optional — interactive %matplotlib widget backend)
```
