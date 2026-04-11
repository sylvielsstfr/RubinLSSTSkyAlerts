# 04_calib — Photometric Calibration Notebooks

**Author:** Sylvie Dagoret-Campagne (IJCLab / IN2P3 / CNRS)  
**Project:** Rubin LSST — Fink Alert Broker photometric calibration diagnostics  
**Creation date:** 2026-04-02  
**Last update:** 2026-04-11

---

## Overview

This directory contains a pipeline of Jupyter notebooks for photometric calibration
diagnostics using Fink broker alert data from the Rubin LSST Deep Drilling Fields (DDFs).
The pipeline starts from raw Fink API queries, builds enriched light-curve tables,
performs Gaia DR3 cross-matching, and produces a variety of calibration figures —
including relative-flux light curves, PSF/science/template flux comparisons with
catalogue reference lines, zero-point proxies, and focal-plane heatmaps.

All notebooks use the `conda_py313` kernel (Python 3.13).  
All comments, docstrings, and variable names are in **English**.

---

## Data directories

| Directory | Content |
|---|---|
| `data_FINK_BLOCK_LC_01/` | Raw Fink src/fp parquet files, diaObject catalogues (all groups and Gaia-stable subset), flatness metrics, visit index CSVs |
| `data_FINK_BLOCK_LC_03/` | Enriched alert tables joined with Rubin visit metadata (Butler + consDb) |
| `data_FINK_BLOCK_LC_03b/` | Diagnostic figures produced by notebook 03b |
| `data_FINK_BLOCK_LC_08/` | Fink–Gaia DR3 cross-match results from notebook 08 (cone-search method) |
| `data_FINK_BLOCK_LC_08b/` | Fink–Gaia DR3 cross-match results from notebook 08b (exact ID join method) |
| `data_FocalPlane/` | LSSTCam focal-plane geometry (`ccd_geometry.csv`) |

---

## Notebook descriptions

### `01_fink_block_flatlightcurves.ipynb`

**Purpose:** Download, classify, and catalogue all Fink alert light curves for objects in the LSST DDFs, enriched with full aggregated object-level statistics from the Fink `/api/v1/objects` endpoint.

- Performs cone-searches on each DDF via the Fink REST API (`/api/v1/conesearch`, `r:` prefix).
- Deduplicates by `diaObjectId`, downloads full DIA-source light curves (`/api/v1/sources`) and forced photometry (`/api/v1/fp`).
- Classifies each object using Fink crossmatch metadata (`f:xm_*`): Gaia stable stars (`gaia_star_stable`, `gaia_star_stable_hq`, `gaia_star_unknown_parallax`), variable stars, TNS transients, solar-system objects, blazars, YSOs, GCVS/VSX variables, SIMBAD types, etc.
- **Section 4c (new):** fetches all aggregated per-band flux statistics from `/api/v1/objects` in batches of 50 IDs (prefix `r:`, all columns returned without explicit column list). Columns include: `r:{b}_psfFluxMean`, `r:{b}_psfFluxSigma`, `r:{b}_psfFluxMax/Min/NData`, `r:{b}_psfFluxLinearSlope`, `r:{b}_psfFluxChi2`, `r:{b}_psfFluxPercentile05/25/50/75/95`, `r:{b}_scienceFluxMean`, `r:{b}_templateFluxMean`, `r:{b}_apFluxMean`, `r:target_name`, `r:observation_reason`, etc.
- The enriched tables are merged into two output catalogues saved to `data_FINK_BLOCK_LC_01/`:
  - `diaobj_catalogue.csv` — all groups, full aggregated columns
  - `diaobj_catalogue_gaia_stable.csv` — Gaia-stable groups only, same columns
- Also saves per-group parquet files (`{group}_src.parquet`, `{group}_fp.parquet`) and `flatness_metrics.csv`.

