# 08_Dipoles — Dipole Artefact Analysis in Rubin LSST DIA Alerts

This directory contains notebooks dedicated to the characterisation of **dipole artefacts**
in Rubin LSST Difference Image Analysis (DIA) alerts retrieved via the Fink broker.

Dipoles arise in difference images when a PSF-subtracted source is slightly mis-registered
with respect to its template, leaving a positive-lobe / negative-lobe residual pattern.
Their spatial distribution, temporal evolution, per-object concentration, and angular
clustering are studied across the LSST **Deep Drilling Fields** (DDFs).

---

## Notebook overview

### Data retrieval — DDF conesearch

| Notebook | Description |
|----------|-------------|
| `00_show_cone_slicing_ddf.ipynb` | Utility / visualisation notebook. Draws the 3×3 mini-cone tiling strategy used to work around the Fink API conesearch size limit: the main DDF cone is covered by 9 overlapping sub-cones. No data download; pure geometry illustration. |
| `01_fink_dipoles_per_ddf.ipynb` | First-pass dipole retrieval. Performs a conesearch (`/api/v1/conesearch`) on each DDF with all dipole columns (`isDipole`, `dipoleFluxDiff`, `dipoleLength`, `dipoleAngle`, `dipoleChi2`, …) plus flux, observing metadata, and crossmatch columns. Produces spatial sky maps with dipole orientation arrows and temporal evolution plots of the dipole fraction per DDF and per band. Saves one parquet file per DDF to `data_DIPOLES_01/`. |
| `01b_fink_dipoles_per_ddf.ipynb` | Extended version of notebook 01 using the **sliced-cone + time-slice** strategy: the DDF cone is split into 3×3 spatial sub-cones and the time axis is divided into configurable slices to avoid API payload limits. Adds direction-of-dipole-axis plots per DDF. Saves to `data_DIPOLES_01b/`. |
| `01c_fink_dipoles_per_ddf.ipynb` | Same sliced-cone strategy as 01b but **without time slicing** — the full temporal baseline is retrieved in one pass per sub-cone. This produces the most complete per-DDF parquet files used as input for all downstream notebooks (02, 02b, 03b, 04). Saves to `data_DIPOLES_01c/`. |

### Spatial uniformity and angular correlation analysis

| Notebook | Description |
|----------|-------------|
| `02_fink_dipoles_uniformity.ipynb` | Tests the **angular uniformity** of DIA alert positions across all DDFs using the two-point angular correlation function $w(\theta)$ (Landy–Szalay estimator). Computes three correlation types per DDF: (1) auto-correlation of all alerts, (2) auto-correlation of `isDipole=True` alerts, (3) cross-correlation of non-dipoles × dipoles. Uses **TreeCorr** when available, with a NumPy/KDTree flat-sky fallback. Loads data from `data_DIPOLES_01c/` — no Fink API calls. Saves figures to `figs_DIPOLES_02/`. |
| `02b_fink_dipoles_uniformity_in_one_DDF.ipynb` | Same Landy–Szalay analysis as notebook 02 but restricted to a **single user-selected DDF** and split into configurable **time slices**. Each slice is rendered as one coloured curve in a summary figure, allowing investigation of whether dipole clustering evolves with time (e.g. as template quality improves). Loads from `data_DIPOLES_01c/`. Saves figures to `figs_DIPOLES_02b/`. |

### Per-object dipole concentration analysis

| Notebook | Description |
|----------|-------------|
| `03_dipoleobjectcorr.ipynb` | **Dipole concentration per diaObject** — conesearch variant. Retrieves alert catalogues via the Fink `/api/v1/conesearch` endpoint, deduplicates by `diaObjectId`, pre-selects objects with `nDiaSources >= NDIASOURCES_MIN`, then downloads full diaSources via `/api/v1/sources`. Computes per-object dipole counts and fractions per band, Lorenz curve + Gini coefficient, psfFlux−apFlux diagnostics, three-panel light curves, and angular stability of dipole direction. Saves data to `data_DIPOLES_03/`. |
| `03b_dipoleobjectcorr.ipynb` | **Dipole concentration per diaObject** — cached-parquet variant of notebook 03. The conesearch step is replaced by reading the per-DDF parquets already produced by `01c`. Only the `/api/v1/sources` download is kept. Adds Gini coefficient annotation and psfFlux−apFlux per-band histograms. All outputs (per-object source parquets, statistics, angle stability) written to `data_DIPOLES_03b/`. Figures to `figs_DIPOLES_03b/`. |
| `04_reloaddipoleobjectcorr.ipynb` | **Fully offline reload** of `03b`. Reads all files from `data_DIPOLES_03b/` (catalogue, statistics, concatenated sources, per-object parquets, angle table) and reproduces every figure of `03b` without any API call. Figures go to `figs_DIPOLES_04/`. Intended for quick re-inspection, parameter tweaking, and presentation preparation after `03b` has been run once. |

