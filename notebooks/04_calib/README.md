# 04_calib — Photometric Calibration Notebooks

**Author:** Sylvie Dagoret-Campagne (IJCLab / IN2P3 / CNRS)  
**Project:** Rubin LSST — Fink Alert Broker photometric calibration diagnostics  
**Creation date:** 2026-04-02
**Last update:** 2026-04-02

---

## Overview

This directory contains a pipeline of Jupyter notebooks for photometric calibration
diagnostics using Fink broker alert data from the Rubin LSST Deep Drilling Fields (DDFs).
The pipeline starts from raw Fink API queries, builds enriched light-curve tables,
and produces a variety of calibration figures — including relative-flux light curves,
PSF-vs-aperture zero-point proxies, and focal-plane heatmaps.

All notebooks use the `conda_py313` kernel (Python 3.13).  
All comments, docstrings, and variable names are in **English**.

---

## Data directories

| Directory | Content |
|---|---|
| `data_FINK_BLOCK_LC_01/` | Raw Fink src and fp parquet files + flatness metrics CSV |
| `data_FINK_BLOCK_LC_03/` | Enriched alert tables joined with Rubin visit metadata |
| `data_FocalPlane/` | LSSTCam focal-plane geometry (`ccd_geometry.csv`) |

---

## Notebook descriptions

### `01_fink_block_flatlightcurves.ipynb`

**Purpose:** Download and classify Fink alert light curves for objects in the LSST DDFs.

- Performs cone-searches on each DDF via the Fink REST API (`/api/v1/conesearch`, `r:` column prefix).
- Deduplicates by `diaObjectId`, downloads full DIA-source light curves (`/api/v1/sources`) and forced photometry (`/api/v1/fp`).
- Classifies each object into a group using Fink crossmatch metadata (`f:xm_*` columns): Gaia stable stars, Gaia variable stars, TNS transients, solar-system objects, blazars, YSOs, GCVS/VSX variables, SIMBAD types, etc.
- Computes **flatness metrics** σ/⟨F⟩ per group to rank source categories for calibration suitability.
- Saves per-group parquet files (`{group}_src.parquet`, `{group}_fp.parquet`) and `flatness_metrics.csv` to `data_FINK_BLOCK_LC_01/`.

**Key output:** `data_FINK_BLOCK_LC_01/gaia_star_stable_src.parquet`, `gaia_star_stable_fp.parquet`

---

### `02_fink_block_lightcurves_replot.ipynb`

**Purpose:** Reload the parquet files produced by notebook 01 and reproduce all light-curve visualisations without making any API call.

- Reads `{group}_src.parquet` and `{group}_fp.parquet` from `data_FINK_BLOCK_LC_01/`.
- Plots flux and AB-magnitude light curves (including luptitudes for DIA negative fluxes) per source group.
- A `PLOT_MODE` switch allows selecting: all groups, calibration-suitable groups only, or excluded groups only.

---

### `03_associateFinkAlerts-RubinVisits.ipynb`

**Purpose:** Enrich the Fink alert tables with Rubin visit metadata via a left-join on the visit identifier.

- Joins `gaia_star_stable_src.parquet` and `gaia_star_stable_fp.parquet` (from notebook 01) with the Butler visitTable and the consDb visitTable (both produced at USDF).
- Join key: `r:visit` (alert side) ↔ `id` / `visit_id` (Butler / consDb side), cast to `int64`.
- Adds visit-level columns: observing conditions, airmass, field name, seeing, etc.
- Writes four enriched parquet files to `data_FINK_BLOCK_LC_03/`:
  `src_joined_butler.parquet`, `src_joined_consdb.parquet`, `fp_joined_butler.parquet`, `fp_joined_consdb.parquet`.

**Key output:** `data_FINK_BLOCK_LC_03/src_joined_butler.parquet` (used by all subsequent notebooks)

---

### `04_relativeFlux.ipynb`

**Purpose:** Display relative-flux PSF and aperture light curves for the top-ranked DIA objects.

- Loads the enriched alert table from `data_FINK_BLOCK_LC_03/` (butler preferred, consdb fallback).
- Selects the N top-ranked DIA objects by decreasing alert count.
- For each object: 7-panel figure (`u | g | r | i | z | y | all-bands`).
  - **y-axis:** `psfFlux(t) / median(psfFlux)` or `apFlux(t) / median(apFlux)` with propagated error bars.
  - **x-axis bottom:** Δt [days] from first alert; **x-axis top:** calendar dates.
- Produces three series of figures: PSF relative flux, AP relative flux, and PSF vs AP overlay.
- Outputs a summary CSV of σ(ratio) per object and band.

---

### `04b_relativeFlux_compairmass.ipynb`

**Purpose:** Same relative-flux light curves as notebook 04, but with markers colour-coded by a third variable (default: **airmass**).

- Computes airmass = 1/cos(zenith angle [rad]) from the visit metadata column.
- Uses a shared vertical colour-bar (`jet` colourmap) on the right of each 7-panel row.
- Produces three series of figures (PSF, AP, PSF vs AP) with the third-variable colour encoding.
- Useful for diagnosing whether photometric scatter correlates with airmass or other observing conditions.

---

### `04c_relativeFlux_withfp.ipynb`

**Purpose:** Overlay forced-photometry (fp) points on the PSF relative-flux light curves (src only; apFlux ignored).