**Key outputs:**
- `data_FINK_BLOCK_LC_01/diaobj_catalogue.csv`
- `data_FINK_BLOCK_LC_01/diaobj_catalogue_gaia_stable.csv`
- `data_FINK_BLOCK_LC_01/gaia_star_stable_src.parquet`

---

### `02_fink_block_lightcurves_replot.ipynb`

**Purpose:** Reload the parquet files produced by notebook 01 and reproduce all light-curve visualisations without making any API call.

- Reads `{group}_src.parquet` and `{group}_fp.parquet` from `data_FINK_BLOCK_LC_01/`.
- Plots flux and AB-magnitude light curves (including luptitudes for DIA negative fluxes) per source group.
- A `PLOT_MODE` switch allows selecting: all groups, calibration-suitable groups only, or excluded groups only.

---

### `03_associateFinkAlerts-RubinVisits.ipynb`

**Purpose:** Enrich the Fink alert tables with Rubin visit metadata via a left-join on the visit identifier.

- Joins `gaia_star_stable_src.parquet` and `gaia_star_stable_fp.parquet` with the Butler visitTable and consDb visitTable.
- Join key: `r:visit` (alert) ↔ `id` / `visit_id` (Butler / consDb), cast to `int64`.
- Adds visit-level columns: observing conditions, airmass, field name, seeing, etc.
- Writes four enriched parquet files to `data_FINK_BLOCK_LC_03/`.

**Key output:** `data_FINK_BLOCK_LC_03/src_joined_butler.parquet` (used by all subsequent notebooks)

---

### `03b_check-RubinVisits.ipynb`

**Purpose:** Diagnostic notebook to inspect and validate the Rubin visit metadata tables before and after the join with Fink alerts.

- Reads raw Butler and consDb visitTables from `../05_runbindata_visits/data_fromlsst/`.
- Checks column availability, dtype consistency, and coverage of the 13-digit visit IDs.
- Produces diagnostic plots saved to `data_FINK_BLOCK_LC_03b/`.

---

### `04_relativeFlux.ipynb`

**Purpose:** Display relative-flux PSF and aperture light curves for the top-ranked DIA objects.

- y-axis: `psfFlux(t) / median(psfFlux)` or `apFlux(t) / median(apFlux)` with propagated error bars.
- x-axis bottom: Δt [days]; top: calendar dates.
- 7-panel layout per object (`u | g | r | i | z | y | all-bands`).
- Outputs a summary CSV of σ(ratio) per object and band.

---

### `04b_relativeFlux_compairmass.ipynb`

**Purpose:** Same as notebook 04 but with markers colour-coded by **airmass** (X = 1/cos z).

---

### `04c_relativeFlux_withfp.ipynb`

**Purpose:** Overlay forced-photometry (fp) on the PSF relative-flux light curves.

- Normalisation: median of src psfFlux per (diaObjectId, band).
- src = filled circle; fp = hollow circle.
- Also reads `data_FINK_BLOCK_LC_01/gaia_star_stable_fp.parquet`.

---

### `04c02_relativeFlux_withfp_showdetectors.ipynb`

**Purpose:** Variant of `04c` where each measurement is colour-coded by **detector number (CCD ID)** using a `tab20+tab20b` palette.

---

### `04d_relativeFlux_withfp_alllcinDDF.ipynb`

**Purpose:** All DIA objects from the same DDF field on a single figure (one per field).

- Colour = object identity; marker shape = band; fill = src (solid) or fp (hollow).

---

### `04e_relativeFlux_ZP.ipynb`

**Purpose:** Display the PSF-to-aperture flux ratio as a zero-point proxy light curve.

$$\Delta m(t) = 2.5 \log_{10}\!\left(\frac{F_{\rm psf}(t)}{F_{\rm ap}(t)}\right), \quad \sigma_{\Delta m} = \frac{2.5}{\ln 10}\sqrt{\left(\frac{\sigma_{\rm psf}}{F_{\rm psf}}\right)^2 + \left(\frac{\sigma_{\rm ap}}{F_{\rm ap}}\right)^2}$$

