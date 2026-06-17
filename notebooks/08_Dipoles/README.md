# 08_Dipoles — Dipole Artefact Analysis in Rubin LSST DIA Alerts

This directory contains notebooks dedicated to the characterisation of **dipole artefacts**
in Rubin LSST Difference Image Analysis (DIA) alerts retrieved via the Fink broker.

Dipoles arise in difference images when a PSF-subtracted source is slightly mis-registered
with respect to its template, leaving a positive-lobe / negative-lobe residual pattern.
Their spatial distribution, temporal evolution, per-object concentration, angular
orientation, and relationship to **Differential Chromatic Refraction (DCR)** are studied
across the LSST **Deep Drilling Fields** (DDFs).

---

## Notebook overview

### Geometry utilities

| Notebook | Description |
|----------|-------------|
| `00_show_cone_slicing_ddf.ipynb` | Draws the 3×3 mini-cone tiling strategy used to work around the Fink API conesearch size limit. No data download; pure geometry illustration. |
| `0001_SphereForParalacticAngle.ipynb` | Spherical-trigonometry derivation and numerical validation of the parallactic angle formula used throughout the dipole analysis. |

### Data retrieval — DDF conesearch

| Notebook | Description |
|----------|-------------|
| `01_fink_dipoles_per_ddf.ipynb` | First-pass dipole retrieval via `/api/v1/conesearch` on each DDF. Produces spatial sky maps with dipole orientation arrows and temporal evolution plots. Saves parquets to `data_DIPOLES_01/`. |
| `01b_fink_dipoles_per_ddf.ipynb` | Extended version using the **sliced-cone + time-slice** strategy (3×3 spatial sub-cones, configurable time slices). Adds direction-of-dipole-axis plots. Saves to `data_DIPOLES_01b/`. |
| `01c_fink_dipoles_per_ddf.ipynb` | Same sliced-cone strategy as `01b` but **without time slicing** — full temporal baseline per sub-cone. Produces the most complete per-DDF parquet files, used as primary input for all downstream notebooks. Saves to `data_DIPOLES_01c/`. ★ **main input** |
| `01d_fink_reload_dipoles_per_ddf.ipynb` | **Fully offline reload** of `01c`. Reads existing parquets from `data_DIPOLES_01c/` and reproduces all figures from `01c` without any Fink API call. Figures go to `figs_DIPOLES_01d/`. |

### Spatial uniformity and angular correlation analysis

| Notebook | Description |
|----------|-------------|
| `02_fink_dipoles_uniformity.ipynb` | Tests **angular uniformity** across all DDFs using the two-point angular correlation function $w(\theta)$ (Landy–Szalay estimator): auto-correlation of all alerts, auto-correlation of `isDipole=True` alerts, cross-correlation of non-dipoles × dipoles. Uses **TreeCorr** when available, with a NumPy/KDTree flat-sky fallback. Loads from `data_DIPOLES_01c/`. Saves to `figs_DIPOLES_02/`. |
| `02b_fink_dipoles_uniformity_in_one_DDF.ipynb` | Same Landy–Szalay analysis restricted to a **single user-selected DDF**, split into configurable **time slices**. Investigates whether dipole clustering evolves with time (e.g. as template quality improves). Loads from `data_DIPOLES_01c/`. Saves to `figs_DIPOLES_02b/`. |

### Per-object dipole concentration analysis

| Notebook | Description |
|----------|-------------|
| `03_dipoleobjectcorr.ipynb` | **Dipole concentration per diaObject** — conesearch variant. Retrieves alerts via `/api/v1/conesearch`, deduplicates by `diaObjectId`, pre-selects objects with `nDiaSources >= NDIASOURCES_MIN`, downloads full diaSources via `/api/v1/sources`. Computes per-object dipole counts and fractions, Lorenz curve + Gini coefficient, psfFlux−apFlux diagnostics, light curves, and angular stability of dipole direction. Saves to `data_DIPOLES_03/`. |
| `03b_dipoleobjectcorr.ipynb` | **Dipole concentration per diaObject** — cached-parquet variant of `03`. Conesearch step replaced by reading `01c` parquets. Adds Gini coefficient annotation and per-band psfFlux−apFlux histograms. Writes per-object source parquets and statistics to `data_DIPOLES_03b/`. ★ **produces the top-ranked object list used by 12a** |
| `04_reloaddipoleobjectcorr.ipynb` | **Fully offline reload** of `03b`. Reads all files from `data_DIPOLES_03b/` and reproduces every figure without any API call. Figures go to `figs_DIPOLES_04/`. |

