# Fink/LSST — Light Curve Analysis for Atmospheric Transparency Calibration

This directory contains a series of Jupyter notebooks that retrieve, classify,
and visualise photometric light curves from the [Fink](https://fink-portal.org)
alert broker for LSST/Rubin commissioning data, with the goal of identifying
stable stellar and galactic sources suitable for **atmospheric transparency calibration**.

---

## Context

During the Rubin Observatory Science Verification (SV) phase, alert packets are
distributed through the Fink broker, which enriches them with crossmatch metadata
from external catalogues (Gaia DR3, SIMBAD, Legacy Survey DR8, Mangrove, VSX, TNS).
The notebooks query the [Fink LSST API](https://api.lsst.fink-portal.org) to
download light curves in the six LSST bands (*u g r i z y*) and measure their
photometric stability (normalised RMS variability σ/⟨f⟩) per source class.

Two complementary strategies are implemented:

- **Block / group strategy** (notebooks 01–06): objects are retrieved by spatial
  cone search on each Deep Drilling Field and classified client-side using Fink
  crossmatch columns (`f:xm_*`).
- **Tag strategy** (notebooks 07–08): objects are retrieved globally by Fink
  classification tag (`/api/v1/tags`) and then filtered spatially per DDF.
  The Fink tag name directly serves as the group key.

---

## Notebooks

### `01_fink_block_lightcurves.ipynb` — Data retrieval & light-curve analysis

**What it does:**

1. **Cone search** each LSST Deep Drilling Field (COSMOS, ELAIS-S1, XMM-LSS,
   ECDFS, EDFS, M49 …) via `POST /api/v1/conesearch` using the `r:` column
   prefix required by the Fink LSST API.
2. **Deduplication** — keeps one entry per `diaObjectId`, retaining only objects
   with at least `NP_MIN = 50` detections.
3. **Classification** — assigns each object to a calibration group based on Fink
   crossmatch columns (`f:xm_gaiadr3_*`, `f:xm_simbad_otype`,
   `f:xm_legacydr8_pstar`, `f:xm_mangrove_*`, `f:is_sso`).
   Groups include: `gaia_star_stable`, `gaia_star_variable`, `simbad_star`,
   `simbad_galaxy`, `legacy_star`, `legacy_galaxy`, `mangrove_galaxy`,
   `solar_system`, `fink_cataloged`, `unclassified`.
4. **Light curve download** — fetches full diaSources (`/api/v1/sources`) and
   forced photometry (`/api/v1/fp`) for up to 100 objects.
5. **NaN cleaning** — removes rows with missing flux, flux error, or MJD at
   every stage (after SNR filtering, after flux-to-magnitude conversion, and
   before plotting).
6. **Flatness metrics** — computes σ/⟨f⟩ per object per band and stores the
   results in `data_FINK_BLOCK_LC_01/flatness_metrics.csv`.
7. **Visualisations** — boxplot of variability by group and band; light curve
   grids in flux (nJy) and AB magnitude for the top-20 objects per group;
   calibration scatter plot (mean flux vs. median RMS).
8. **Persistence** — saves all filtered light curves to Parquet files
   (`{group}_fp.parquet`, `{group}_src.parquet`) under `data_FINK_BLOCK_LC_01/`.

**Cache structure:**
```python
lc_cache[group][oid] = {'fp': DataFrame, 'src': DataFrame}
```

**Outputs written to disk:**

| Path | Content |
|------|---------|
| `data_FINK_BLOCK_LC_01/{group}_fp.parquet` | Forced-photometry light curves |
| `data_FINK_BLOCK_LC_01/{group}_src.parquet` | Detection-based light curves |
| `data_FINK_BLOCK_LC_01/flatness_metrics.csv` | Per-object, per-band RMS metrics |
| `figs_FINK_BLOCK_LC_01/01_flatness_boxplot_by_group.{pdf,png}` | Variability boxplot |
| `figs_FINK_BLOCK_LC_01/02_lc_{group}_{mode}.{pdf,png}` | Light curve grids |
| `figs_FINK_BLOCK_LC_01/03_calibration_summary.{pdf,png}` | Calibration scatter plot |

---

### `01_fink_block_lightcurves_lmcsmc.ipynb` — Variant: LMC / SMC fields

Same pipeline as notebook 01, adapted for the **Large and Small Magellanic Cloud**
fields instead of the standard Deep Drilling Fields.
Outputs are written to `data_FINK_BLOCK_LC_LMCSMC/` and figures to
`figs_FINK_BLOCK_LC_LMCSMC/`.

---

### `01_fink_block_lightcurves_showcalibcurves.ipynb` — Variant: calibration curve display

A lightweight variant of notebook 01 focused on displaying only the light curves
of sources flagged as suitable for photometric calibration (`calib` groups).
Useful for a quick visual inspection of the calibration sample without rerunning
the full pipeline.

---

### `02_fink_block_lightcurves_replot.ipynb` — Offline re-visualisation (block strategy)

**What it does:**

Reads all Parquet files and the CSV produced by notebook 01 — **no API call is
made** — and reproduces or extends the same set of plots.

1. **Auto-discovery** — scans `data_FINK_BLOCK_LC_01/` with `glob` to find all
   available groups without hard-coding their names.
2. **Cache reconstruction** — loads each `_fp` and `_src` Parquet file and
   rebuilds the `lc_cache[group][oid]` dictionary used by the plotting functions.
   Magnitude columns (`mag`, `mag_err`) are recomputed on-the-fly if absent.
3. **Defensive NaN removal** — applies `dropna` on core columns at load time and
   a finite-value mask just before each `errorbar` call.
4. **PLOT_MODE filter** — select `'all'` groups, only `'calib'` groups, or only
   `'exclude'` (variable, transient, SSO) groups via a single configuration variable.
5. **Group-level plots** — flux and magnitude grids for all selected groups,
   identical layout to notebook 01.
6. **Single-object inspector** (section 9) — detailed flux + magnitude side-by-side
   plot per band for any chosen `TARGET_GROUP` / `TARGET_OID`.
7. **Calibration summary** (section 10) — scatter plot and ranking table read from
   `flatness_metrics.csv`.

**Figures are saved to** `figs_FINK_BLOCK_LC_01_02/`.

---

### `02_fink_block_lightcurves_replot_lmcsmc.ipynb` — Variant: LMC / SMC replot

Offline re-visualisation counterpart of `01_fink_block_lightcurves_lmcsmc.ipynb`.
Reads data from `data_FINK_BLOCK_LC_LMCSMC/` and saves figures to
`figs_FINK_BLOCK_LC_LMCSMC/`.

---

### `03_fink_add_visitId.ipynb` — Add visit identifiers to light curve data

**What it does:**

Enriches the per-detection source tables produced by notebook 01 with the
**Rubin visit identifier** (`visitId`) needed to retrieve individual exposures
via the Butler.

1. Reads the `{group}_src.parquet` files from `data_FINK_BLOCK_LC_01/`.
2. Cross-matches the `r:visit` column returned by the Fink API against the
   visit index (`visit_index.csv`) to confirm and normalise visit IDs.
3. Writes back enriched Parquet files and a consolidated visit index.

**Outputs written to disk:**

| Path | Content |
|------|---------|
| `data_FINK_BLOCK_LC_01/visit_index.csv` | Unique visit IDs across all sources |
| `data_FINK_BLOCK_LC_01/{group}_src.parquet` | Source tables with normalised `visitId` |

---

### `04_fink_selectDIAObject_tovisitIddetector.ipynb` — Select objects by visit & detector

**What it does:**

Filters the object catalogue to keep only objects observed in a specific set of
visits and detector numbers, enabling targeted Butler queries.

1. Loads the enriched source tables from notebook 03.
2. Applies a user-defined selection on `visitId` and `detector` number.
3. Exports a filtered object list and a per-visit/detector summary table
   suitable for batch Butler `isr` or `calibrate` calls.

**Outputs written to disk:**

| Path | Content |
|------|---------|
| `data_FINK_BLOCK_LC_01/visit_summary_src.csv` | Per-visit source summary |
| `data_FINK_BLOCK_LC_01/visit_index_fp.csv` | Visit index for forced-photometry data |
| `data_FINK_BLOCK_LC_01/visit_summary_fp.csv` | Per-visit forced-photometry summary |

---

### `05_fink_download_objects.ipynb` — Download object-level aggregate summary

**What it does:**

Downloads **object-level aggregate statistics** from the Fink
`/api/v1/objects` endpoint for every `diaObjectId` in `flatness_metrics.csv`.
These columns (medians, means, global statistics computed across all diaSources)
are distinct from the per-detection and per-epoch data fetched in notebook 01.

1. Loads the unique `diaObjectId` list from `flatness_metrics.csv`
   (the canonical trace of `lc_cache` in notebook 01).
2. Probes the API schema with a single-object query and prints all available columns.
3. Iterates over all objects, querying `/api/v1/objects` with a configurable
   inter-request delay (`API_SLEEP = 0.25 s`).
4. Assembles the results into a single DataFrame, drops duplicate `diaObjectId`
   columns potentially returned by the API, and reports a fill-rate inventory.
5. Saves the result as both Parquet (primary) and CSV.
6. Verifies the output with a read-back check.

**Data flow:**
```
flatness_metrics.csv  →  unique diaObjectId values (objects in lc_cache)
    ↓
POST https://api.lsst.fink-portal.org/api/v1/objects   →  summary per diaObjectId
    ↓
data_FINK_BLOCK_LC_01/objects_all.parquet   (+  objects_all.csv)
```

**Outputs written to disk:**

| Path | Content |
|------|---------|
| `data_FINK_BLOCK_LC_01/objects_all.parquet` | Object-level aggregate summary (primary) |
| `data_FINK_BLOCK_LC_01/objects_all.csv` | Same data in CSV format |

---

### `06_fink_color_color_diagram.ipynb` — Colour-colour diagram (G−R) vs (R−I)

**What it does:**

Reads `objects_all.parquet` produced by notebook 05 and plots a
**colour-colour diagram** in AB magnitudes with error bars on both axes.

- **X-axis**: R − I (AB mag)
- **Y-axis**: G − R (AB mag)
- Error bars on both axes, propagated in quadrature from per-band magnitude uncertainties
- Objects colour-coded by classification group inherited from notebook 01

#### Flux → magnitude conversion

LSST/Fink fluxes are in nanojansky (nJy). The AB magnitude and its uncertainty are:

$$m = -2.5\log_{10}(f_{\rm nJy}) + 31.4, \qquad \sigma_m = \frac{2.5}{\ln 10}\,\frac{\sigma_f}{f}$$

Colour uncertainties are propagated in quadrature:

$$\sigma_{G-R} = \sqrt{\sigma_{m_g}^2 + \sigma_{m_r}^2}, \qquad
\sigma_{R-I} = \sqrt{\sigma_{m_r}^2 + \sigma_{m_i}^2}$$

#### Column-discovery strategy

The notebook automatically searches for per-band photometric columns in
`objects_all.parquet` using keyword pattern matching, with three fallback strategies:

1. **Flux columns found** → compute AB magnitudes from nJy fluxes.
2. **Magnitude columns found directly** → use them as-is.
3. **Fallback** → pivot `flatness_metrics.csv` (mean flux per band per object) and convert.

**Outputs written to disk:**

| Path | Content |
|------|---------|
| `figs_FINK_BLOCK_LC_01_01_02/colour_colour_gr_ri.png/.pdf` | Combined colour-colour diagram (all groups) |
| `figs_FINK_BLOCK_LC_01_01_02/magnitude_histograms_gri.png` | Magnitude distributions per band (g, r, i) |
| `figs_FINK_BLOCK_LC_01_01_02/colour_colour_gr_ri_per_group.png` | Split-panel diagram — one panel per group |

---

### `07_fink_tags_lightcurves.ipynb` — Data retrieval & light-curve analysis (tag strategy)

**What it does:**

Retrieves photometric light curves for objects found via the **Fink LSST
classification tags** (`/api/v1/tags` endpoint), restricted to the LSST Deep
Drilling Fields by client-side spatial cross-matching.

1. **Global tag fetch** — for each tag in `TAGS_TO_QUERY`, fetches up to
   `N_PER_TAG = 50 000` alerts globally via `GET /api/v1/tags?tag=<tag>&n=N`.
   RA/Dec coordinates are included in the returned columns.
2. **Client-side spatial filter** — for each (tag, DDF) pair, keeps only objects
   whose coordinates fall within `CONE_RADIUS` arcsec of the DDF centre using
   the vectorised Vincenty formula.  This requires only `len(TAGS_TO_QUERY)` API
   calls (instead of `len(TAGS) × len(DDFs)`).
3. **Deduplication** — one entry per `diaObjectId`; objects must have at least
   `NP_MIN = 200` detections.
4. **Light curve download** — fetches full diaSources (`/api/v1/sources`) and
   forced photometry (`/api/v1/fp`) for up to 200 objects, sorted by
   `nDiaSources` descending.
5. **Group key = tag** — the Fink tag name directly replaces the
   `classify_object()` scheme of notebook 01.  The DDF name is preserved as a
   `field` attribute in both `lc_cache` and the Parquet files.
6. **Flatness metrics** — same σ/⟨f⟩ computation as notebook 01, with an extra
   breakdown by DDF (`field`).
7. **Visit summary** — builds `visit_summary_src.csv` / `visit_summary_fp.csv`
   and `visit_index.csv` / `visit_index_fp.csv` with `tag` and `field` columns.
8. **Persistence** — saves light curves to `data_FINK_BLOCK_LC_07/` and ranking
   to `tag_ranking.csv`.

Currently queried tags:

| Tag | Description |
|-----|-------------|
| `extragalactic_lt20mag_candidate` | Rising, bright (mag < 20), extragalactic candidates |
| `extragalactic_new_candidate` | New (< 48 h first detection) and potentially extragalactic |
| `hostless_candidate` | Hostless alerts according to ELEPHANT (arXiv:2404.18165) |
| `in_tns` | Alerts with a known counterpart in TNS (AT or confirmed) |
| `sn_near_galaxy_candidate` | Alerts matching a galaxy catalog and consistent with SNe |

**Cache structure:**
```python
lc_cache[oid] = {
    'fp'   : DataFrame,   # forced photometry
    'src'  : DataFrame,   # diaSources
    'group': str,         # = tag name
    'tag'  : str,         # = tag name (explicit copy)
    'field': str,         # DDF name (e.g. 'COSMOS')
}
```

**Comparison with notebook 01:**

| Aspect | NB 01 (blocks / groups) | NB 07 (tags × DDFs) |
|--------|------------------------|---------------------|
| Object selection | Cone search POST `/conesearch` per DDF | GET `/tags` global then client-side spatial filter per DDF |
| Classification | Custom `classify_object()` on `f:xm_*` | Fink tag = group directly |
| `lc_cache` key | `lc_cache[group][oid]` | `lc_cache[oid]` |
| `field` attribute | DDF name from cone search loop | DDF name from spatial filter loop |
| Output directory | `data_FINK_BLOCK_LC_01` | `data_FINK_BLOCK_LC_07` |

**Outputs written to disk:**

| Path | Content |
|------|---------|
| `data_FINK_BLOCK_LC_07/{tag}_fp.parquet` | Forced-photometry light curves |
| `data_FINK_BLOCK_LC_07/{tag}_src.parquet` | Detection-based light curves |
| `data_FINK_BLOCK_LC_07/flatness_metrics.csv` | Per-object, per-band RMS metrics |
| `data_FINK_BLOCK_LC_07/tag_ranking.csv` | Variability ranking by tag |
| `data_FINK_BLOCK_LC_07/visit_summary_src.csv` | Per-visit diaSources summary |
| `data_FINK_BLOCK_LC_07/visit_summary_fp.csv` | Per-visit forced-photometry summary |
| `data_FINK_BLOCK_LC_07/visit_index.csv` | Global visit index (diaSources) |
| `data_FINK_BLOCK_LC_07/visit_index_fp.csv` | Global visit index (forced photometry) |
| `figs_FINK_BLOCK_LC_07/01_flatness_boxplot_by_tag.{pdf,png}` | Variability boxplot by tag |
| `figs_FINK_BLOCK_LC_07/01b_flatness_boxplot_by_field.{pdf,png}` | Variability boxplot by DDF |
| `figs_FINK_BLOCK_LC_07/02_lc_{tag}_{mode}.{pdf,png}` | Light curve grids |
| `figs_FINK_BLOCK_LC_07/03_tag_summary_scatter.{pdf,png}` | Variability scatter plot |

---

### `08_fink_tags_lightcurves_replot.ipynb` — Offline re-visualisation (tag strategy)

**What it does:**

Reads all Parquet files and CSVs produced by notebook 07 — **no API call is
made** — and reproduces or extends the same set of plots.

1. **Auto-discovery** — scans `data_FINK_BLOCK_LC_07/` with `glob` to find all
   available tags without hard-coding their names.
2. **Cache reconstruction** — loads each `_fp` and `_src` Parquet file and
   rebuilds the `lc_cache[oid]` dictionary with `group`, `tag`, and `field` keys
   extracted from the stored Parquet columns.
   Magnitude columns (`mag`, `mag_err`) are recomputed on-the-fly if absent.
3. **PLOT_MODE filter** — set to `'all'` (default) or a Python list of tag names
   to restrict which tags are plotted.
4. **Flatness boxplots** — per-tag variability (section 6) and per-DDF variability
   (section 6b), identical to notebook 07.
5. **Light curve grids** — flux (section 8) and magnitude (section 9) for all
   selected tags, with the DDF name displayed in each y-axis label.
6. **Single-object inspector** (section 10) — detailed flux + magnitude
   side-by-side plot per band for any chosen `TARGET_TAG` / `TARGET_OID`.
7. **Summary scatter plot** (section 11) — variability vs. mean flux per tag,
   per band.
8. **Ranking table** (section 12) — reads `tag_ranking.csv` if present, or
   recomputes the ranking on-the-fly from `flatness_metrics.csv`.

**Comparison with notebook 02:**

| Aspect | NB 02 (block replot) | NB 08 (tag replot) |
|--------|---------------------|-------------------|
| Source data directory | `data_FINK_BLOCK_LC_01` | `data_FINK_BLOCK_LC_07` |
| `lc_cache` structure | `lc_cache[group][oid]` | `lc_cache[oid]` with `group`/`tag`/`field` keys |
| Group key | `classify_object()` category | Fink tag name directly |
| PLOT_MODE options | `'all'` / `'calib'` / `'exclude'` | `'all'` / list of tag names |
| Extra plots | — | Per-DDF flatness boxplot, tag ranking table |
| Figure directory | `figs_FINK_BLOCK_LC_01_02` | `figs_FINK_BLOCK_LC_07_08` |

**Figures are saved to** `figs_FINK_BLOCK_LC_07_08/`.

---

## Directory layout

```
03_fink_api_blockselections/
│
├── 01_fink_block_lightcurves.ipynb                    # block strategy: data retrieval & analysis
├── 01_fink_block_lightcurves_lmcsmc.ipynb             # variant: LMC/SMC fields
├── 01_fink_block_lightcurves_showcalibcurves.ipynb    # variant: calibration curves only
├── 02_fink_block_lightcurves_replot.ipynb             # block strategy: offline re-visualisation
├── 02_fink_block_lightcurves_replot_lmcsmc.ipynb      # variant: LMC/SMC replot
├── 03_fink_add_visitId.ipynb                          # add Rubin visit identifiers
├── 04_fink_selectDIAObject_tovisitIddetector.ipynb    # select objects by visit & detector
├── 05_fink_download_objects.ipynb                     # download object-level aggregate summary
├── 06_fink_color_color_diagram.ipynb                  # colour-colour diagram (G−R) vs (R−I)
├── 07_fink_tags_lightcurves.ipynb                     # tag strategy: data retrieval & analysis
├── 08_fink_tags_lightcurves_replot.ipynb              # tag strategy: offline re-visualisation
│
├── README.md                                          # this file
│
├── lsst_meridian_visibility.py                        # helper: LSST meridian visibility curves
├── lsst_meridian_visibility_fr.py                     # idem (French labels)
│
├── data_FINK_BLOCK_LC_01/                             # block strategy outputs
│   ├── flatness_metrics.csv
│   ├── objects_all.parquet / objects_all.csv
│   ├── visit_index.csv / visit_index_fp.csv
│   ├── visit_summary_src.csv / visit_summary_fp.csv
│   ├── gaia_star_stable_fp.parquet
│   ├── gaia_star_stable_src.parquet
│   ├── gaia_star_variable_fp.parquet
│   ├── gaia_star_variable_src.parquet
│   ├── simbad_galaxy_fp.parquet
│   ├── simbad_galaxy_src.parquet
│   ├── mangrove_galaxy_2mass_fp.parquet
│   ├── mangrove_galaxy_2mass_src.parquet
│   ├── tns_transient_fp.parquet
│   ├── tns_transient_src.parquet
│   ├── vsx_variable_fp.parquet
│   ├── vsx_variable_src.parquet
│   ├── unclassified_fp.parquet
│   └── unclassified_src.parquet
│
├── data_FINK_BLOCK_LC_07/                             # tag strategy outputs
│   ├── flatness_metrics.csv
│   ├── tag_ranking.csv
│   ├── visit_index.csv / visit_index_fp.csv
│   ├── visit_summary_src.csv / visit_summary_fp.csv
│   ├── extragalactic_lt20mag_candidate_fp.parquet
│   ├── extragalactic_lt20mag_candidate_src.parquet
│   ├── extragalactic_new_candidate_fp.parquet
│   ├── extragalactic_new_candidate_src.parquet
│   ├── hostless_candidate_fp.parquet
│   ├── hostless_candidate_src.parquet
│   ├── in_tns_fp.parquet
│   ├── in_tns_src.parquet
│   ├── sn_near_galaxy_candidate_fp.parquet
│   └── sn_near_galaxy_candidate_src.parquet
│
├── data_FINK_BLOCK_LC_LMCSMC/                        # LMC/SMC variant outputs
│
├── figs_FINK_BLOCK_LC_01/                            # figures from notebook 01
├── figs_FINK_BLOCK_LC_01_02/                         # figures from notebooks 02 & 06
├── figs_FINK_BLOCK_LC_01_AUG/                        # figures from augmented variant
├── figs_FINK_BLOCK_LC_07/                            # figures from notebook 07
├── figs_FINK_BLOCK_LC_07_08/                         # figures from notebook 08
└── figs_FINK_BLOCK_LC_LMCSMC/                        # figures for LMC/SMC variant
```

---

## Execution order

The notebooks must be run in order, as each one depends on outputs from the previous:

```
Block strategy
──────────────
01  →  02  (optional offline replot, no API call)
01  →  03  →  04
01  →  05  →  06

Tag strategy
────────────
07  →  08  (optional offline replot, no API call)
```

The two strategies are independent: notebooks 07–08 do not depend on 01–06.

---

## Requirements

| Package | Purpose |
|---------|---------|
| `requests` | Fink API HTTP calls (notebooks 01, 07 only) |
| `pandas ≥ 2.0` | DataFrames, Parquet I/O |
| `numpy` | Numerical computations |
| `matplotlib` | Plotting |
| `pyarrow` or `fastparquet` | Parquet backend for pandas |
| `ipympl` *(optional)* | Interactive `%matplotlib widget` backend |

Install with:
```bash
pip install requests pandas numpy matplotlib pyarrow
```
or activate the `conda_py313` environment already configured for this project.

---

## Key API notes

- The Fink LSST API requires the **`r:` column prefix** in cone-search and
  source requests (using `i:` causes HTTP 500 errors).
- Block flags (`b_*`) cannot be used as API filters; classification is done
  client-side via `f:xm_*` crossmatch columns.
- The `/api/v1/tags` endpoint does **not** support spatial (RA/Dec/radius)
  filtering; spatial selection must be applied client-side after the global fetch.
- Endpoints used across the notebooks:

| Endpoint | Method | Used in |
|----------|--------|---------|
| `/api/v1/conesearch` | POST | notebook 01 |
| `/api/v1/sources` | POST | notebooks 01, 07 |
| `/api/v1/fp` | POST | notebooks 01, 07 |
| `/api/v1/objects` | POST | notebook 05 |
| `/api/v1/tags` | GET | notebooks 01, 07 |
| `/api/v1/blocks` | GET | notebooks 01, 07 |

---

## Authors

Notebook series developed for the Rubin/LSST SV atmospheric transparency
calibration study using the Fink alert broker.
