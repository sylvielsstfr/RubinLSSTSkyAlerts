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

The `plot_skymap_with_annotations()` function supports both equatorial (`coord='C'`)
and Galactic (`coord='G'`) projections. In Galactic mode all overlays (plane,
landmarks, DDFs) are automatically converted to Galactic coordinates (l, b) before
being passed to the healpy projection routines, and axis tick labels switch to
(l, b) accordingly.

### `03_fink_healpix_temporal_dynamics.ipynb`
Temporal dynamics of Fink/LSST alerts on HEALPix skymaps:

- **Fixed time windows** — last 24 h, 3 days, 7 days, 30 days
- **Comparative 2×2 panel** across all four windows
- **Age-layer maps** — differential skymaps by alert age bracket
- **Custom date range** — set `CUSTOM_START` / `CUSTOM_STOP` in the config cell
- **Sliding-window animation** — GIF of a 3-day window rolling over 30 days
- **Alert rate curves** — hourly total rate and daily rate per tag

Same astronomical annotations as notebook 02.

### `04_fink_api_statistics.ipynb`
Exploration of the nightly and cumulative statistics exposed by the
`/api/v1/statistics` endpoint of the Fink LSST API. This endpoint returns
one row per observing night with per-tag alert counters. The notebook covers:

- **Schema discovery** — automatic detection of all available columns, dtype
  summary, and descriptive statistics
- **Nightly alert counts** — dual-panel bar chart (total alerts + unique objects)
- **Cumulative stream** — filled area curve with dual Y-axis (alerts / objects)
- **Per-tag breakdown** — pie chart of cumulative totals (top 10) and nightly
  stacked bar chart (top 8 tags)
- **Monthly aggregation** — resampled bar chart with labelled totals
- **Per-tag cumulative growth** — one curve per tag (top 6) for trend comparison
- **Rolling 7-night mean** — alert rate smoothing superimposed on nightly bars
- **Day-of-week patterns** — mean nightly alert count per weekday
- **Week × day-of-week heatmap** — 2-D calendar view of alert activity
- **Single-night deep-dive** — re-fetch and full column display for the most
  productive observed night
- **Summary table** — key figures (total, mean, median, max night, date range)

API parameters used:

| Parameter       | Values                                      |
|-----------------|---------------------------------------------|
| `date`          | `''` (all), `YYYY`, `YYYYMM`, `YYYYMMDD`   |
| `columns`       | comma-separated `f:`-prefixed column names  |
| `output-format` | `csv` (default in this notebook)            |

Outputs are saved to `data_FINKAPISTAT04/` (CSV) and `figs_FINKAPISTAT04/` (PDF + PNG).

### `05_fink_api_blocks.ipynb`
Decoding and exploration of the `/api/v1/blocks` endpoint of the Fink LSST API.
This endpoint returns the **complete schema** of the Fink HBase database, i.e. the
full list of column definitions organised into logical *block families* (column groups).

In the Fink HBase backend, each column carries a two-character prefix that identifies
its block family:

| Prefix | Content |
|--------|---------|
| `i:`   | Raw Rubin/LSST alert fields (`diaSource` / `diaObject`) |
| `r:`   | Rubin-derived fields further processed by Fink |
| `d:`   | Fink science module outputs (classifiers, cross-matches) |
| `f:`   | Fink broker metadata (night counters, statistics) |
| `b:`   | Binary data / cutout metadata |

The notebook covers:

- **Raw JSON inspection** — pretty-print of the API response and automatic detection
  of its structure (flat list, dict of lists, or nested dict)
- **Normalisation** — adaptive flattening into a tidy DataFrame regardless of the
  response format, with automatic inference of the block prefix from column names
- **Schema completeness** — null-count and fill-rate summary per DataFrame column
- **Columns per block prefix** — horizontal bar chart and pie chart showing how many
  columns belong to each block family
- **Data-type distribution** — bar chart of column data types across the full schema
- **Data-type breakdown per prefix** — stacked bar chart crossing block family and
  data type
- **Column name length distribution** — histogram and top-20 longest names
- **Per-prefix column listing** — full tabular display of every column per block family,
  with optional type and description columns; each prefix exported as a CSV file
- **Cross-reference with live endpoints** — comparison of block-defined columns against
  those actually returned by `/api/v1/statistics` and `/api/v1/tags`
- **Block completeness histogram** — grouped bar chart (defined vs. active per prefix)
- **Keyword analysis** — CamelCase / snake_case tokenisation of all column names,
  top-50 recurring keywords plotted as a horizontal bar chart
- **Summary table** — total counts per block, active columns per live endpoint

Outputs are saved to `data_FINKAPIBLOCKS05/` (JSON, CSV) and `figs_FINKAPIBLOCKS05/` (PDF + PNG).

---

## Output directory convention

Each notebook writes its generated files into two dedicated subdirectories:

```
data_<TAG><NN>/   — raw and processed data (CSV, JSON, parquet, …)
figs_<TAG><NN>/   — figures exported as PDF and PNG
```

| Notebook | Tag        | Data dir                  | Figs dir                  |
|----------|------------|---------------------------|---------------------------|
| 04       | FINKAPISTAT| `data_FINKAPISTAT04/`     | `figs_FINKAPISTAT04/`     |
| 05       | FINKAPIBLOCKS| `data_FINKAPIBLOCKS05/` | `figs_FINKAPIBLOCKS05/`   |

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

| Endpoint               | Description                                        |
|------------------------|----------------------------------------------------|
| `/api/v1/tags`         | Alerts filtered by scientific classification tag   |
| `/api/v1/latests`      | Latest alerts by class (incl. Solar System)        |
| `/api/v1/objects`      | Aggregated statistics per `diaObjectId`            |
| `/api/v1/statistics`   | Per-night alert stream statistics (all tags)       |
| `/api/v1/blocks`       | Full HBase schema — block family and column definitions |
| `/api/v1/schema`       | Column schema for each endpoint                    |

Available tags (as of March 2026):
- `extragalactic_lt20mag_candidate`
- `extragalactic_new_candidate`
- `hostless_candidate`
- `in_tns`
- `sn_near_galaxy_candidate`

---

## Rubin/LSST Deep Drilling Fields

| Field                   | RA (°)   | Dec (°)  |
|-------------------------|----------|----------|
| COSMOS                  | 150.1191 | +2.2058  |
| XMM-LSS                 | 34.3900  | −4.9000  |
| ECDFS                   | 53.1250  | −28.1000 |
| EDFS-a                  | 58.9000  | −49.3150 |
| EDFS-b                  | 63.6000  | −47.6000 |
| Euclid Deep Field South | 61.2400  | −48.4230 |

---

## Author

Sylvie Dagoret-Campagne — IJCLab / IN2P3