### Parallactic angle and DCR orientation analysis

| Notebook | Description |
|----------|-------------|
| `05_dipole_parallacticcorr.ipynb` | Correlates the **dipole orientation** (`r:dipoleAngle`) with the **parallactic angle** computed from observing metadata (hour angle, declination, observatory latitude). First full exploration: scatter plots, profile histograms, and rose diagrams of dipole PA vs. parallactic angle per DDF and per band. Loads from `data_DIPOLES_01c/`. Saves to `figs_DIPOLES_05/`. |
| `05b_dipole_parallacticcorr.ipynb` | Refined version of `05` with extended diagnostics: profile histograms with error bars, rose diagrams for individual DDFs, and scatter plots of `(dipole_PA − parallactic_angle)` residuals as a function of hour angle. Confirms that `r:dipoleAngle` is directly the astronomical PA (North toward East) — **no 90° offset required**. Saves to `figs_DIPOLES_05b/`. |
| `06_checkdirections_astroplan.ipynb` | **Observational geometry verification** using `astroplan`. Recomputes parallactic angle and alt/az trajectories for each DDF from visit timestamps in the alert stream and compares with `05b` results. Validates that the DCR direction predicted by theory matches the observed dipole orientation. Saves to `figs_DIPOLES_06/`. |

### DCR-predicted dipole separation

| Notebook | Description |
|----------|-------------|
| `08_dipole_separation.ipynb` | Characterises the **dipole length distribution** per DDF and per band. Produces 2-D density maps of dipole length vs. tan(zenith angle), 1-D distributions, and comparisons with the DCR-predicted shift $\Delta\theta_{\rm DCR}(b) = \sigma_n(b)\,\tan z$ derived in `99_tools/07_DDF_DCR.ipynb`. Includes weighted least-squares fits of dipole length vs. tan(z) per band. Saves to `figs_DIPOLES_08/`. |
| `08b_dipole_separation_selectdiaobj.ipynb` | Same analysis as `08` restricted to a **selected subset of diaObjects** from COSMOS (filtered from `data_DIPOLES_03b/`). Performs per-diaObject temporal analysis: evolution of dipole length and angle vs. tan(z) over visits, weighted least-squares fits per object and per band. Saves to `figs_DIPOLES_08b/`. |

### Cutout inspection — raw format (`.npy`)

| Notebook | Description |
|----------|-------------|
| `12a_downloadSelectedCutouts.ipynb` | Downloads science / template / difference image triplets (stamp cutouts) from the Fink `/api/v1/cutouts` endpoint for a user-defined list of diaObjectIds. Stores cutout arrays as `.npy` files in per-object subdirectories `fullcutouts_{oid}/`. |
| `12b_viewSelectedCutouts.ipynb` | Displays the downloaded `.npy` cutout triplets as multi-panel figures for visual inspection. Saves figures to `figs_DIPOLES_12b/` and `figs_FINK_DIPOLES_12b/`. |
| `12c_viewSelectedCutouts_splitbypages.ipynb` | Same as `12b` but renders cutouts **split by page** (configurable number of objects per page) for easier navigation of large object samples. Saves figures to `figs_DIPOLES_12c/`. |

### Cutout inspection — FITS format (WCS-aware) ★ new

