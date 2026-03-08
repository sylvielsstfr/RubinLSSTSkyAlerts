# 02 — Fink API Exploration

This directory contains notebooks for exploring and visualizing alert data from the
[Fink broker](https://fink-portal.org) for the Rubin/LSST survey.

---

## Notebooks

### `01_fink_ra_histogram.ipynb`
Stacked histograms of Fink/LSST alerts as a function of Right Ascension (RA),
broken down by scientific classification tag. Provides a first look at the
angular distribution of alerts across the surveyed sky.

### `01b_fink_dec_histogram.ipynb`
Stacked histograms of Fink/LSST alerts as a function of Declination (Dec),
broken down by scientific classification tag. Complements the RA notebook by
showing the latitudinal sky coverage. The Dec distribution directly reflects
the Rubin/LSST Wide-Fast-Deep footprint and the observatory latitude
(Cerro Pachón, –30.24°). Includes:

- **Stacked histogram by tag** — alert count vs Dec, one colour per classification tag
- **Per-tag side-by-side panels** — individual Dec distributions per tag
- **Stacked histogram by spectral band** — same Dec axis but stacked by filter
  (`u`, `g`, `r`, `i`, `z`, `y`) to reveal filter-dependent coverage patterns
- Observatory latitude and approximate Galactic plane region overlaid as reference lines

### `02_fink_healpix_skymap_statistics.ipynb`
Full-sky HEALPix statistics of Fink/LSST alerts:

- **Total skymap** — cumulative density of all alerts (equatorial and Galactic projections)
- **Per-tag skymaps** — one map per classification tag:
  `extragalactic_lt20mag_candidate`, `extragalactic_new_candidate`,
  `hostless_candidate`, `in_tns`, `sn_near_galaxy_candidate`, and Solar System objects
- **Comparative multi-tag panel** — 2×N grid for quick visual comparison
- **Spatial overlap matrix** — Jaccard index between tag pairs
- **Galactic latitude density** — histogram corrected for cos(b), per tag

Astronomical annotations on every map: Galactic plane (b = 0° and |b| = 10°),
Galactic centre, Large and Small Magellanic Clouds, and all six
Rubin/LSST Deep Drilling Fields (COSMOS, XMM-LSS, ECDFS, EDFS-a, EDFS-b,
Euclid Deep Field South).

### `03_fink_healpix_temporal_dynamics.ipynb`
Temporal dynamics of Fink/LSST alerts on HEALPix skymaps:

- **Fixed time windows** — last 24 h, 3 days, 7 days, 30 days
- **Comparative 2×2 panel** across all four windows
- **Age-layer maps** — differential skymaps by alert age bracket
- **Custom date range** — set `CUSTOM_START` / `CUSTOM_STOP` in the config cell
- **Sliding-window animation** — GIF of a 3-day window rolling over 30 days
- **Alert rate curves** — hourly total rate and daily rate per tag

Same astronomical annotations as notebook 02.

---

## Dependencies

| Package     | Role                                     |
|-------------|------------------------------------------|
| `healpy`    | HEALPix pixelisation and Mollweide plots |
| `astropy`   | Coordinate transforms, time (MJD/TAI)   |
| `numpy`     | Array operations                         |
| `matplotlib`| Plotting, animations                     |
| `requests`  | Fink REST API calls                      |
| `pandas`    | Tabular data handling                    |

Install (or update) the full project dependencies from the repository root:

```bash
pip install -e ".[dev]"
```

---

## Fink LSST API

All data are fetched from the public Fink LSST REST API:

```
https://api.lsst.fink-portal.org
```

Key endpoints used:

| Endpoint            | Description                                      |
|---------------------|--------------------------------------------------|
| `/api/v1/tags`      | Alerts filtered by scientific classification tag |
| `/api/v1/latests`   | Latest alerts by class (incl. Solar System)      |
| `/api/v1/objects`   | Aggregated statistics per `diaObjectId`           |
| `/api/v1/schema`    | Column schema for each endpoint                  |

Available tags (as of March 2026):
- `extragalactic_lt20mag_candidate`
- `extragalactic_new_candidate`
- `hostless_candidate`
- `in_tns`
- `sn_near_galaxy_candidate`

---

## Rubin/LSST Deep Drilling Fields

| Field                  | RA (°)   | Dec (°)  |
|------------------------|----------|----------|
| COSMOS                 | 150.1191 | +2.2058  |
| XMM-LSS                | 34.3900  | −4.9000  |
| ECDFS                  | 53.1250  | −28.1000 |
| EDFS-a                 | 58.9000  | −49.3150 |
| EDFS-b                 | 63.6000  | −47.6000 |
| Euclid Deep Field South| 61.2400  | −48.4230 |

---

## Author

Sylvie Dagoret-Campagne — IJCLab / IN2P3
