# 97_SNIaGarazi — SNIa Light Curve Analysis (Garazi collaboration)

**Author:** Sylvie Dagoret-Campagne — IJCLab / IN2P3 / CNRS — Université Paris-Saclay  
**Created:** 2026-06-15  
**Context:** Rubin/LSST Fink broker — COSMOS Deep Drilling Field

---

## Overview

This directory contains notebooks for the analysis of a single Type Ia supernova
candidate identified in Rubin/LSST DP2 alerts and retrieved via the
[Fink broker](https://api.lsst.fink-portal.org).

The target object is:

| Field | Value |
|-------|-------|
| `r:diaObjectId` (Rubin) | `739161397740437575` |
| Fink internal `objectId` | `313629129605382159` |
| Photometric redshift (LegacyDR8) | see notebook `02` |

The collaboration context ("Garazi") refers to photometric data files provided
by a collaborator containing aperture fluxes, PSF fluxes, and scienceFlux
calibrated by the Rubin `photoCalib` pipeline on the tract 2704 DRP2 output.

---

## Notebooks

### `01_SNIaGarazi.ipynb` — Load and compare light curves

Loads two photometric data files:

- **Fink alert stream** (`data_NB97_01_SNIaGarazi/313629129605382159.csv`):
  multi-band `psfFlux` [nJy] from the DIA pipeline, including dipole columns.
- **Rubin DRP2 file** (`data_NB97_01_SNIaGarazi/lightcurve_tract_2704_i_739161397740437575.csv`):
  aperture flux (electrons), `psfFlux` and `scienceFlux` in nJy from Garazi.

Key operations:

- Baseline subtraction (pre-explosion median per band, with estimated explosion MJD).
- ApertureFlux recalibration: derives a `psfFlux / aperture_flux` scale factor
  to convert Garazi electron fluxes to nJy.
- SALT3 / SALT2-extended fit (fixed-z) via `sncosmo`, using the LegacyDR8
  photometric redshift as a prior.
- Single-panel SALT fit plot with per-band SNR in the legend.

Output figures saved in `figs_NB97_01_SNIaGarazi/`.

---

### `02_SNIaGarazi_fink_salt3.ipynb` — Full Fink download + SALT3 fit

Self-contained notebook that downloads all data from Fink directly.

**Data retrieval:**

- `/api/v1/sources` — DIA alert photometry (`psfFlux` [nJy]), dipole columns,
  and Fink cross-match columns (TNS, LegacyDR8, MANGROVE, Gaia DR3, SIMBAD).
- `/api/v1/fp` — Forced photometry at the DIA source position.

**Redshift priority:** TNS spec-z → LegacyDR8 photo-z → MANGROVE lum-dist → free-z.

**SALT fits:**

- Fixed-z fit (parameters: `t0`, `x0`, `x1`, `c`).
- Free-z two-pass fit: coarse χ² grid scan over `z ∈ [0.02, 1.50]`,
  followed by a refined free-z minimisation in a ±0.15 window around the
  grid minimum.

**Hubble diagram:** distance modulus μ via the Tripp formula
(`α=0.14`, `β=3.14`, `M_B=−19.3`), with flat ΛCDM overlay (H₀=70, Ωm=0.30).

Output figures saved in `figs_NB97_02_SNIaGarazi/`.  
Results summary saved as `data_NB97_02_SNIaGarazi/salt3_results_*.parquet`.

---

### `12_fetch_onecutouts.ipynb` — Fetch and display one FITS cutout

Fetches the Science / Template / Difference cutout triplet for the **first**
diaSource of the target object from Fink (`/api/v1/cutouts`).

Injects observation-time and observatory keywords into the FITS headers
(`MJD-OBS`, `TIMESYS`, `DATE-OBS`, `OBS-LAT`, `OBS-LONG`, `OBS-ELEV`)
before saving to disk (`<mjd>_cutout_<kind>.fits`).

Displays the Difference image with WCS axes and four direction overlays:

- **N** (red), **E** (blue): celestial cardinal directions via `SkyOffsetFrame`.
- **Z** (yellow): zenith direction = North rotated by the parallactic angle η.
- **Dip** (cyan ↔): dipole axis from `r:dipoleAngle` (PA convention, no offset).

Colourmap conventions: `RdBu_r` + `TwoSlopeNorm(vcenter=0)` for the Difference;
shared ZScale for Science and Template.

---

### `12b_viewSelectedCutoutsFits.ipynb` — Batch viewer for all diaSources

Reads FITS cutouts pre-downloaded by `12a_downloadSelectedCutoutsFits.ipynb`
(stored under `fullcutouts_fits_313629129605382159/cutouts/`) and produces
a **2 × 3 figure grid** per diaSource:

| | col 0 | col 1 | col 2 |
|---|---|---|---|
| **row 0** | Info panel | Science + N/E/Z | Template + N/E/Z |
| **row 1** | Light curve | DIA Difference + N/E/Z/Dip | Sci − Tpl + N/E/Z/Dip |

WCS direction vectors are derived from the PC matrix via `wcs.wcs.get_pc()`
(robust against cutouts with empty CTYPE keywords).  The parallactic angle η
is computed with the Meeus formula; the `.to_value(u.rad)` idiom avoids
astropy Quantity unit-propagation issues in `arctan2`.

Output figures (PDF + PNG) saved in `figs_DIPOLES_12b_fits/`.

---

## Ancillary files

| File / Directory | Description |
|------------------|-------------|
| `data_313629129605382159.csv` | Raw Fink src table (diaSources) for the target |
| `61058_0651439257_cutout_*.fits` | Example cutout FITS triplet (one diaSource) |
| `fullcutouts_fits_313629129605382159/` | Full FITS cutout archive (all diaSources) |
| `fink_download_full_cutouts_fits.py` | Script to batch-download FITS cutouts from Fink |
| `data_NB97_01_SNIaGarazi/` | Data produced by notebook 01 |
| `data_NB97_02_SNIaGarazi/` | Data produced by notebook 02 |
| `figs_NB97_01_SNIaGarazi/` | Figures produced by notebook 01 |
| `figs_NB97_02_SNIaGarazi/` | Figures produced by notebook 02 |
| `figs_DIPOLES_12b_fits/` | Figures produced by notebook 12b |

---

## Key scientific result

The dipole axis (`r:dipoleAngle`) is aligned with the **zenith direction** in
the observation plane.  This confirms that dipole artifacts in Rubin/LSST DIA
images are caused by **Differential Chromatic Refraction (DCR)**: a colour
mismatch between the science and template images shifts the PSF centroid along
the parallactic angle direction, producing a positive/negative dipole in the
difference image oriented along the Zenith arrow overlay.

`r:dipoleAngle` can therefore be used directly (without any 90° offset) as a
proxy for the parallactic angle.

---

## Software environment

Python 3.13, `conda_py313` kernel.  
Main dependencies: `astropy`, `sncosmo`, `matplotlib`, `pandas`, `numpy`, `requests`, `ipympl`.
