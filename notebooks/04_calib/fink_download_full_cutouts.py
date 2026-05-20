"""
fink_download_full_cutouts.py
==============================
Download ALL cutouts (Science + Template + Difference) AND forced photometry
for a single diaObject, across ALL its diaSources (all observations, all filters).

For a given diaObjectId:
  1. Fetch the complete list of diaSources via /api/v1/sources
  2. For each diaSource (each observation epoch × filter):
       - Download the 3 cutouts (Science, Template, Difference)
       - Save as individual .npy files
  3. Fetch forced photometry (upper limits + detections) via /api/v1/fp
  4. Save:
       - manifest.{csv,parquet}        — diaSource metadata (incl. dipole columns)
       - manifest_fp.{csv,parquet}     — forced photometry table

Output structure:
  fullcutouts_{diaObjectId}/
    manifest.parquet          # all diaSource metadata, time-sorted
    manifest.csv              # same, human-readable
    manifest_fp.parquet       # forced photometry, time-sorted
    manifest_fp.csv           # same, human-readable
    cutouts/
      {diaSourceId}_{band}_Science.npy
      {diaSourceId}_{band}_Template.npy
      {diaSourceId}_{band}_Difference.npy

Column naming convention (LSST DPDD schema):
  - Prefix 'r:' → diaSource / diaObject table field (NOT the spectral band 'r')
  - Prefix 'f:' → Fink-computed field (classifiers, cross-matches)
  - Spectral band → value of column r:band ∈ {u, g, r, i, z, y}

Usage:
  python fink_download_full_cutouts.py --obj_id 170032915988086813
  python fink_download_full_cutouts.py --obj_id 170032915988086813 --outdir ./my_output
  python fink_download_full_cutouts.py --obj_id 170032915988086813 --no_skip

Author : dagoret
Date   : 2026-05
"""

import argparse
import io
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

FINK_API = "https://api.lsst.fink-portal.org/api/v1"

# Columns to fetch for each diaSource (via /api/v1/sources)
COLUMNS_SOURCES = ",".join(
    [
        "r:diaObjectId",
        "r:diaSourceId",
        "r:midpointMjdTai",
        "r:band",
        "r:ra",
        "r:dec",
        "r:target_name",
        "r:psfFlux",
        "r:psfFluxErr",
        "r:snr",
        "r:reliability",
        "r:extendedness",
        "r:psfChi2",
        "r:visit",
        "r:detector",
        "r:x",
        "r:y",
        "r:xErr",
        "r:yErr",
        "r:scienceFlux",
        "r:scienceFluxErr",
        "r:templateFlux",
        "r:templateFluxErr",
        "r:apFlux",
        "r:apFluxErr",
        "r:isDipole",
        "r:isNegative",
        "r:dipoleFitAttempted",
        "r:dipoleFluxDiff",
        "r:dipoleFluxDiffErr",
        "r:dipoleMeanFlux",
        "r:dipoleMeanFluxErr",
        "r:dipoleLength",
        "r:dipoleAngle",
        "r:dipoleNdata",
        "r:dipoleChi2",
        "f:clf_snnSnVsOthers_score",
        "f:clf_earlySNIa_score",
        "f:clf_cats_class",
        "f:clf_cats_score",
        "f:fxm_gaiadr3_DR3Name",
        "f:fxm_gaiadr3_Plx",
        "f:fxm_gaiadr3_VarFlag",
        "f:fxm_gaiadr3_e_Plx",
    ]
)

# Columns to fetch for forced photometry (via /api/v1/fp)
# Mirrors the column set used in 01_fink_block_flatlightcurves.ipynb
COLUMNS_FP = ",".join(
    [
        "r:diaObjectId",
        "r:diaForcedSourceId",
        "r:midpointMjdTai",
        "r:band",
        "r:ra",
        "r:dec",
        "r:psfFlux",
        "r:psfFluxErr",
        "r:visit",
        "r:detector",
        "r:x",
        "r:y",
        "r:forced",
        "r:time_processed",
    ]
)

# Delay between API calls (seconds) — be respectful to the Fink server
SLEEP_BETWEEN_CALLS = 0.2


# ─────────────────────────────────────────────────────────────────────────────
# API helpers
# ─────────────────────────────────────────────────────────────────────────────


