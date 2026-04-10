# README — 05_runbindata_visits

**Author:** Sylvie Dagoret-Campagne (IJCLab/IN2P3/CNRS)  
**Last updated:** 2026-04-09

---

## Purpose

This directory contains notebooks that load, cross-check, and visualise
**Rubin/LSSTCam visit tables** downloaded from the USDF (US Data Facility).

Two independent data sources are used and compared:

| Source | Description |
|--------|-------------|
| **Butler** | Visit registry extracted from the Rubin Butler repository (`dp2_prep`) |
| **consDb** | Consolidated database (`cdb_lsstcam`) queried via `ConsDbClient` |

Both sources provide visit metadata including pointing coordinates (`s_ra`, `s_dec`),
photometric band, observation date (`day_obs`), and sky-map geometry (tract, patch).

---

## Notebooks

### `05_crosscheck_visitTable_vs_constDb.ipynb`

Cross-check between Butler `visitTable` and consDb `visitTable`.

**Workflow:**
1. Load both parquet files from `data_fromlsst/`
2. Auto-detect key columns (visit ID, RA/Dec, band, tract/patch)
3. Compare visit sets (overlap, Butler-only, consDb-only)
4. Verify tract/patch consistency on common visits
5. Build a canonical `visitId → (tract, patch)` lookup table
6. Cross-match Fink diaObject alerts to their tract/patch via visitId
7. Generate the `dataQuery` string for a `bps submit` DRP pipeline job

**Reference notebooks used at USDF:**
- [Butler visit extraction](https://github.com/sylvielsstfr/RubinLSSTDP2Data/blob/main/notebooks/2026-03-25_FindObservationsInButlerRegistryInTractPatch.ipynb)
- [consDb visit extraction](https://github.com/sylvielsstfr/RubinLSSTDP2Data/blob/main/notebooks/2026-03-26_DP2_ConstDB_Butler_LSSTCam_VisitsTractPatch.ipynb)

---

### `06_visitTable_HEALPix_GlobalAndMonthly.ipynb`

HEALPix sky maps of visit counts — global all-time map and month-by-month subplots.

**Workflow:**
1. Load Butler and consDb parquet files; build a canonical merged visit table
2. Parse `day_obs` (YYYYMMDD integer) → `obs_date` + `year_month`
3. **Global HEALPix map**: all visits, all bands, logarithmic colour scale (`YlOrRd`),
   Mollweide projection with Galactic plane trace and DDF `+` markers
4. **Monthly overview grid**: one subplot per calendar month (all-bands combined,
   log scale), laid out chronologically to reveal survey footprint evolution
5. **Per-band monthly panels**: 2×3 grid (u, g, r / i, z, y) per month,
   band-specific colormaps, log scale
6. **Summary bar charts**: grouped and stacked monthly visit counts per band

**HEALPix resolution:** `NSIDE = 64` (pixel size ≈ 0.92 deg), configurable.

**Based on:**
- `05_crosscheck_visitTable_vs_constDb.ipynb` (visit loading & merging logic)
- [`2026-03-10_ConsDB_LSSTCam_HEALPix_Monthly_subplots.ipynb`](https://github.com/sylvielsstfr/RubinLSSTDP2Data/blob/main/notebooks/2026-03-10_ConsDB_LSSTCam_HEALPix_Monthly_subplots.ipynb) (HEALPix mapping & plotting style)

---

## Data

### Input — `data_fromlsst/`

Parquet files downloaded from USDF, containing the merged visit + tract/patch tables:

| File | Source | Rows (approx.) |
|------|--------|----------------|
| `visitTable-2025041500138-2026040500856_N58748_WithTracts.parquet` | Butler | ~58 700 |
| `constDbVisitTable-2025041500043-2026040600288_N93006_WithTracts.parquet` | consDb | ~93 000 |

Both files cover observations from **2025-04-15** onwards.  
Columns include: `visitId` / `visit_id`, `s_ra`, `s_dec`, `band`, `day_obs`, `tract`, `patch`.

### Output — `data_tolsst/`

Text files and query strings generated for use on the USDF DRP pipeline:

| File pattern | Content |
|-------------|---------|
| `diaObj<ID>_tract<N>.txt` | List of visitIds for a given diaObject and tract |
| `dataQuery_diaObj<ID>_tract<N>_patch<P>.txt` | `dataQuery` string for `bps submit` |

---

## Sky-map configuration

- **Instrument:** `LSSTCam`
- **Sky map:** `lsst_cells_v2`
- **DRP pipeline:** `$DRP_PIPE_DIR/pipelines/LSSTCam/DRP.yaml`
- **Butler repo:** `dp2_prep`
- **Collections:** `LSSTCam/runs/DRP/DP2/v30_0_0/DM-53881/stage{1..4}`

---

## Dependencies

| Package | Usage |
|---------|-------|
| `pandas` | Parquet I/O, DataFrame merging |
| `numpy` | Array operations |
| `matplotlib` | Plotting |
| `healpy` | HEALPix map construction and Mollweide projection |
| `astropy` | Coordinate transforms (Galactic → ICRS for Galactic plane trace) |

---

## Related directories

| Directory | Description |
|-----------|-------------|
| `../03_fink_api_blockselections/` | Fink alert light curves and diaObject data |
| `../04_calib/` | Photometric calibration diagnostics and zero-point proxy maps |
