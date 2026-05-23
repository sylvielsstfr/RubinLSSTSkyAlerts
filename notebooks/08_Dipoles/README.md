# 08_Dipoles — Dipole Artefact Analysis in Rubin LSST DIA Alerts

This directory contains notebooks dedicated to the characterisation of **dipole artefacts**
in Rubin LSST Difference Image Analysis (DIA) alerts retrieved via the Fink broker.

Dipoles arise in difference images when a PSF-subtracted source is slightly mis-registered
with respect to its template, leaving a positive-lobe / negative-lobe residual pattern.
Their spatial distribution, temporal evolution, and angular clustering are studied across
the LSST **Deep Drilling Fields** (DDFs).

---

## Notebook overview

### Data retrieval — DDF conesearch

| Notebook | Description |
|----------|-------------|
| `00_show_cone_slicing_ddf.ipynb` | Utility / visualisation notebook. Draws the 3×3 mini-cone tiling strategy used to work around the Fink API conesearch size limit: the main DDF cone is covered by 9 overlapping sub-cones. No data download; pure geometry illustration. |
| `01_fink_dipoles_per_ddf.ipynb` | First-pass dipole retrieval. Performs a conesearch (`/api/v1/conesearch`) on each DDF with all dipole columns (`isDipole`, `dipoleFluxDiff`, `dipoleLength`, `dipoleAngle`, `dipoleChi2`, …) plus flux, observing metadata, and crossmatch columns. Produces spatial sky maps with dipole orientation arrows and temporal evolution plots of the dipole fraction per DDF and per band. Saves one parquet file per DDF to `data_DIPOLES_01/`. |
| `01b_fink_dipoles_per_ddf.ipynb` | Extended version of notebook 01 using the **sliced-cone + time-slice** strategy: the DDF cone is split into 3×3 spatial sub-cones and the time axis is divided into configurable slices to avoid API payload limits. Adds direction-of-dipole-axis plots per DDF. Saves to `data_DIPOLES_01b/`. |
| `01c_fink_dipoles_per_ddf.ipynb` | Same sliced-cone strategy as 01b but **without time slicing** — the full temporal baseline is retrieved in one pass per sub-cone. This produces the most complete per-DDF parquet files used as input for the correlation notebooks (02, 02b). Saves to `data_DIPOLES_01c/`. |

### Spatial uniformity and angular correlation analysis

| Notebook | Description |
|----------|-------------|
| `02_fink_dipoles_uniformity.ipynb` | Tests the **angular uniformity** of DIA alert positions across all DDFs using the two-point angular correlation function $w(\theta)$ (Landy–Szalay estimator). Computes three correlation types per DDF: (1) auto-correlation of all alerts, (2) auto-correlation of `isDipole=True` alerts, (3) cross-correlation of non-dipoles × dipoles. Uses **TreeCorr** when available, with a NumPy/KDTree flat-sky fallback. Loads data from `data_DIPOLES_01c/` — no Fink API calls. Saves figures to `figs_DIPOLES_02/`. |
| `02b_fink_dipoles_uniformity_in_one_DDF.ipynb` | Same Landy–Szalay analysis as notebook 02 but restricted to a **single user-selected DDF** and split into configurable **time slices**. Each slice is rendered as one coloured curve in a summary figure, allowing investigation of whether dipole clustering evolves with time (e.g. as template quality improves). Loads from `data_DIPOLES_01c/`. Saves figures to `figs_DIPOLES_02b/`. |

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

The five main DDFs used across these notebooks:

| DDF name | RA (deg) | Dec (deg) |
|----------|----------|-----------|
| COSMOS | 150.1191 | +2.2058 |
| ECDFS | 53.1 | −28.1 |
| EDFS | 58.9 | −49.3 |
| ELAIS-S1 | 9.45 | −44.0 |
| XMM-LSS | 35.7 | −4.75 |

---

## Directory structure

```
08_Dipoles/
├── 00_show_cone_slicing_ddf.ipynb        ← 3×3 mini-cone geometry illustration
├── 01_fink_dipoles_per_ddf.ipynb         ← dipole retrieval, basic conesearch
├── 01b_fink_dipoles_per_ddf.ipynb        ← sliced cones + time slices
├── 01c_fink_dipoles_per_ddf.ipynb        ← sliced cones, full time baseline
├── 02_fink_dipoles_uniformity.ipynb      ← angular correlation, all DDFs
├── 02b_fink_dipoles_uniformity_in_one_DDF.ipynb  ← time-sliced correlation, one DDF
├── swagger.json                          ← Fink LSST API OpenAPI spec (reference)
├── data_DIPOLES_01/                      ← parquets from notebook 01
├── data_DIPOLES_01b/                     ← parquets from notebook 01b
├── data_DIPOLES_01c/                     ← parquets from notebook 01c (main input for 02/02b)
├── data_DIPOLES_02/                      ← correlation results from notebook 02
├── data_DIPOLES_02b/                     ← correlation results from notebook 02b
├── figs_DIPOLES_01/                      ← figures from notebook 01
├── figs_DIPOLES_01b/                     ← figures from notebook 01b
├── figs_DIPOLES_01c/                     ← figures from notebook 01c
├── figs_DIPOLES_02/                      ← figures from notebook 02
└── figs_DIPOLES_02b/                     ← figures from notebook 02b
```

---

## Notebook dependency graph

```
01c_fink_dipoles_per_ddf  ──────────────────────┐
(sliced cones, full time)                       │
                                                ▼
                                  02_fink_dipoles_uniformity
                                  (all DDFs, Landy–Szalay)

                                                │
                                                ▼
                            02b_fink_dipoles_uniformity_in_one_DDF
                            (single DDF, time-sliced correlation)

00_show_cone_slicing_ddf   ← standalone utility, no data dependency
01_fink_dipoles_per_ddf    ← independent first-pass retrieval
01b_fink_dipoles_per_ddf   ← independent extended retrieval
```

---

## Dependencies

- `requests` — Fink API HTTP calls
- `pandas`, `numpy`, `matplotlib`, `astropy`
- `treecorr` *(optional but recommended)* — fast two-point correlation; NumPy/KDTree fallback used if absent
- `scipy` — KDTree for the flat-sky correlation fallback
- `healpy` *(optional)* — HEALPix sky maps in exploration sections

## References

- Landy & Szalay 1993 — two-point angular correlation estimator: https://doi.org/10.1086/172900
- Rubin DPDD (Data Products Definition Document): https://ls.st/dpdd
- Fink portal: https://lsst.fink-portal.org | API: https://api.lsst.fink-portal.org
- Alard & Lutz 1998 — image subtraction and PSF matching (context for dipole origin)

---

*Author: Sylvie Dagoret-Campagne — IJCLab / IN2P3 / CNRS — Université Paris-Saclay*
