# rubinlsstskyalerts.fink_tools

Sub-package of `rubinlsstskyalerts` providing tools to download, process, and
visualise Rubin/LSST transient alerts retrieved from the
[Fink broker](https://lsst.fink-portal.org) REST API.

All public symbols are re-exported from `__init__.py`, so a single import line
is enough in any notebook or script:

```python
from rubinlsstskyalerts.fink_tools import FinkDataset, plot_alert_detail
from rubinlsstskyalerts.fink_tools import plot_skymap_combined, download_dataset
```

---

## File overview

```
fink_tools/
├── __init__.py                          ← package entry point, re-exports everything
├── fink_alert_lib.py                    ← alert dataset class + all plot functions
├── fink_skymap_lib.py                   ← sky-map plots (rectangular, Mollweide, HiPS)
├── fink_download_tag_dataset.py         ← download by tag — CLI + Python API
├── fink_download_alerts_with_cutouts.py ← download fixed multi-tag dataset
└── fink_download_full_cutouts.py        ← download every cutout for one diaObject
```

---

## Module descriptions

### `fink_alert_lib.py`
*Author: dagoret — 2026-02-27*

Core visualisation library.  Reads a local `fink_dataset/` directory produced
by any of the download scripts and exposes a high-level API for Jupyter
notebooks.

**Key class**

| Class | Description |
|-------|-------------|
| `FinkDataset` | Loads `alerts_catalog.parquet`, indexes light-curve `.parquet` files and cutout `.npy` arrays; provides `get_lightcurve()`, `get_cutouts()`, `get_meta()`, `list_objects()`, `summary()` |

**Key functions**

| Function | Description |
|----------|-------------|
| `flux_to_mag(flux, flux_err)` | Converts `psfFlux` (nJy) to AB magnitude; returns `(mag, mag_err)` or `mag`; NaN for non-positive flux |
| `plot_lightcurve_flux(df_lc)` | Multi-band light curve in flux units (nJy), dark portal theme |
| `plot_lightcurve_mag(df_lc)` | Multi-band light curve in AB magnitude, inverted y-axis |
| `plot_cutouts(cutouts_arr)` | Three-panel Science / Template / Difference display with ZScale stretch |
| `plot_classifiers(meta)` | Horizontal bar chart of Fink classifier scores (SNN, early-SN Ia, CATS) |
| `plot_alert_overview(dataset, obj_id)` | Compact 5-panel row: flux LC + mag LC + 3 cutouts |
| `plot_alert_detail(dataset, obj_id)` | Full 2×3 grid: LCs + classifiers + cutouts |
| `plot_tag_grid(dataset, tag)` | Overview mosaic of Science cutout thumbnails for all objects of a tag |
| `plot_tag_loop(dataset, tag)` | Iterates over a tag and calls the chosen plot type for each object |

**Constants exported**

`BAND_COLORS`, `BAND_WAVELENGTHS`, `RUBIN_ZEROPOINT`,
`DARK_BG`, `PANEL_BG`, `TEXT_COL`, `MUTED_COL`, `ACCENT`, `HIGHLIGHT`, `BORDER`

**Expected dataset layout**

```
fink_dataset/
├── alerts_catalog.parquet   # alert metadata + Fink scores (one row per diaSource)
├── lightcurves/
│   └── <diaObjectId>.parquet
└── cutouts/
    └── <diaObjectId>_label<0|1>.npy   # shape (3, H, W) — Science/Template/Difference
```

---

### `fink_skymap_lib.py`
*Author: dagoret — 2026-03-06*

Sky-map visualisation library.  Plots the sky distribution of Fink/LSST
alerts with full astronomical context.

**Key functions**

| Function | Description |
|----------|-------------|
| `load_catalog(dataset_dir)` | Reads `alerts_catalog.parquet`, deduplicates on `diaObjectId`, keeps highest SNN score per object |
| `catalog_summary(catalog)` | Returns a per-tag statistics DataFrame (counts, RA/Dec ranges, mean SNN score, TNS matches) |
| `plot_skymap_rect(catalog, ...)` | Rectangular (RA, Dec) projection; RA increases to the left (astronomical convention); optional HiPS real-sky background |
| `plot_skymap_mollweide(catalog, ...)` | Full-sky Mollweide projection; 0h at centre; optional HiPS background reprojected onto the Mollweide ellipse |
| `plot_skymap_combined(catalog, ...)` | Two-panel figure: Mollweide (top) + rectangular zoom (bottom) |
| `fetch_hips_image(ra, dec, fov, ...)` | Downloads a HiPS sky image from CDS hips2fits; tries four strategies (astroquery FITS, astroquery JPG, direct HTTP new server, direct HTTP legacy server) |
| `overlay_hips_background(ax, ...)` | Fetches and overlays the HiPS image onto an existing `Axes` |
| `draw_radec_grid(ax, ...)` | Draws a clearly visible RA/Dec coordinate grid with formatted tick labels |
| `galactic_plane_radec(n)` | Returns (RA, Dec) points tracing the galactic plane (b = 0) in ICRS |
| `galactic_latitude_radec(b_deg, n)` | Returns (RA, Dec) points along a constant galactic latitude |

**Overlays available on all map functions**

- Galactic plane (b = 0) and optional galactic band (|b| = user-defined)
- Galactic Centre marker
- Rubin LSST Deep Drilling Fields (COSMOS, XMM-LSS, ELAIS-S1, ECDFS, EDFS-a, EDFS-b)
- Per-tag colour-coded scatter markers

**Constants exported**

`TAG_STYLES`, `DEFAULT_TAG_STYLE`, `RUBIN_DDF`,
`BORDER_COL`, `GRID_COL`, `GALPLANE_COL`, `GALBAND_COL`, `GALCENTER_COL`, `DDF_COL`

---

### `fink_download_tag_dataset.py`
*Author: dagoret — 2026-02-28*

**Configurable** download script and Python API.  Fetches alerts for a
user-chosen Fink tag and organises them into a structured directory tree.

Usable as a CLI tool or imported as a library function.

**CLI usage**

```bash
# List all available tags
python fink_download_tag_dataset.py --list-tags

# Download 50 extragalactic new-candidate alerts
python fink_download_tag_dataset.py \
    --tag extragalactic_new_candidate --n 50

# Custom output directory + dry-run
python fink_download_tag_dataset.py \
    --tag sn_near_galaxy_candidate --n 200 \
    --outdir /data/fink_dataset --dry-run
```

**Python API**

```python
from rubinlsstskyalerts.fink_tools import download_dataset
from pathlib import Path

download_dataset(
    tag="extragalactic_new_candidate",
    n=50,
    outdir=Path("fink_dataset"),
)
```

**Key functions**

| Function | Description |
|----------|-------------|
| `download_dataset(tag, n, outdir, ...)` | Full pipeline: fetches catalog, light curves and cutouts for `n` objects of `tag`; supports `--dry-run` and `skip_existing` |
| `fetch_latest_alerts(tag, n)` | Queries `/api/v1/tags`; returns a `pd.DataFrame` of the `n` most recent alerts |
| `fetch_light_curve(obj_id)` | Queries `/api/v1/sources`; returns multi-band light curve sorted by MJD |
| `fetch_cutouts(src_id)` | Queries `/api/v1/cutouts` for Science, Template and Difference; returns a dict of 2D `float32` arrays |
| `list_tags()` | Prints all available tag names with descriptions |

**Output layout**

```
fink_dataset/
└── <tag>/
    ├── catalog.parquet
    ├── light_curves/
    │   └── lc_<diaObjectId>.parquet
    └── cutouts/
        └── cutout_<diaObjectId>.npy    # np.load(..., allow_pickle=True).item()
                                         # → dict {Science, Template, Difference}
```

**Available tags**

| Tag | Label | Description |
|-----|-------|-------------|
| `extragalactic_new_candidate` | 1 | New (< 48 h) and potentially extragalactic |
| `extragalactic_lt20mag_candidate` | 1 | Rising, bright (mag < 20), extragalactic |
| `sn_near_galaxy_candidate` | 1 | SNe-like alert near a galaxy catalog entry |
| `in_tns` | 1 | Known counterpart in TNS (AT or confirmed SN) |
| `hostless_candidate` | 0 | Hostless according to ELEPHANT (arXiv:2404.18165) |

---

### `fink_download_alerts_with_cutouts.py`
*Author: dagoret — 2026-02-26*

**Fixed multi-tag** download script.  Iterates over a hard-coded set of tags
(`TAGS_CONFIG`), downloads alerts, full light curves, and cutouts, and saves a
merged catalog.  Intended for building a single consolidated `fink_dataset/`
from multiple tag categories at once.

**Key functions**

| Function | Description |
|----------|-------------|
| `fetch_by_tag(tag, n)` | Queries `/api/v1/tags`; returns up to `n` alerts for `tag` as a DataFrame |
| `fetch_lightcurve(obj_id)` | Full light curve for one `diaObjectId` via `/api/v1/sources` |
| `fetch_cutouts(src_id)` | Downloads Science, Template, Difference cutouts for one `diaSourceId`; returns a dict of 2D arrays |
| `save_cutouts_npy(obj_id, cutouts, label)` | Stacks cutouts to shape `(3, H, W)` and saves as `<obj_id>_label<label>.npy` |
| `plot_alert_summary(obj_id, df_lc, cutouts, label, tag)` | Quick diagnostic figure (flux LC + 3 cutouts); saves as `<obj_id>_summary.png` |
| `main()` | Runs the full download loop over `TAGS_CONFIG`; saves `alerts_catalog.parquet` |

**Output layout**

```
fink_dataset/
├── alerts_catalog.parquet   # merged catalog across all tags
├── alerts_catalog.csv
├── lightcurves/
│   └── <diaObjectId>.parquet
└── cutouts/
    └── <diaObjectId>_label<0|1>.npy   # shape (3, H, W)
```

---

### `fink_download_full_cutouts.py`
*Author: dagoret — 2026-02*

Downloads **every** cutout stamp for a single `diaObjectId`, across all
diaSources (all observation epochs × all spectral bands).  Designed to build
per-object temporal sequences for morphological analysis or machine-learning
datasets.

**CLI usage**

```bash
python fink_download_full_cutouts.py --obj_id 170032915988086813

# Custom output directory
python fink_download_full_cutouts.py \
    --obj_id 170032915988086813 --outdir ./my_output

# Force re-download of existing files
python fink_download_full_cutouts.py \
    --obj_id 170032915988086813 --no_skip
```

**Key functions**

| Function | Description |
|----------|-------------|
| `download_full_cutouts(obj_id, outdir, skip_existing)` | Full pipeline: fetches all diaSources then downloads all 3 cutouts per epoch; saves a manifest |
| `fetch_sources(obj_id)` | Returns all diaSources for a `diaObjectId` via `/api/v1/sources`, sorted by MJD |
| `fetch_single_cutout(src_id, kind)` | Downloads one cutout (`Science`, `Template`, or `Difference`) for a `diaSourceId`; returns a 2D `float32` array |
| `fetch_all_cutouts(src_id)` | Calls `fetch_single_cutout` for all three kinds; returns a dict or `None` on failure |

**Output layout**

```
fullcutouts_<diaObjectId>/
├── manifest.parquet          # all diaSource metadata + file paths, time-sorted
├── manifest.csv
└── cutouts/
    ├── <diaSourceId>_<band>_Science.npy      # shape (H, W), float32
    ├── <diaSourceId>_<band>_Template.npy
    └── <diaSourceId>_<band>_Difference.npy
```

---

## Column naming convention (LSST DPDD schema)

> This is a frequent source of confusion — read carefully.

| Prefix | Meaning | Example |
|--------|---------|---------|
| `r:` | Field from the **diaSource table** (table alias in the LSST DPDD) | `r:psfFlux`, `r:band`, `r:ra` |
| `f:` | Field **computed by Fink** (classifiers, cross-matches) | `f:clf_snnSnVsOthers_score`, `f:xm_tns_fullname` |

**`r:` is NOT the spectral band `r`.**  The spectral band is always the
*value* of the column `r:band` ∈ `{u, g, r, i, z, y}`.

Key photometric columns:

| Column | Unit | Notes |
|--------|------|-------|
| `r:psfFlux` | nJy | PSF-fit flux in the difference image |
| `r:psfFluxErr` | nJy | Flux uncertainty |
| `r:band` | — | Rubin spectral band: `u`, `g`, `r`, `i`, `z`, or `y` |
| `r:midpointMjdTai` | MJD (TAI) | Observation midpoint |
| `r:snr` | — | Signal-to-noise ratio |
| `f:clf_snnSnVsOthers_score` | [0, 1] | SuperNNova: SN vs everything else |
| `f:clf_earlySNIa_score` | [0, 1] | Early SN Ia classifier score |

AB magnitude conversion (uniform zero-point across all Rubin bands):

```
mag_AB = -2.5 × log10(psfFlux_nJy) + 31.4
```

---

## Fink LSST API quick reference

Base URL: `https://api.lsst.fink-portal.org/api/v1`
Swagger:  `https://api.lsst.fink-portal.org/swagger.json`

All endpoints use **HTTP GET** with query-string parameters (unlike the ZTF
portal which uses POST with a JSON body).

| Endpoint | Parameters | Returns |
|----------|-----------|---------|
| `/tags` | `tag`, `n`, `columns`, `output-format` | Latest `n` alerts matching `tag` |
| `/sources` | `diaObjectId`, `columns`, `output-format` | All diaSources for one object |
| `/cutouts` | `diaSourceId`, `kind`, `output-format` | One cutout stamp as a JSON 2D array |

---

## Dependencies

```
numpy>=1.24
pandas>=2.0
matplotlib>=3.7
astropy>=5.3
requests>=2.28
pyarrow>=12          # parquet I/O backend for pandas
astroquery>=0.4.7    # hips2fits sky backgrounds (optional)
Pillow>=9.0          # fallback JPG decode in fetch_hips_image (optional)
```

All declared in `pyproject.toml`; installed automatically with:

```bash
pip install -e ".[dev]"   # from repo root
```