### Cutout inspection

| Notebook | Description |
|----------|-------------|
| `12a_downloadSelectedCutouts.ipynb` | Downloads science / template / difference image triplets (stamp cutouts) from the Fink `/api/v1/cutouts` endpoint for a user-defined list of diaObjectIds. Stores FITS cutouts in per-object subdirectories under `fullcutouts_{oid}/`. |
| `12b_viewSelectedCutouts.ipynb` | Displays the downloaded cutout triplets as multi-panel figures for visual inspection. Saves figures to `figs_DIPOLES_12b/`. |

---

## Key dipole columns (LSST DPDD / Fink)

| Column | Description |
|--------|-------------|
| `r:isDipole` | `True` if the source is classified as a dipole by the Rubin AP pipeline |
| `r:isNegative` | `True` if this detection is the negative lobe |
| `r:dipoleFitAttempted` | `True` if a dipole model fit was attempted |
| `r:dipoleFluxDiff` | Flux difference between positive and negative lobes (nJy) |
| `r:dipoleFluxDiffErr` | Uncertainty on `dipoleFluxDiff` (nJy) |
| `r:dipoleMeanFlux` | Mean of positive and negative lobe fluxes (nJy) |
| `r:dipoleMeanFluxErr` | Uncertainty on `dipoleMeanFlux` (nJy) |
| `r:dipoleLength` | Angular separation between lobes (arcsec) |
| `r:dipoleAngle` | Position angle of the dipole axis (degrees, N through E) |
| `r:dipoleNdata` | Number of pixels used in the dipole fit |
| `r:dipoleChi2` | Chi² of the dipole fit |

## Column naming conventions (LSST DPDD / Fink)

| Prefix | Meaning |
|--------|---------|
| `r:<col>` | Original LSST diaSource / diaObject field — the `r:` prefix is the table name, **not** the r spectral band |
| `f:<col>` | Fink-computed field (classifiers, crossmatch results) |
| `r:band` | Spectral filter ∈ {`u`, `g`, `r`, `i`, `z`, `y`} |
| Flux unit | **nJy** (nano-Jansky), AB system, ZP = 31.4 |

---

## LSST Deep Drilling Fields targeted

| DDF name | RA (deg) | Dec (deg) |
|----------|----------|-----------|
| COSMOS   | 150.1191 | +2.2058   |
| ELAIS-S1 |   9.4500 | −44.000   |
| ECDFS    |  53.1250 | −27.800   |
| EDFS-a   |  58.9000 | −49.315   |
| EDFS-b   |  63.6000 | −47.600   |
| EDFS     |  61.2400 | −48.423   |
| M49      | 187.4000 |  +8.000   |

---

## Directory structure

```
08_Dipoles/
├── 00_show_cone_slicing_ddf.ipynb                    ← 3×3 mini-cone geometry illustration
├── 01_fink_dipoles_per_ddf.ipynb                     ← dipole retrieval, basic conesearch
├── 01b_fink_dipoles_per_ddf.ipynb                    ← sliced cones + time slices
├── 01c_fink_dipoles_per_ddf.ipynb                    ← sliced cones, full time baseline  ★ main input
├── 02_fink_dipoles_uniformity.ipynb                  ← angular correlation, all DDFs
├── 02b_fink_dipoles_uniformity_in_one_DDF.ipynb      ← time-sliced correlation, one DDF
├── 03_dipoleobjectcorr.ipynb                         ← dipole concentration, conesearch variant
├── 03b_dipoleobjectcorr.ipynb                        ← dipole concentration, cached-parquet variant
├── 04_reloaddipoleobjectcorr.ipynb                   ← fully offline reload of 03b figures
├── 12a_downloadSelectedCutouts.ipynb                 ← download cutout triplets
├── 12b_viewSelectedCutouts.ipynb                     ← display cutout triplets
├── swagger.json                                      ← Fink LSST API OpenAPI spec (reference)
│
├── data_DIPOLES_01/                      ← parquets from notebook 01
├── data_DIPOLES_01b/                     ← parquets from notebook 01b
├── data_DIPOLES_01c/                     ← parquets from notebook 01c  ★ main input for 02–04
├── data_DIPOLES_02/                      ← correlation results from notebook 02
├── data_DIPOLES_02b/                     ← correlation results from notebook 02b
├── data_DIPOLES_03/                      ← dipole stats from notebook 03
├── data_DIPOLES_03b/                     ← dipole stats + per-object sources from notebook 03b
│   ├── presel_catalogue.{parquet,csv}
│   ├── dipole_stats_from_sources.{parquet,csv}
│   ├── all_src_presel.parquet
│   ├── topranked_objects_dipoles.{parquet,csv}
│   ├── dipole_angle_stability.csv
│   └── src_per_object/
│       └── {diaObjectId}_src.parquet     ← one file per pre-selected object
│
├── figs_DIPOLES_01/                      ← figures from notebook 01
├── figs_DIPOLES_01b/                     ← figures from notebook 01b
├── figs_DIPOLES_01c/                     ← figures from notebook 01c
├── figs_DIPOLES_02/                      ← figures from notebook 02
├── figs_DIPOLES_02b/                     ← figures from notebook 02b
├── figs_DIPOLES_03/                      ← figures from notebook 03
├── figs_DIPOLES_03b/                     ← figures from notebook 03b
├── figs_DIPOLES_04/                      ← figures from notebook 04  (offline reload)
├── figs_DIPOLES_12b/                     ← figures from notebook 12b
│
└── fullcutouts_{oid}/                    ← FITS cutout triplets per object (from 12a)
```