def fetch_sources(dia_object_id: int) -> pd.DataFrame:
    """
    Fetch all diaSources for a diaObjectId via /api/v1/sources.
    Parameters
    ----------
    dia_object_id : int
        The diaObjectId for which to fetch diaSources.

    Returns
    -------
    Returns a DataFrame sorted by midpointMjdTai, or empty on failure.
    """
    print(f"  Fetching diaSources for diaObjectId={dia_object_id} ...")
    r = requests.get(
        f"{FINK_API}/sources",
        params={"diaObjectId": dia_object_id, "columns": COLUMNS_SOURCES, "output-format": "json"},
        timeout=60,
    )
    if r.status_code != 200 or not r.text.strip():
        print(f"  ✗ /sources HTTP {r.status_code} — {r.text[:200]}")
        return pd.DataFrame()
    try:
        df = pd.read_json(io.BytesIO(r.content))
    except Exception as e:
        print(f"  ✗ /sources JSON parse error: {e}")
        return pd.DataFrame()
    df = df.sort_values("r:midpointMjdTai").reset_index(drop=True)
    print(f"  ✓ {len(df)} diaSources  bands: {sorted(df['r:band'].unique())}")
    return df


def fetch_fp(dia_object_id: int) -> pd.DataFrame:
    """
    Fetch forced photometry for a diaObjectId via /api/v1/fp.

    Parameters
    ----------
    dia_object_id : int
        The diaObjectId for which to fetch forced photometry.

    Returns
    -------
    Returns a DataFrame sorted by midpointMjdTai, or empty on failure.
    """
    print(f"  Fetching forced photometry for diaObjectId={dia_object_id} ...")
    r = requests.get(
        f"{FINK_API}/fp",
        params={"diaObjectId": dia_object_id, "columns": COLUMNS_FP, "output-format": "json"},
        timeout=60,
    )
    if r.status_code != 200 or not r.text.strip():
        print(f"  ✗ /fp HTTP {r.status_code} — {r.text[:200]}")
        return pd.DataFrame()
    try:
        df = pd.read_json(io.BytesIO(r.content))
    except Exception as e:
        print(f"  ✗ /fp JSON parse error: {e}")
        return pd.DataFrame()
    if df.empty:
        print("  ✓ /fp returned empty table (no forced photometry available)")
        return df
    df = df.sort_values("r:midpointMjdTai").reset_index(drop=True)
    print(f"  ✓ {len(df)} fp points  bands: {sorted(df['r:band'].unique())}")
    return df


def fetch_single_cutout(dia_source_id: int, kind: str) -> np.ndarray | None:
    """
    Fetch one cutout stamp for a diaSourceId.

    Parameters
    ----------
    dia_source_id : int
        The diaSourceId for which to fetch the cutout.
    kind : str — 'Science', 'Template', or 'Difference'
        the type of cutout to fetch.

    Returns
    -------
    np.ndarray of shape (H, W) float32, or None on failure.
    """
    r = requests.get(
        f"{FINK_API}/cutouts",
        params={"diaSourceId": dia_source_id, "kind": kind, "output-format": "array"},
        timeout=30,
    )
    if r.status_code != 200 or not r.content:
        print(f"    ✗ cutout {kind} HTTP {r.status_code} for diaSourceId={dia_source_id}")
        return None
    try:
        data = r.json()
        key = list(data.keys())[0]
        return np.array(data[key], dtype=np.float32)
    except Exception as e:
        print(f"    ✗ cutout {kind} parse error for diaSourceId={dia_source_id}: {e}")
        return None


def fetch_all_cutouts(dia_source_id: int) -> dict[str, np.ndarray] | None:
    """
    Fetch Science, Template, and Difference cutouts for one diaSourceId.

    Parameters
    ----------
    dia_source_id : int
        The diaSourceId for which to fetch cutouts.
    kind : str — 'Science', 'Template', or 'Difference'
        the type of cutout to fetch.

    Returns
    -------
    dict[str, np.ndarray] | None
        A dictionary mapping cutout types  {'Science': arr, 'Template': arr, 'Difference': arr},
    or None if any of the three requests fails.
    """
    cutouts = {}
    for kind in ["Science", "Template", "Difference"]:
        arr = fetch_single_cutout(dia_source_id, kind)
        if arr is None:
            return None
        cutouts[kind] = arr
        time.sleep(SLEEP_BETWEEN_CALLS)
    return cutouts


