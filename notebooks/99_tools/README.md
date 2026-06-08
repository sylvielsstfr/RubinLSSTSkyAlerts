# 99_tools — Utility Notebooks and Scripts

This directory contains standalone utility notebooks and scripts developed as
auxiliary tools for the Rubin/LSST sky-alert analysis pipeline. They cover
observational geometry, atmospheric chromatic refraction, and visualisation
helpers used across the `07_TNS_SN/` and `08_Dipoles/` analysis directories.

---

## Contents

### Python scripts

| File | Description |
|------|-------------|
| `01_lsst_meridian_visibility_claude.py` | Compute and plot LSST meridian visibility windows for Deep Drilling Fields as a function of sidereal time. Generates `lsst_meridian_visibility.pdf/.png`. |
| `01_VisibilitySideralTime_gemini.py` | Alternative sidereal-time visibility computation (Gemini-assisted prototype). |
| `06_plot_parallactic_angle.py` | Standalone script to plot parallactic angle sweeps for DDF fields. |

### Jupyter notebooks

| Notebook | Description |
|----------|-------------|
| `02_fitparamchi2.ipynb` | Generic χ² parameter fitting utilities used for light-curve and dipole-length fits. |
| `03_FicherEllipse.ipynb` | Ellipse fitting helper (Ficher/Fitzgibbon method) for 2-D distribution characterisation. |
| `04_DDF_astroplan.ipynb` | Observational planning for Rubin Deep Drilling Fields using `astroplan`: altitude/azimuth tracks, airmass curves, and observing windows from Cerro Pachón (`lat = −30.2447°`). |
| `05_SphereForParallacticAngle.ipynb` | Spherical-trigonometry derivation and validation of the parallactic angle formula used throughout the dipole analysis. |
| `06_DDF_parallacticAngle.ipynb` | Parallactic-angle sweeps for all DDFs as a function of hour angle, with `TwoSlopeNorm` colour maps. Figures saved to `figs_TOOLS_06_DDF-PARAANGLE/`. |
| `07_DDF_DCR.ipynb` | Theoretical Differential Chromatic Refraction (DCR) predictions for each LSST band using the Ciddor refractive-index formula and photon-count-weighted `σ_n(b)`. Figures saved to `figs_TOOLS_07_DDF-DCR/`. |
| `07_DDF_DCR_backup.ipynb` | Backup snapshot of `07_DDF_DCR.ipynb` before the last major revision. |
| `08_polarmap_tanzenith.ipynb` | Polar-projection map of DDF trajectories in horizontal coordinates (Az, Alt), colour-coded by tan(zenith angle). Used to visualise DCR amplitude across the sky accessible to Rubin. Figures saved to `figs_TOOLS_08_POLARMAP-TANZENITH/`. |
| `08_polarmap_tanzenith_backup.ipynb` | Backup snapshot of `08_polarmap_tanzenith.ipynb`. |

### Output directories

| Directory | Contents |
|-----------|----------|
| `figs_TOOLS_06_DDF-PARAANGLE/` | PDF + PNG figures from `06_DDF_parallacticAngle.ipynb` |
| `figs_TOOLS_07_DDF-DCR/` | PDF + PNG figures from `07_DDF_DCR.ipynb` |
| `figs_TOOLS_08_POLARMAP-TANZENITH/` | PDF + PNG figures from `08_polarmap_tanzenith.ipynb` |

---

## Scientific context

These tools support the study of **Differential Chromatic Refraction** effects on
difference-image-analysis (DIA) dipole artefacts in Rubin/LSST alerts, as
described in the `08_Dipoles/` analysis directory. Key physical ingredients are:

- **Ciddor formula** for the wavelength-dependent refractive index of moist air
  at Cerro Pachón conditions.
- **Photon-count-weighted band dispersion** `σ_n(b)` derived from LSST
  throughput curves.
- **Parallactic angle** geometry linking the dipole orientation in the focal
  plane to the atmospheric refraction direction on the sky.
- **tan(z)** scaling of the DCR angular shift, directly related to the observed
  dipole separation in DIA images.

---

## Dependencies

```
astropy
astroplan
numpy
scipy
matplotlib
```

Notebooks run under the `conda_py313` kernel.

---

## Author

Sylvie Dagoret-Campagne — IJCLab / IN2P3 / CNRS, Université Paris-Saclay
Rubin/LSST commissioning & alert science