- Section 9 produces a focal-plane heatmap of ⟨Δm⟩ and σ(Δm).

---

### `05_fink_block_AlertsStatistic_PlotFocalPlane.ipynb`

**Purpose:** Alert count heatmap on the LSSTCam focal plane per CCD.

- Groups src alerts by `r:detector`, plots polygon CCD map from `data_FocalPlane/ccd_geometry.csv`.

---

### `05b_fink_block_ZP.ipynb`

**Purpose:** Dual focal-plane heatmap of the zero-point proxy Δm per CCD: median (left) and RMS (right). Repeated per band.

---

### `05c_fink_block_FluxThreshold.ipynb`

**Purpose:** Per-CCD detection threshold proxy using median psfFlux: all-band heatmap, per-band heatmap, per-band radial error plots.

---

### `06_relativeFlux_science.ipynb`

**Purpose:** Investigate whether DIA light-curve variability originates from the science image or the template.

- Three figure series per object: `scienceFlux/median`, overlay `scienceFlux` vs `psfFlux`, estimated `templateFlux = scienceFlux − psfFlux`.

---

### `07_psfFlux_scienceFlux_templateFlux.ipynb`

**Purpose:** Display raw (non-normalised) `psfFlux`, `scienceFlux`, and `templateFlux` in nJy for the top-N DIA objects.

- 7-panel layout per object: 6 per-band panels (u g r i z y) + 1 combined all-bands panel.
- **Catalogue reference lines (new):** in each per-band subplot, two horizontal lines from `data_FINK_BLOCK_LC_01/diaobj_catalogue_gaia_stable.csv` (or `diaobj_catalogue.csv`) show the object-level aggregated fluxes:
  - **dash-dot (`-.-`)** : `r:{b}_scienceFluxMean` — labelled `cat sciFluxMean` in legend
  - **dotted (`:`)** : `r:{b}_psfFluxMean` — labelled `cat psfFluxMean` in legend
  - In the 7th (all-bands) subplot: same lines drawn thin (lw=0.7, alpha=0.45) in band colour, without legend labels.
- Data source: `data_FINK_BLOCK_LC_03/src_joined_butler.parquet`.
- Reference fluxes: `data_FINK_BLOCK_LC_01/diaobj_catalogue_gaia_stable.csv`.
- Figures saved to `figs_FINK_BLOCK_LC_07/`.

---

### `07b_psfFlux_scienceFlux_templateFlux_compairmass.ipynb`

**Purpose:** Same three-flux raw display as notebook 07, colour-coded by **airmass**.

---

### `07c_psfFlux_scienceFlux_templateFlux_showdetector.ipynb`

**Purpose:** Same three-flux raw display as notebook 07, colour-coded by **CCD detector number**.

---

### `07d_psfFlux_scienceFlux_templateFlux_compseeing.ipynb`

**Purpose:** Same three-flux raw display as notebook 07, colour-coded by **seeing** (PSF FWHM).

---

### `07e_psfFlux_scienceFlux_templateFlux_FocalPlane.ipynb`

**Purpose:** Correlate flux variability with the trajectory of observations across the LSSTCam focal plane.

- 2-row layout per object: flux time series (top) + focal-plane CCD map (bottom), both colour-coded by time.

---

### `08_matchFinkAlertswithGaiaDR3.ipynb`

**Purpose:** Cross-match Fink diaObjects with the Gaia DR3 reference catalogue using a **cone-search** (astropy `match_to_catalog_sky`).

- Input: `diaobj_catalogue_gaia_stable.csv` (positions) + `../06_gaia/data_GAIA_STARCAT_DR3_03/allgaia_sources_allddf.csv`.
- Match radius: 5 arcsec.
- Produces 8 diagnostic figures: separation histogram, sky maps, stability bar charts, G-mag distribution, variability flags, astrometric residuals.
- Outputs to `data_FINK_BLOCK_LC_08/`:
  - `fink_diaobj_gaia_match_all.csv` — all Fink objects + match flag + Gaia columns
  - `fink_diaobj_gaia_match_matched.csv` — matched objects only

