# 07_TNS_SN — Supernovae Light Curves and SALT2 Fitting

This directory contains notebooks dedicated to the retrieval, visualisation, and photometric
analysis of supernova candidates from the **Fink LSST alert broker**, using the SALT2 light-curve
model and `sncosmo` for fitting.  The pipeline covers two complementary samples — TNS-confirmed
supernovae and `sn_near_galaxy_candidate` alerts — and includes cutout inspection tools to
diagnose difference-image artefacts.

---

## Notebook overview

### Light-curve retrieval and exploration

| Notebook | Description |
|----------|-------------|
| `01_fink_tns_sn_lightcurves.ipynb` | Downloads alerts tagged `fink_in_tns_lsst` from the Fink API. Builds a catalog of TNS-confirmed or candidate supernovae (with TNS type, spectroscopic redshift `f:xm_tns_redshift`, and host-galaxy photo-z). Plots multi-band flux and AB-magnitude light curves per object. Saves the catalog and per-object light-curve parquets to `data_NB07_01_TNS_SN/`. |
| `02_fink_sn_near_galaxy_candidate_sn_lightcurves.ipynb` | Same pipeline as notebook 01, but for the `sn_near_galaxy_candidate` tag. Objects are not necessarily in TNS; the redshift prior comes from `f:xm_legacydr8_zphot` (Legacy Survey DR8) or `f:xm_mangrove_lum_dist`. Saves to `data_NB07_02_SN_NEAR/`. |

### ELAsTiCC2 SALT2 development notebook

| Notebook | Description |
|----------|-------------|
| `02b_elasticc2_fitsalt2andredshift_lightcurves.ipynb` | Prototype/validation notebook on DESC ELAsTiCC2 simulated light curves. Fits **five SALT2 parameters simultaneously** `{z, t0, x0, x1, c}` using a two-pass strategy: (1) coarse redshift grid scan with 4-parameter fit, (2) refined free-z optimisation initialised at the grid minimum. Truth redshift (`ZCMB`) is used only for post-fit validation. Produces `z_fit ± σ_z` vs `z_true` diagnostic plots with Δz residuals. |

### SALT2 fitting — TNS sample

| Notebook | Description |
|----------|-------------|
| `03_fink_tns_sn_fitSNIa_salt2_lightcurves.ipynb` | Reads the TNS catalog and light curves from notebook 01. Selects SNIa with a spectroscopic redshift from TNS. Fits SALT2 with **redshift fixed** to the TNS spec-z `(t0, x0, x1, c)`. Derives the distance modulus via the Tripp formula (α = 0.14, β = 3.14, M_B = −19.3). Produces a **Hubble diagram** μ(z) compared to ΛCDM (Ω_m = 0.3, Ω_Λ = 0.7, H0 = 70 km/s/Mpc) and to the empty-universe reference. Saves results to `data_NB07_03_FINK_TNS_SN_FIT_SALT2/`. |
| `04_fink_tns_sn_fitSNIa_salt2_withredshift_lightcurves.ipynb` | Same TNS SNIa sample as notebook 03, but fits SALT2 with **redshift as a free parameter** using the same two-pass strategy as `02b`. The TNS spec-z is used only for post-fit validation (photometric-z accuracy). Produces both a Hubble diagram and `z_fit ± σ_z` vs `z_TNS` diagnostic plots. Saves results to `data_NB07_04_FINK_TNS_SN_FIT_SALT2_FREEZ/`. |

### SALT2 fitting — `sn_near_galaxy_candidate` sample

| Notebook | Description |
|----------|-------------|
| `05_fink_sn_near_galaxy_candidate_sn_fitSNIa_salt2_lightcurves.ipynb` | Selects `sn_near_galaxy_candidate` alerts that have a photometric redshift from the near host galaxy (`f:xm_legacydr8_zphot` preferred, `f:xm_tns_redshift` as fallback). Fits SALT2 with **photo-z held fixed**. Produces a Hubble diagram μ(z_phot) colour-coded by χ²/dof, with marker shape encoding galaxy type. Saves results to `data_NB07_05_FINK_SN_NEARGAL_FIT_SALT2/`. |

### Cutout download and inspection

| Notebook | Description |
|----------|-------------|
| `12a_downloadAllCutouts.ipynb` | Downloads and caches on disk the **Science / Template / Difference** cutout stamps and forced photometry for all diaSources of Gaia-stable diaObjects (identified in notebook 09b of the `04_calib` pipeline). Calls `fink_download_full_cutouts.py` as a module. Output is stored in `fullcutouts_{diaObjectId}/` directories containing `.npy` arrays and a `manifest.csv/parquet`. |
| `12b_viewCutouts.ipynb` | Visualises the cutout triplet for a user-selected `diaObjectId`. Layout: 2×3 grid per diaSource (info panel, Science, Template, light curve, DIA Difference, Science−Template). Primary goal: demonstrate that **dipole residuals** in the PSF-subtracted difference image drive spurious Rubin AP alerts on intrinsically stable Gaia stars. |
| `12c_checkTemplateCutouts.ipynb` | Checks whether the **template stamps** sent by Rubin via the Fink alert stream are identical across all diaSources for a given `diaObjectId` and band. Computes per-visit residuals `ΔT_k = T_k − T_ref` and displays them on a diverging colormap. Investigates PSF-convolution, WCS resampling, and possible template epoch changes as sources of template variability. |