| Notebook | Description |
|----------|-------------|
| `12_fetch_onecutouts.ipynb` | Fetches the Science / Template / Difference cutout **triplet for a single diaSource** from Fink and saves them as FITS. Injects time and observatory keywords (`MJD-OBS`, `TIMESYS`, `DATE-OBS`, `OBS-LAT`, `OBS-LONG`, `OBS-ELEV`) into the headers before saving. Displays the Difference image with WCS axes and four direction overlays: **N** (red), **E** (blue), **Z** (yellow, = zenith along parallactic angle η), **Dip** (cyan ↔, = `r:dipoleAngle` PA). Colourmap: `RdBu_r` + `TwoSlopeNorm(vcenter=0)` for the Difference; shared ZScale for Science / Template. |
| `12a_downloadSelectedCutoutsFits.ipynb` | Downloads and caches ALL cutout triplets for the **top-ranked dipole objects** from `03b`, saving each stamp as a **self-describing FITS file** (WCS + diaSource metadata injected into the PRIMARY header). Also downloads forced photometry. Delegates to `fink_download_full_cutouts_fits.py`. Output: `fullcutouts_fits_{oid}/manifest.{csv,parquet}`, `manifest_fp.{csv,parquet}`, `cutouts/{srcId}_{band}_{kind}.fits`. |
| `12b_viewSelectedCutoutsFits.ipynb` | Displays the FITS cutout triplets produced by `12a_downloadSelectedCutoutsFits`. Renders a **2 × 3 grid** per diaSource (info panel / Science / Template / light curve / DIA Difference / Sci−Tpl). WCS direction vectors derived from the PC matrix via `wcs.wcs.get_pc()`. Parallactic angle computed with the Meeus formula; `.to_value(u.rad)` idiom used to avoid astropy Quantity propagation issues in `arctan2`. Figures saved as PDF + PNG to `figs_DIPOLES_12b_fits/`. |

---

## Python scripts

| Script | Description |
|--------|-------------|
| `fink_download_full_cutouts.py` | Batch-download FITS cutout triplets + forced photometry for a list of diaObjectIds (`.npy` format). Backend used by `12a_downloadSelectedCutouts`. |
| `fink_download_full_cutouts_fits.py` | Same, but saves cutouts as **FITS files** with full WCS and diaSource metadata injected into the PRIMARY header. Backend imported by `12a_downloadSelectedCutoutsFits`. Includes `MJD-OBS`, `TIMESYS`, `DATE-OBS`, `OBS-LAT/LONG/ELEV` keywords. |
| `fink_download_full_cutouts_fits_complicated.py` | Development / experimental version of the FITS download script — kept as a reference for more complex header injection strategies. Not used by the main notebooks. |

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
| `r:dipoleAngle` | Dipole axis position angle measured from **North toward East** (standard astronomical PA convention, degrees). Used directly — no offset transformation required. |
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

## Angle convention note

`r:dipoleAngle` is the **position angle of the dipole axis measured from North toward East**
(standard astronomical PA convention, in degrees), as confirmed by the alignment with the
parallactic angle in notebooks `05b` and `06`.

It is used **directly** — no offset transformation is required:

```python
dipole_PA_deg = r_dipoleAngle   # already North-toward-East PA
```

The dipole axis is bilateral (it has no preferred direction), so it is drawn as a
double-headed arrow (↔) symmetric about the image centre.

> **Note:** earlier versions of notebooks `05` and some comments in the `01` series
> applied a `(90 − angle) mod 360` conversion. This was corrected in `05b` after
> comparison with `astroplan`-computed parallactic angles confirmed that `r:dipoleAngle`
> is already the astronomical PA.

---

## Key scientific result

The **dipole axis (`r:dipoleAngle`) is aligned with the zenith direction** in the
observation plane, confirming that dipole artefacts in Rubin/LSST DIA images are
caused by **Differential Chromatic Refraction (DCR)**:

$$\Delta\theta_{\rm DCR}(b) = \sigma_n(b) \cdot \tan z$$

where $\sigma_n(b)$ is the photon-count-weighted refractive-index dispersion across
band $b$ (from Ciddor formula + LSST throughputs, see `99_tools/07_DDF_DCR.ipynb`)
and $z$ is the zenith angle. The colour mismatch between the science and template
images shifts the PSF centroid along the parallactic angle direction, producing a
positive/negative dipole in the difference image oriented along the Zenith arrow
overlay. `r:dipoleAngle` can therefore be used directly (without any 90° offset)
as a proxy for the parallactic angle.

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

Observatory: Cerro Pachón, `lat = −30.2447°`, `lon = −70.7494°`

---

## Directory structure