# ─────────────────────────────────────────────────────────────────────────────
# Main download pipeline
# ─────────────────────────────────────────────────────────────────────────────


def download_full_cutouts(
    dia_object_id: int,
    outdir: Path | None = None,
    skip_existing: bool = True,
) -> Path:
    """
    Download all cutouts AND forced photometry for a diaObjectId.

    Steps
    -----
    1. Fetch all diaSources via /api/v1/sources  →  manifest.{csv,parquet}
    2. For each diaSource fetch the 3 stamps     →  cutouts/*.npy
    3. Fetch forced photometry via /api/v1/fp    →  manifest_fp.{csv,parquet}

    Parameters
    ----------
    dia_object_id : int
        diaObjectId for which to download cutouts and forced photometry.
    outdir        : str, optional —
        Path to the output directory. Defaults to ./fullcutouts_{dia_object_id}/
    skip_existing : bool
        if True, skip diaSources already on disk

    Returns
    -------
    Path — the output directory
    """
    if outdir is None:
        outdir = Path(f"fullcutouts_{dia_object_id}")
    cutout_dir = outdir / "cutouts"
    cutout_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"Downloading cutouts + fp for diaObjectId={dia_object_id}")
    print(f"Output directory : {outdir.resolve()}")
    print(f"{'=' * 60}")

    # ── Step 1: fetch all diaSources ─────────────────────────────────────────
    df_sources = fetch_sources(dia_object_id)
    if df_sources.empty:
        print("  ✗ No diaSources found. Aborting.")
        return outdir

    n_sources = len(df_sources)
    print(f"\n  Processing {n_sources} diaSources ...\n")

    # ── Step 2: download cutout stamps ───────────────────────────────────────
    results = []
    for i, row in df_sources.iterrows():
        src_id = int(row["r:diaSourceId"])
        band = row["r:band"]
        mjd = row["r:midpointMjdTai"]
        snr = row.get("r:snr", float("nan"))

        print(f"  [{i + 1:3d}/{n_sources}]  diaSourceId={src_id}  band={band}  MJD={mjd:.4f}  SNR={snr:.1f}")

        paths = {
            kind: cutout_dir / f"{src_id}_{band}_{kind}.npy" for kind in ["Science", "Template", "Difference"]
        }

        if skip_existing and all(p.exists() for p in paths.values()):
            print("           → already on disk, skipping")
            status = "skipped"
        else:
            cutouts = fetch_all_cutouts(src_id)
            if cutouts is None:
                print("           → ✗ cutout download failed")
                status = "failed"
            else:
                for kind, arr in cutouts.items():
                    np.save(paths[kind], arr)
                h, w = next(iter(cutouts.values())).shape
                print(f"           → ✓ saved  ({h}×{w} pix)")
                status = "ok"

        results.append(
            {
                "r:diaObjectId": dia_object_id,
                "r:diaSourceId": src_id,
                "r:midpointMjdTai": mjd,
                "r:visit": row.get("r:visit"),
                "r:detector": row.get("r:detector"),
                "r:x": row.get("r:x"),
                "r:y": row.get("r:y"),
                "r:xErr": row.get("r:xErr"),
                "r:yErr": row.get("r:yErr"),
                "r:band": band,
                "r:ra": row.get("r:ra"),
                "r:dec": row.get("r:dec"),
                "r:target_name": row.get("r:target_name"),
                "r:psfFlux": row.get("r:psfFlux"),
                "r:psfFluxErr": row.get("r:psfFluxErr"),
                "r:snr": snr,
                "r:reliability": row.get("r:reliability"),
                "r:scienceFlux": row.get("r:scienceFlux"),
                "r:scienceFluxErr": row.get("r:scienceFluxErr"),
                "r:templateFlux": row.get("r:templateFlux"),
                "r:templateFluxErr": row.get("r:templateFluxErr"),
                "r:apFlux": row.get("r:apFlux"),
                "r:apFluxErr": row.get("r:apFluxErr"),
                "r:isDipole": row.get("r:isDipole"),
                "r:isNegative": row.get("r:isNegative"),
                "r:dipoleFitAttempted": row.get("r:dipoleFitAttempted"),
                "r:dipoleFluxDiff": row.get("r:dipoleFluxDiff"),
                "r:dipoleFluxDiffErr": row.get("r:dipoleFluxDiffErr"),
                "r:dipoleMeanFlux": row.get("r:dipoleMeanFlux"),
                "r:dipoleMeanFluxErr": row.get("r:dipoleMeanFluxErr"),
                "r:dipoleLength": row.get("r:dipoleLength"),
                "r:dipoleAngle": row.get("r:dipoleAngle"),
                "r:dipoleNdata": row.get("r:dipoleNdata"),
                "r:dipoleChi2": row.get("r:dipoleChi2"),
                "f:clf_snnSnVsOthers_score": row.get("f:clf_snnSnVsOthers_score"),
                "f:clf_earlySNIa_score": row.get("f:clf_earlySNIa_score"),
                "f:clf_cats_class": row.get("f:clf_cats_class"),
                "f:clf_cats_score": row.get("f:clf_cats_score"),
                "f:fxm_gaiadr3_DR3Name": row.get("f:fxm_gaiadr3_DR3Name"),
                "f:fxm_gaiadr3_Plx": row.get("f:fxm_gaiadr3_Plx"),
                "f:fxm_gaiadr3_VarFlag": row.get("f:fxm_gaiadr3_VarFlag"),
                "f:fxm_gaiadr3_e_Plx": row.get("f:fxm_gaiadr3_e_Plx"),
                "path_Science": str(paths["Science"]),
                "path_Template": str(paths["Template"]),
                "path_Difference": str(paths["Difference"]),
                "status": status,
            }
        )
        time.sleep(SLEEP_BETWEEN_CALLS)

    # ── Step 3: save diaSource manifest ──────────────────────────────────────
    df_manifest = pd.DataFrame(results)
    df_manifest.to_parquet(outdir / "manifest.parquet", index=False)
    df_manifest.to_csv(outdir / "manifest.csv", index=False)
    print(f"\n  manifest saved → {outdir / 'manifest.csv'}")

    # ── Step 4: fetch and save forced photometry ──────────────────────────────
    print()
    df_fp = fetch_fp(dia_object_id)
    if not df_fp.empty:
        df_fp.to_parquet(outdir / "manifest_fp.parquet", index=False)
        df_fp.to_csv(outdir / "manifest_fp.csv", index=False)
        print(f"  manifest_fp saved → {outdir / 'manifest_fp.csv'}")
    else:
        print("  No forced photometry saved (empty response).")

    # ── Summary ───────────────────────────────────────────────────────────────
    n_ok = (df_manifest["status"] == "ok").sum()
    n_skip = (df_manifest["status"] == "skipped").sum()
    n_fail = (df_manifest["status"] == "failed").sum()
    print(f"\n{'=' * 60}")
    print("Done.")
    print(f"  ✓ Cutouts downloaded  : {n_ok}")
    print(f"  → Cutouts skipped     : {n_skip}")
    print(f"  ✗ Cutouts failed      : {n_fail}")
    print(f"  Total diaSources      : {n_sources}")
    if not df_fp.empty:
        print(f"  fp points downloaded  : {len(df_fp)}")
    print("\nBands (diaSources):")
    for band, grp in df_manifest.groupby("r:band"):
        print(f"  {band} : {len(grp):3d} diaSources")
    if not df_fp.empty:
        print("\nBands (forced photometry):")
        for band, grp in df_fp.groupby("r:band"):
            print(f"  {band} : {len(grp):3d} fp points")
    print(f"{'=' * 60}")
    return outdir


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download all cutouts + forced photometry for a single LSST diaObjectId."
    )
    parser.add_argument("--obj_id", type=int, required=True, help="diaObjectId (e.g. 170032915988086813)")
    parser.add_argument(
        "--outdir", type=str, default=None, help="Output directory (default: ./fullcutouts_{obj_id}/)"
    )
    parser.add_argument(
        "--no_skip", action="store_true", help="Re-download even if cutout files already exist"
    )
    args = parser.parse_args()

    download_full_cutouts(
        dia_object_id=args.obj_id,
        outdir=Path(args.outdir) if args.outdir else None,
        skip_existing=not args.no_skip,
    )