- Loads src data from `data_FINK_BLOCK_LC_03/` and fp data from `data_FINK_BLOCK_LC_01/gaia_star_stable_fp.parquet`.
- **Normalisation convention:** the median of `src psfFlux` per *(diaObjectId, band)* is used for both src and fp normalisation. Bands without src are skipped gracefully.
- **Visual convention:** src = filled circle; fp = hollow circle with edge colour = band colour.
- 7-panel layout per object; subplot 7 shows all bands with the same src/fp encoding.
- Outputs a summary CSV with σ(src ratio) and fp counts per object and band.

---

### `04d_relativeFlux_withfp_alllcinDDF.ipynb`

**Purpose:** Group all DIA objects from the same DDF field onto a single figure (one figure per field) instead of one figure per object.

- Derived from notebook 04c; same src + fp data, same normalisation convention.
- **Visual encoding:** colour = diaObject identity (tab20 + tab20b palette, 40 distinct colours); marker shape = band (`u=○, g=□, r=△, i=◇, z=▽, y=+`); fill = src (solid) or fp (hollow).
- Subplot 7 carries two separate legends: object colours and band shapes.
- Handles up to 30+ superimposed light curves per field.
- Outputs one figure per DDF field and a summary CSV with σ and fp counts per (field, object, band).

---

### `04e_relativeFlux_ZP.ipynb`

**Purpose:** Display the PSF-to-aperture flux ratio as a zero-point proxy light curve per DIA object.

The plotted quantity is:

$$\Delta m(t) = 2.5 \log_{10}\!\left(\frac{F_{\rm psf}(t)}{F_{\rm ap}(t)}\right)$$

with propagated 1-sigma error:

$$\sigma_{\Delta m} = \frac{2.5}{\ln 10}\,\sqrt{\left(\frac{\sigma_{\rm psf}}{F_{\rm psf}}\right)^2 + \left(\frac{\sigma_{\rm ap}}{F_{\rm ap}}\right)^2}$$

- Reference line at Δm = 0 (perfect PSF calibration); points with non-positive flux are masked and shown as `×` markers.
- 7-panel layout per object (same as notebooks 04–04c).
- Section 9 produces an overview heatmap of ⟨Δm⟩ and σ(Δm) across all top-N objects and bands.
- Outputs summary CSV with `dm_mean`, `dm_std`, `n_valid` per object and band.

---

### `05_fink_block_AlertsStatistic_PlotFocalPlane.ipynb`

**Purpose:** Visualise alert statistics on the LSSTCam focal plane as a heatmap.

- Loads all src groups from `data_FINK_BLOCK_LC_01/` and concatenates `gaia_star_stable` + `gaia_star_stable_hq`.
- Groups by `r:detector` (CCD number) and counts the number of alerts per detector.
- Renders the LSSTCam focal plane using the polygon geometry from `data_FocalPlane/ccd_geometry.csv`, with each CCD coloured by alert count (logarithmic colour scale, grey for empty CCDs).
- Identifies which CCDs receive the most calibration alerts.

---

### `05b_fink_block_ZP.ipynb`

**Purpose:** Display the zero-point proxy Δm = 2.5 log₁₀(F_psf / F_ap) as two focal-plane heatmaps in a 1×2 figure.

- Computes Δm **per individual src alert**, independently of the diaObject — one value per (visit, CCD, source).
- Aggregates per CCD detector: **median** and **RMS (std)** of Δm.
- Produces a dual focal-plane figure:
  - **Left panel:** median Δm — diverging colormap `RdBu_r` centred on 0 (red = PSF brighter than aperture, blue = aperture brighter).
  - **Right panel:** RMS σ(Δm) — sequential colormap `plasma` (dark = stable, bright = unstable).
- A bonus section (section 9) repeats the same 1×2 figure for each photometric band `u g r i z y` to reveal chromatic dependencies.
- Saves a per-CCD summary CSV `ccd_zp_proxy_summary.csv`.

---

## Pipeline data flow

```
Fink API
   │
   ▼
01_fink_block_flatlightcurves.ipynb
   │  data_FINK_BLOCK_LC_01/  (src + fp parquets, flatness_metrics.csv)
   ├──────────────────────────────────────────────────────────┐
   ▼                                                          │
02_fink_block_lightcurves_replot.ipynb                        │
   (re-visualisation, no new data written)                    │
                                                              │
03_associateFinkAlerts-RubinVisits.ipynb ◄────────────────────┘
   │  data_FINK_BLOCK_LC_03/  (src/fp joined with visit metadata)
   │
   ├──► 04_relativeFlux.ipynb
   ├──► 04b_relativeFlux_compairmass.ipynb
   ├──► 04c_relativeFlux_withfp.ipynb  ◄── also reads data_FINK_BLOCK_LC_01/ (fp)
   ├──► 04d_relativeFlux_withfp_alllcinDDF.ipynb  ◄── also reads data_FINK_BLOCK_LC_01/ (fp)
   └──► 04e_relativeFlux_ZP.ipynb

data_FINK_BLOCK_LC_01/  ──► 05_fink_block_AlertsStatistic_PlotFocalPlane.ipynb
data_FINK_BLOCK_LC_01/  ──► 05b_fink_block_ZP.ipynb
data_FocalPlane/        ──► 05_fink_block_AlertsStatistic_PlotFocalPlane.ipynb
data_FocalPlane/        ──► 05b_fink_block_ZP.ipynb
```

---

## Dependencies

```
python >= 3.13
pandas, numpy, matplotlib, astropy
ipympl          (optional — enables interactive %matplotlib widget)
```

The Fink broker REST API is only called in notebook 01. All subsequent notebooks
work exclusively from local parquet files.
