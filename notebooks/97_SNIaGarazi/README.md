# 97_SNIaGarazi — SNIa Light Curve Analysis (Garazi collaboration)

**Author:** Sylvie Dagoret-Campagne — IJCLab / IN2P3 / CNRS — Université Paris-Saclay  
**Created:** 2026-06-15  
**Last updated:** 2026-06-24  
**Context:** Rubin/LSST Fink broker — COSMOS Deep Drilling Field

---

## Overview

This directory contains notebooks for the analysis of a single Type Ia supernova
candidate identified in Rubin/LSST DP2 alerts and retrieved via the
[Fink LSST broker](https://api.lsst.fink-portal.org).

The primary target object is:

| Field | Value |
|-------|-------|
| `r:diaObjectId` (Rubin) | `739161397740437575` |
| Fink internal `objectId` | `313629129605382159` |
| Photometric redshift (LegacyDR8) | see notebook `01` / `02` |

A second candidate (`diaObjectId = 170226393328648251`) is analysed in
notebook `02` as a Garazi collaboration target.

The "Garazi" context refers to photometric data files provided by a collaborator
containing aperture fluxes, PSF fluxes, and `scienceFlux` calibrated by the
Rubin `photoCalib` pipeline on the tract 2704 DRP2 output.

### Column naming conventions

| Prefix | Meaning |
|--------|---------|
| `r:<col>` | LSST `diaSource` / `diaObject` field (prefix = table name, **not** the r band) |
| `f:<col>` | Fink-computed field (classifiers, cross-matches) |
| Flux unit | **nJy**, AB zeropoint = 31.4 |

---

## Notebooks

### `01_SNIaGarazi_fink_readfromfileandFitSalt3.ipynb` — Load from file + SALT3 fit

Loads two pre-downloaded photometric data files and fits a SALT3 light curve
with fixed redshift.

**Input data:**

- **Fink alert stream** (`data_NB97_01_SNIaGarazi/313629129605382159.csv`):
  multi-band `psfFlux` [nJy] from the DIA pipeline, including Fink cross-match
  columns (TNS, LegacyDR8, MANGROVE, Gaia DR3).
- **Rubin DRP2 file** (`data_NB97_01_SNIaGarazi/lightcurve_tract_2704_i_739161397740437575.csv`):
  aperture flux (electrons), `psfFlux` and `scienceFlux` [nJy] from the
  Garazi collaboration.

**Key operations:**

- Baseline subtraction: pre-explosion median per band using an estimated
  explosion MJD.
- ApertureFlux recalibration: derives a `psfFlux / aperture_flux` scale factor
  to convert Garazi electron counts to nJy.
- SALT3 / SALT2-extended fit (fixed-z) via `sncosmo`, using the LegacyDR8
  photometric redshift as a prior.
- Fisher ellipse plots (lower-triangle corner plot) from the SALT3 covariance
  matrix, at 68 % and 95 % CL (Δχ² = 2.30 and 6.17 for 2 d.o.f.).
  The axis range is computed independently per parameter from the marginal
  standard deviation `sqrt(cov[i,i] * Δχ²_95)`, which is the correct
  projection of the ellipse onto each axis regardless of its orientation.
- Hubble diagram with flat ΛCDM overlay and Tripp-formula distance modulus.

Output figures saved in `figs_NB97_01_SNIaGarazi/`.

---

### `02_SNIaGarazi_fink_downladfromapiandFitSalt3.ipynb` — Full Fink API download + SALT3 fit

Self-contained notebook that downloads all data live from the Fink LSST API
and performs the full SALT3 analysis pipeline.

**Data retrieval (Fink LSST API):**

- `/api/v1/sources` — DIA alert photometry (`r:psfFlux` [nJy]), dipole
  columns, and Fink cross-match columns (TNS, LegacyDR8, MANGROVE, Gaia DR3,
  SIMBAD, VSX, …). Results cached as Parquet.
- `/api/v1/fp` — Forced photometry at the DIA source position
  (`r:psfFlux` [nJy]). Endpoint parameter: `diaObjectId` (not `objectId`).
- `/api/v1/sources` (cross-match only) — Redshift lookup via
  `f:xm_tns_redshift`, `f:xm_legacydr8_zphot`, `f:xm_mangrove_lum_dist`.

**Redshift selection priority:** TNS spec-z → LegacyDR8 photo-z →
MANGROVE luminosity distance (converted to z via flat ΛCDM) → free-z fallback.

**SALT fits:**

- Fixed-z fit (free parameters: `t0`, `x0`, `x1`, `c`).
- Free-z two-pass fit: coarse χ² grid scan over `z ∈ [0.02, 1.50]`
  (100 steps), followed by a refined free-z minimisation initialised at the
  grid minimum within a ±0.15 window.

**Fisher ellipse plots** — corner plot (lower triangle) at 68 % & 95 % CL:

- All-parameter matrix: `(t0, x0, x1, c)` for fixed-z; `(z, t0, x0, x1, c)`
  for free-z.
- Cosmological sub-matrix: `(x1, c)` only.
- Redshift–stretch degeneracy plot: `(z, x1)` for the free-z fit, with an
  overlay of the reference redshift.

> **Bug fix (2026-06-24):** The axis range in `plot_fisher_ellipses()` was
> previously computed from the largest eigenvalue `vals[0]` and applied
> identically to both axes, causing the ellipse to appear flattened when the
> two parameters have very different scales (e.g. `x0 ~ 1e-5` vs `t0 ~ 60000`).
> The fix uses `sqrt(cov[i,i] * Δχ²_95)` independently per axis — the exact
> marginal projection of the ellipse onto each original axis.

**Hubble diagram:** distance modulus μ via the Tripp formula
(`α = 0.14`, `β = 3.14`, `M_B = −19.3`, Betoule+ 2014), compared to a flat
ΛCDM model (H₀ = 70 km/s/Mpc, Ωm = 0.30, ΩΛ = 0.70).

Output figures saved in `figs_NB97_02_SNIaGarazi/`.  
Results summary saved as `data_NB97_02_SNIaGarazi/salt3_results_<diaObjectId>.parquet`.

---

### `03_FicherEllipse.ipynb` — Fisher ellipse unit test / sandbox

Standalone development notebook used to prototype and validate the
`plot_fisher_ellipses()` function before integrating it into notebooks 01 and 02.

Uses a synthetic 3-parameter cosmological example (`Ωm`, `σ8`, `H0`) with a
hand-crafted covariance matrix to verify that:

- The ellipse orientation, width, and height are correctly derived from the
  eigendecomposition of the 2×2 sub-covariance matrix.
- The Δχ² levels (≈ 2.30 for 68 %, ≈ 6.17 for 95 %) match `scipy.stats.chi2.ppf`
  for 2 degrees of freedom.
- The axis ranges properly contain the ellipses for all pairs of parameters.

This notebook does **not** depend on any Fink data.

---

### `12_fetch_onecutouts.ipynb` — Fetch and display one FITS cutout triplet

Fetches the Science / Template / Difference FITS cutout triplet for the
**first** `diaSource` of the target object from the Fink API
(`/api/v1/cutouts`).

**Header enrichment:** injects observation-time and observatory keywords
(`MJD-OBS`, `TIMESYS`, `DATE-OBS`, `OBS-LAT`, `OBS-LONG`, `OBS-ELEV`)
before saving to disk as `<mjd>_cutout_<kind>.fits`.

**Difference image display** with WCS axes and four direction overlays:

| Arrow | Colour | Meaning |
|-------|--------|---------|
| **N** | red | Celestial North via `SkyOffsetFrame` |
| **E** | blue | Celestial East via `SkyOffsetFrame` |
| **Z** | yellow | Zenith direction = North rotated by the parallactic angle η |
| **Dip** | cyan ↔ | Dipole axis from `r:dipoleAngle` (standard PA, no offset) |

Colourmap: `RdBu_r` + `TwoSlopeNorm(vcenter=0)` for the Difference image;
shared ZScale limits for Science and Template.

---

### `12b_viewSelectedCutoutsFits.ipynb` — Batch viewer for all diaSource cutouts

Reads FITS cutouts pre-downloaded by a companion download script
(stored under `fullcutouts_fits_313629129605382159/cutouts/`) and produces
a **2 × 3 figure grid** per `diaSource`:

| | col 0 | col 1 | col 2 |
|---|---|---|---|
| **row 0** | Info panel (metadata) | Science + N/E/Z overlays | Template + N/E/Z overlays |
| **row 1** | Light curve (all bands) | DIA Difference + N/E/Z/Dip | Science − Template + N/E/Z/Dip |

**Implementation notes:**

- WCS direction vectors derived from `wcs.wcs.get_pc()` (robust against
  cutouts with empty `CTYPE` keywords).
- Parallactic angle η computed with the Meeus formula; the `.to_value(u.rad)`
  idiom avoids astropy `Quantity` unit-propagation issues inside `arctan2`.

Output figures (PDF + PNG) saved in `figs_DIPOLES_12b_fits/`.

---

## Utility scripts

### `apply_fisher_patch.py`

Standalone patch script that applies the asymmetric axis-range fix to
`plot_fisher_ellipses()` in notebook `02` (see bug fix note above).
Creates a `.bak` backup before modifying the notebook in place.

```bash
python apply_fisher_patch.py
```

### `fink_download_full_cutouts_fits.py`

Batch script to download the full FITS cutout triplet (Science / Template /
Difference) for all `diaSources` of the target object from the Fink API and
save them under `fullcutouts_fits_313629129605382159/`.

---

## Ancillary data files

| File / Directory | Description |
|------------------|-------------|
| `data_313629129605382159.csv` | Raw Fink src table (all diaSources for the primary target) |
| `61058_0651439257_cutout_*.fits` | Example FITS cutout triplet (one diaSource) |
| `fullcutouts_fits_313629129605382159/` | Full FITS cutout archive (all diaSources) |
| `swagger.json` | Fink LSST API OpenAPI specification snapshot |
| `data_NB97_01_SNIaGarazi/` | Parquet and CSV data produced by notebook `01` |
| `data_NB97_02_SNIaGarazi/` | Parquet and CSV data produced by notebook `02` |
| `figs_NB97_01_SNIaGarazi/` | Figures produced by notebook `01` |
| `figs_NB97_02_SNIaGarazi/` | Figures produced by notebook `02` |
| `figs_DIPOLES_12b_fits/` | Figures produced by notebook `12b` |

---

## Key scientific result

The dipole axis (`r:dipoleAngle`) is aligned with the **zenith direction** in
the observation plane. This confirms that dipole artifacts in Rubin/LSST DIA
images are caused by **Differential Chromatic Refraction (DCR)**: a colour
mismatch between the science and template images shifts the PSF centroid along
the parallactic angle direction, producing a positive/negative dipole in the
difference image oriented along the Zenith arrow overlay.

`r:dipoleAngle` can therefore be used directly as a proxy for the parallactic
angle — no 90° offset is required.

---

## Software environment

| Item | Value |
|------|-------|
| Python | 3.13 |
| Kernel | `conda_py313` |
| Key packages | `astropy`, `sncosmo`, `matplotlib`, `pandas`, `numpy`, `requests`, `ipympl`, `scipy` |
| Fink API base URL | `https://api.lsst.fink-portal.org/api/v1` |