```
08_Dipoles/
├── 00_show_cone_slicing_ddf.ipynb                    ← 3×3 mini-cone geometry illustration
├── 0001_SphereForParalacticAngle.ipynb               ← parallactic angle derivation
├── 01_fink_dipoles_per_ddf.ipynb                     ← basic conesearch retrieval
├── 01b_fink_dipoles_per_ddf.ipynb                    ← sliced cones + time slices
├── 01c_fink_dipoles_per_ddf.ipynb                    ← sliced cones, full time  ★ main input
├── 01d_fink_reload_dipoles_per_ddf.ipynb             ← offline reload of 01c
├── 02_fink_dipoles_uniformity.ipynb                  ← angular correlation, all DDFs
├── 02b_fink_dipoles_uniformity_in_one_DDF.ipynb      ← time-sliced correlation, one DDF
├── 03_dipoleobjectcorr.ipynb                         ← dipole concentration, conesearch variant
├── 03b_dipoleobjectcorr.ipynb                        ← dipole concentration, cached-parquet ★
├── 04_reloaddipoleobjectcorr.ipynb                   ← offline reload of 03b
├── 05_dipole_parallacticcorr.ipynb                   ← dipole PA vs. parallactic angle (first pass)
├── 05b_dipole_parallacticcorr.ipynb                  ← refined, confirms direct PA convention
├── 06_checkdirections_astroplan.ipynb                ← geometry verification with astroplan
├── 08_dipole_separation.ipynb                        ← dipole length vs. tan(z), all DDFs
├── 08b_dipole_separation_selectdiaobj.ipynb          ← dipole length vs. tan(z), selected objects
│
├── 12_fetch_onecutouts.ipynb                         ← FITS cutout for one diaSource + WCS overlays ★ new
├── 12a_downloadSelectedCutouts.ipynb                 ← batch download cutouts as .npy
├── 12a_downloadSelectedCutoutsFits.ipynb             ← batch download cutouts as FITS ★ new
├── 12b_viewSelectedCutouts.ipynb                     ← display .npy cutout triplets
├── 12b_viewSelectedCutoutsFits.ipynb                 ← display FITS cutouts + WCS N/E/Z/Dip overlays ★ new
├── 12b_viewSelectedCutoutsFits_backup.ipynb          ← backup of 12b_viewSelectedCutoutsFits
├── 12c_viewSelectedCutouts_splitbypages.ipynb        ← display .npy cutouts, split by page
│
├── fink_download_full_cutouts.py                     ← batch .npy cutout download script
├── fink_download_full_cutouts_fits.py                ← batch FITS cutout download script ★ new
├── fink_download_full_cutouts_fits_complicated.py    ← experimental FITS download variant
├── swagger.json                                      ← Fink LSST API OpenAPI spec (reference)
│
├── data_DIPOLES_01/                      ← parquets from notebook 01
├── data_DIPOLES_01b/                     ← parquets from notebook 01b
├── data_DIPOLES_01c/                     ← parquets from notebook 01c  ★ main input
├── data_DIPOLES_02/                      ← correlation results from notebook 02
├── data_DIPOLES_02b/                     ← correlation results from notebook 02b
├── data_DIPOLES_03/                      ← dipole stats from notebook 03
├── data_DIPOLES_03b/                     ← dipole stats + per-object sources from notebook 03b
│   ├── presel_catalogue.{parquet,csv}
│   ├── dipole_stats_from_sources.{parquet,csv}
│   ├── all_src_presel.parquet
│   ├── topranked_objects_dipoles.{parquet,csv}    ← top-ranked objects → input for 12a FITS
│   ├── dipole_angle_stability.csv
│   └── src_per_object/
│       └── {diaObjectId}_src.parquet
│
├── figs_DIPOLES_01/                      ← figures from notebook 01
├── figs_DIPOLES_01b/                     ← figures from notebook 01b
├── figs_DIPOLES_01c/                     ← figures from notebook 01c
├── figs_DIPOLES_01d/                     ← figures from notebook 01d (offline reload)
├── figs_DIPOLES_02/                      ← figures from notebook 02
├── figs_DIPOLES_02b/                     ← figures from notebook 02b
├── figs_DIPOLES_03/                      ← figures from notebook 03
├── figs_DIPOLES_03b/                     ← figures from notebook 03b
├── figs_DIPOLES_04/                      ← figures from notebook 04 (offline reload)
├── figs_DIPOLES_05/                      ← figures from notebook 05
├── figs_DIPOLES_05b/                     ← figures from notebook 05b
├── figs_DIPOLES_06/                      ← figures from notebook 06
├── figs_DIPOLES_08/                      ← figures from notebook 08
├── figs_DIPOLES_08b/                     ← figures from notebook 08b
├── figs_DIPOLES_12b/                     ← figures from notebook 12b (.npy format)
├── figs_DIPOLES_12b_fits/                ← figures from notebook 12b FITS (PDF+PNG) ★ new
├── figs_DIPOLES_12c/                     ← figures from notebook 12c
├── figs_FINK_DIPOLES_12b/                ← additional cutout figures (Fink stamp format)
│
├── fullcutouts_{oid}/                    ← .npy cutout triplets per object (from 12a)
├── fullcutouts_fits_{oid}/               ← FITS cutout triplets per object (from 12a FITS) ★ new
│   ├── manifest.{csv,parquet}
│   ├── manifest_fp.{csv,parquet}
│   └── cutouts/
│       └── {diaSourceId}_{band}_{Science|Template|Difference}.fits
│
└── *.fits                                ← example single-diaSource cutout triplets
```