---

### `08b_matchFinkAlertswithGaiaDR3.ipynb`

**Purpose:** Associate Fink diaObjects with Gaia DR3 sources via **exact DR3 source_id join** (no cone-search).

- Input: `data_FINK_BLOCK_LC_01/diaobj_catalogue_gaia_stable.csv` (which carries `target_name = "Gaia DR3 <source_id>"`).
- Extracts the numeric `source_id` from `target_name` using `str.split()[-1]` and performs a pandas left-merge on `source_id`.
- No angular tolerance — the match is exact and unambiguous.
- Same 8 diagnostic figures as notebook 08 (adapted: fig01 shows match completeness instead of separation histogram; fig07 shows astrometric residuals for the exact match; fig08 shows `nDiaSources` distribution for matched vs unmatched).
- Outputs to `data_FINK_BLOCK_LC_08b/`:
  - `fink_diaobj_gaia_join_all.csv`
  - `fink_diaobj_gaia_join_matched.csv`
  - `fink_diaobj_gaia_join_unmatched.csv`

---

### `09_psfFlux_scienceFlux_templateFlux_GaiaDR3matching.ipynb`

**Purpose:** Same raw-flux display as notebook 07, but **restricted to Gaia DR3–matched diaObjects** identified by notebook 08b, with Gaia metadata (G magnitude, stability class, Fink group) added to each figure title.

- Reads the flux parquet from `data_FINK_BLOCK_LC_03/` and filters to `diaObjectId` values present in `data_FINK_BLOCK_LC_08b/fink_diaobj_gaia_join_matched.csv`.
- The helper `get_gaia_meta(obj_id)` attaches `{group, field, G_mag, gaia_stable, gaia_variable, gaia_status, dr3_id}` to every figure title.
- **Catalogue reference lines (new):** same as notebook 07 — per-band `r:{b}_scienceFluxMean` (dash-dot) and `r:{b}_psfFluxMean` (dotted) horizontal lines from `data_FINK_BLOCK_LC_01/diaobj_catalogue_gaia_stable.csv`; thin lines without legend in the combined 7th panel.
- Additional sections: per-band multi-object overview (section 9) and summary statistics CSV with Gaia metadata columns (section 10).
- Data sources:
  - Flux data: `data_FINK_BLOCK_LC_03/src_joined_butler.parquet`
  - Gaia match: `data_FINK_BLOCK_LC_08b/fink_diaobj_gaia_join_matched.csv`
  - Reference fluxes: `data_FINK_BLOCK_LC_01/diaobj_catalogue_gaia_stable.csv`
- Figures saved to `figs_FINK_BLOCK_LC_09/`.

---

## Pipeline data flow