---

## Notebook dependency graph

```
01c_fink_dipoles_per_ddf
(sliced cones, full time)
        │
        ├──────────────────────────────────────────┐
        ▼                                          ▼
02_fink_dipoles_uniformity              03b_dipoleobjectcorr
(all DDFs, Landy–Szalay)               (per-object stats + sources)
        │                                          │
        ▼                                          ▼
02b_fink_dipoles_uniformity_in_one_DDF  04_reloaddipoleobjectcorr
(single DDF, time-sliced)              (fully offline reload, no API)

03_dipoleobjectcorr  ← independent (uses conesearch, not 01c parquets)

12a_downloadSelectedCutouts  ← uses diaObjectIds from 03b/04
        │
        ▼
12b_viewSelectedCutouts

00_show_cone_slicing_ddf  ← standalone utility, no data dependency
01_fink_dipoles_per_ddf   ← independent first-pass retrieval
01b_fink_dipoles_per_ddf  ← independent extended retrieval
```

---

## Figures produced (notebooks 03b / 04)

| Figure file | Content |
|-------------|---------|
| `nDiaSources_distribution_min{N}.{pdf,png}` | Histogram of nDiaSources (lin + log) |
| `dipole_stacked_per_object_min{N}.{pdf,png}` | Stacked dipole count per diaObject, top 50 |
| `dipole_distribution_lorenz_min{N}.{pdf,png}` | Dipole count histograms + Lorenz curve + Gini coefficient |
| `nsrc_vs_ndipoles_scatter_min{N}.{pdf,png}` | Scatter: n_src vs n_dipoles, coloured by DDF |
| `delta_mag_psf_ap_all_bands_min{N}.{pdf,png}` | Δm = m_psf − m_ap global histogram (dipole vs non-dipole) |
| `delta_mag_psf_ap_per_band_min{N}.{pdf,png}` | Same Δm histogram per spectral band |
| `lc_{diaObjectId}.{pdf,png}` | Three-panel light curve for each top object |
| `dipole_angle_histogram_top{N}.{pdf,png}` | Rose histogram of dipole angles (folded mod 180°) |
| `dipole_per_ddf_min{N}.{pdf,png}` | Per-DDF stacked dipole count per object |

---

## Dependencies

- `requests` — Fink API HTTP calls (notebooks 01–03b only; not needed for 04)
- `pandas`, `numpy`, `matplotlib`, `astropy`
- `treecorr` *(optional but recommended)* — fast two-point correlation in notebooks 02/02b; NumPy/KDTree fallback used if absent
- `scipy` — KDTree for the flat-sky correlation fallback
- `healpy` *(optional)* — HEALPix sky maps in exploration sections

## References

- Landy & Szalay 1993 — two-point angular correlation estimator: https://doi.org/10.1086/172900
- Rubin DPDD (Data Products Definition Document): https://ls.st/dpdd
- Fink portal: https://lsst.fink-portal.org | API: https://api.lsst.fink-portal.org
- Alard & Lutz 1998 — image subtraction and PSF matching (context for dipole origin)

---

*Author: Sylvie Dagoret-Campagne — IJCLab / IN2P3 / CNRS — Université Paris-Saclay*