---

## Notebook dependency graph

```
01c_fink_dipoles_per_ddf  (★ main input)
        │
        ├──────────────────────────────────────────────────┐
        │                                                  │
        ▼                                                  ▼
01d (offline reload)                        03b_dipoleobjectcorr ★
                                                    │
        ┌───────────────────┐                       ├────────────────────┐
        ▼                   ▼                       ▼                    ▼
02_uniformity       02b_uniformity     04_reloaddipoleobjectcorr   08b_separation
(all DDFs)          (one DDF, sliced)   (offline reload)           (selected objects)
                                               │
                                    12a_downloadSelectedCutoutsFits ★ new
                                               │
                                    12b_viewSelectedCutoutsFits ★ new

05_dipole_parallacticcorr     ← loads from data_DIPOLES_01c/
        │
        ▼
05b_dipole_parallacticcorr    (refined, direct PA convention confirmed)
        │
        ▼
06_checkdirections_astroplan  (astroplan geometry verification)

08_dipole_separation          ← loads from data_DIPOLES_01c/

03_dipoleobjectcorr           ← independent (conesearch variant, no 01c dependency)

12_fetch_onecutouts           ← standalone: one object, interactive FITS + WCS ★ new

12a_downloadSelectedCutouts   ← diaObjectIds from 03b/04 (.npy format)
        ├──► 12b_viewSelectedCutouts
        └──► 12c_viewSelectedCutouts_splitbypages

00_show_cone_slicing_ddf      ← standalone utility
0001_SphereForParalacticAngle ← standalone derivation
01_fink_dipoles_per_ddf       ← independent first-pass retrieval
01b_fink_dipoles_per_ddf      ← independent extended retrieval
```

---

## Dependencies

- `requests` — Fink API HTTP calls (notebooks 01–03b, 12, 12a only)
- `pandas`, `numpy`, `matplotlib`, `astropy`
- `astroplan` — observational geometry in notebook `06`
- `treecorr` *(optional but recommended)* — fast two-point correlation in notebooks 02/02b; NumPy/KDTree flat-sky fallback used if absent
- `scipy` — KDTree for flat-sky correlation fallback, weighted least-squares fits
- `healpy` *(optional)* — HEALPix sky maps in exploration sections

Kernel: `conda_py313`

---

## References

- Landy & Szalay 1993 — two-point angular correlation estimator: https://doi.org/10.1086/172900
- Ciddor 1996 — refractive index of air: https://doi.org/10.1364/AO.35.001566
- Rubin DPDD (Data Products Definition Document): https://ls.st/dpdd
- Fink portal: https://lsst.fink-portal.org | API: https://api.lsst.fink-portal.org
- Alard & Lutz 1998 — image subtraction and PSF matching (context for dipole origin)

---

*Author: Sylvie Dagoret-Campagne — IJCLab / IN2P3 / CNRS — Université Paris-Saclay*