```
Fink API (/api/v1/conesearch, /api/v1/sources, /api/v1/fp, /api/v1/objects)
   │
   ▼
01_fink_block_flatlightcurves.ipynb
   │  data_FINK_BLOCK_LC_01/
   │    ├── {group}_src.parquet, {group}_fp.parquet
   │    ├── diaobj_catalogue.csv           (all groups + objects API aggregates)
   │    ├── diaobj_catalogue_gaia_stable.csv  (Gaia-stable subset)
   │    ├── flatness_metrics.csv
   │    └── visit_index.csv
   │
   ├──► 02_fink_block_lightcurves_replot.ipynb
   │
   ├──► 05_fink_block_AlertsStatistic_PlotFocalPlane.ipynb  ◄── data_FocalPlane/
   ├──► 05b_fink_block_ZP.ipynb                            ◄── data_FocalPlane/
   ├──► 05c_fink_block_FluxThreshold.ipynb                 ◄── data_FocalPlane/
   │
   ├──► 08_matchFinkAlertswithGaiaDR3.ipynb   ◄── ../06_gaia/ Gaia DR3 catalogue
   │       └── data_FINK_BLOCK_LC_08/  (cone-search match)
   │
   └──► 08b_matchFinkAlertswithGaiaDR3.ipynb  (exact ID join)
           └── data_FINK_BLOCK_LC_08b/
                 ├── fink_diaobj_gaia_join_matched.csv
                 ├── fink_diaobj_gaia_join_all.csv
                 └── fink_diaobj_gaia_join_unmatched.csv

Butler visitTable + consDb visitTable
   ├──► 03b_check-RubinVisits.ipynb  (validation / diagnostics)
   └──► 03_associateFinkAlerts-RubinVisits.ipynb ◄── also reads data_FINK_BLOCK_LC_01/
           └── data_FINK_BLOCK_LC_03/
                 └── src_joined_butler.parquet  (+ fp, consdb variants)
                        │
                        ├──► 04_relativeFlux.ipynb
                        ├──► 04b_relativeFlux_compairmass.ipynb
                        ├──► 04c_relativeFlux_withfp.ipynb            ◄── data_FINK_BLOCK_LC_01/ (fp)
                        ├──► 04c02_relativeFlux_withfp_showdetectors.ipynb ◄── data_FINK_BLOCK_LC_01/ (fp)
                        ├──► 04d_relativeFlux_withfp_alllcinDDF.ipynb ◄── data_FINK_BLOCK_LC_01/ (fp)
                        ├──► 04e_relativeFlux_ZP.ipynb
                        ├──► 06_relativeFlux_science.ipynb
                        │
                        ├──► 07_psfFlux_scienceFlux_templateFlux.ipynb
                        │       ◄── data_FINK_BLOCK_LC_01/diaobj_catalogue_gaia_stable.csv  (ref lines)
                        ├──► 07b_psfFlux_scienceFlux_templateFlux_compairmass.ipynb
                        ├──► 07c_psfFlux_scienceFlux_templateFlux_showdetector.ipynb
                        ├──► 07d_psfFlux_scienceFlux_templateFlux_compseeing.ipynb
                        ├──► 07e_psfFlux_scienceFlux_templateFlux_FocalPlane.ipynb ◄── data_FocalPlane/
                        │
                        └──► 09_psfFlux_scienceFlux_templateFlux_GaiaDR3matching.ipynb
                                ◄── data_FINK_BLOCK_LC_08b/fink_diaobj_gaia_join_matched.csv
                                ◄── data_FINK_BLOCK_LC_01/diaobj_catalogue_gaia_stable.csv  (ref lines)
```

---

## Key conventions across notebooks

| Convention | Detail |
|---|---|
| **Flux unit** | nJy (nano-Jansky) |
| **Reference lines in flux plots** | dash-dot (`-.-`) = `r:{b}_scienceFluxMean` from catalogue; dotted (`:`) = `r:{b}_psfFluxMean` from catalogue |
| **Source markers** | filled circles `●` = scienceFlux / src; open squares `□` = psfFlux / src |
| **Forced photometry markers** | hollow circles `○` = fp (same colour as band) |
| **Catalogue column prefix** | `r:` = object-level aggregates from `/api/v1/objects`; `f:` = Fink crossmatch metadata |
| **Gaia group names** | `gaia_star_stable` (Plx/ePlx < 5), `gaia_star_stable_hq` (Plx/ePlx ≥ 5), `gaia_star_unknown_parallax` |

---

## Dependencies

```
python >= 3.13
pandas, numpy, matplotlib, astropy
requests        (Fink REST API calls — notebook 01 only)
ipympl          (optional — enables interactive %matplotlib widget)
```

The Fink broker REST API is only called in notebook 01. All subsequent notebooks
work exclusively from local parquet and CSV files.