### Support script

| File | Description |
|------|-------------|
| `fink_download_full_cutouts.py` | Standalone module imported by `12a`. Handles Fink API queries for cutout stamps (Science, Template, Difference) and forced photometry, with on-disk caching and manifest bookkeeping. |

---

## Column naming conventions (LSST DPDD / Fink)

| Prefix | Meaning |
|--------|---------|
| `r:<col>` | Original LSST diaSource / diaObject field — the `r:` prefix is the table name, **not** the r spectral band |
| `f:<col>` | Fink-computed field (classifiers, cross-match results) |
| `r:band` | Spectral band ∈ {`u`, `g`, `r`, `i`, `z`, `y`} |
| Flux unit | **nJy** (nano-Jansky), AB system, ZP = 31.4 |

Key redshift columns:

| Column | Source |
|--------|--------|
| `f:xm_tns_redshift` | Spectroscopic redshift from TNS (most reliable; may be NaN) |
| `f:xm_legacydr8_zphot` | Photometric redshift from Legacy Survey DR8 (host galaxy) |
| `f:xm_mangrove_lum_dist` | Luminosity distance from the MANGROVE galaxy catalogue |

---

## Directory structure

```
07_TNS_SN/
├── 01_fink_tns_sn_lightcurves.ipynb
├── 02_fink_sn_near_galaxy_candidate_sn_lightcurves.ipynb
├── 02b_elasticc2_fitsalt2andredshift_lightcurves.ipynb
├── 03_fink_tns_sn_fitSNIa_salt2_lightcurves.ipynb
├── 04_fink_tns_sn_fitSNIa_salt2_withredshift_lightcurves.ipynb
├── 05_fink_sn_near_galaxy_candidate_sn_fitSNIa_salt2_lightcurves.ipynb
├── 12a_downloadAllCutouts.ipynb
├── 12b_viewCutouts.ipynb
├── 12c_checkTemplateCutouts.ipynb
├── fink_download_full_cutouts.py
├── snIa_TNS.csv                          ← reference SNIa list from TNS
├── snIIa_TNS.csv                         ← reference SNII list from TNS
├── data_NB07_01_TNS_SN/                  ← catalog + LCs for tag fink_in_tns_lsst
├── data_NB07_02_SN_NEAR/                 ← catalog + LCs for sn_near_galaxy_candidate
├── data_NB07_03_FINK_TNS_SN_FIT_SALT2/  ← SALT2 fit results (z fixed, TNS sample)
├── data_NB07_04_FINK_TNS_SN_FIT_SALT2_FREEZ/  ← SALT2 fit results (z free, TNS sample)
├── data_NB07_05_FINK_SN_NEARGAL_FIT_SALT2/    ← SALT2 fit results (near-galaxy sample)
├── figs_NB07_01_TNS_SN/                  ← figures from notebook 01
├── figs_NB07_02_SN_NEAR/                 ← figures from notebook 02
├── figs_NB07_03_FINK_TNS_SN_FIT_SALT2/  ← figures from notebook 03
├── figs_NB07_04_FINK_TNS_SN_FIT_SALT2_FREEZ/  ← figures from notebook 04
├── figs_NB07_05_FINK_SN_NEARGAL_FIT_SALT2/    ← figures from notebook 05
├── figs_FINK_BLOCK_LC_12b/               ← cutout view figures (notebook 12b)
├── figs_FINK_BLOCK_LC_12c/               ← template consistency figures (notebook 12c)
└── fullcutouts_{diaObjectId}/            ← one directory per object (notebooks 12a/12b/12c)
```

---

## Dependencies

- `sncosmo` — SALT2 light-curve model and fitting
- `astropy` — Table I/O, units, coordinates
- `pandas`, `numpy`, `matplotlib`
- `requests` — Fink API HTTP calls
- `healpy` — HEALPix sky maps (catalog exploration)

## References

- Guy et al. 2007 — SALT2: https://doi.org/10.1051/0004-6361:20066930
- Betoule et al. 2014 — JLA Hubble diagram (Tripp parameters)
- Dey et al. 2019 — Legacy Survey DR8
- Fink portal: https://lsst.fink-portal.org | API: https://api.lsst.fink-portal.org
- Rubin DPDD: https://ls.st/dpdd

---

*Author: Sylvie Dagoret-Campagne — IJCLab / IN2P3 / CNRS — Université Paris-Saclay*
