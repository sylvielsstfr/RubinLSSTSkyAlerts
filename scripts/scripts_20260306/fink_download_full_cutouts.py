"""
fink_download_full_cutouts.py
==============================
Download ALL cutouts (Science + Template + Difference) for a single diaObject,
across ALL its diaSources (all observations, all filters).

For a given diaObjectId:
  1. Fetch the complete list of diaSources via /api/v1/sources
  2. For each diaSource (each observation epoch × filter):
       - Download the 3 cutouts (Science, Template, Difference)
       - Save as individual .npy files
  3. Save a manifest CSV with all diaSource metadata

Output structure:
  fullcutouts_{diaObjectId}/
    manifest.parquet          # all diaSource metadata, time-sorted
    manifest.csv              # same, human-readable
    cutouts/
      {diaSourceId}_{band}_Science.npy      # shape (H, W)
      {diaSourceId}_{band}_Template.npy
      {diaSourceId}_{band}_Difference.npy

Column naming convention (LSST DPDD schema):
  - Prefix 'r:' → diaSource table field (NOT the spectral band 'r')
  - Prefix 'f:' → Fink-computed field (classifiers, cross-matches)
  - Spectral band → value of column r:band ∈ {u, g, r, i, z, y}

Usage:
  python fink_download_full_cutouts.py --obj_id 170032915988086813
  python fink_download_full_cutouts.py --obj_id 170032915988086813 --outdir ./my_output

Author : dagoret
Date   : 2026-02
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

# Columns to fetch for each diaSource
COLUMNS_SOURCES = ",".join(
    [
        "r:diaObjectId",
        "r:diaSourceId",
        "r:midpointMjdTai",
        "r:band",
        "r:ra",
        "r:dec",
        "r:psfFlux",
        "r:psfFluxErr",
        "r:snr",
        "r:reliability",
        "r:extendedness",
        "r:visit",
        "r:scienceFlux",
        "r:scienceFluxErr",
        "r:templateFlux",
        "r:templateFluxErr",
        # Fink classifiers (one value per diaSource)
        "f:clf_snnSnVsOthers_score",
        "f:clf_earlySNIa_score",
        "f:clf_cats_class",
        "f:clf_cats_score",
    ]
)

# Delay between API calls to be respectful (seconds)
SLEEP_BETWEEN_CALLS = 0.2

# ─────────────────────────────────────────────────────────────────────────────
# API helpers
# ─────────────────────────────────────────────────────────────────────────────


def fetch_sources(dia_object_id: int) -> pd.DataFrame:
    """
    Fetch all diaSources for a given diaObjectId via /api/v1/sources.
    Returns a DataFrame sorted by midpointMjdTai (ascending).
    """
    print(f"  Fetching diaSources for diaObjectId={dia_object_id} ...")
    r = requests.get(
        f"{FINK_API}/sources",
        params={
            "diaObjectId": dia_object_id,
            "columns": COLUMNS_SOURCES,
            "output-format": "json",
        },
        timeout=60,
    )
    if r.status_code != 200 or not r.text.strip():
        print(f"  ✗ HTTP {r.status_code} — {r.text[:200]}")
        return pd.DataFrame()
    try:
        df = pd.read_json(io.BytesIO(r.content))
    except Exception as e:
        print(f"  ✗ JSON parse error: {e}")
        return pd.DataFrame()

    df = df.sort_values("r:midpointMjdTai").reset_index(drop=True)
    print(f"  ✓ {len(df)} diaSources found across bands: " f"{sorted(df['r:band'].unique())}")
    return df


def fetch_single_cutout(dia_source_id: int, kind: str) -> np.ndarray | None:
    """
    Fetch one cutout (Science | Template | Difference) for a diaSourceId.

    The Fink LSST API returns a JSON object with a single key whose value
    is a 2D list of float32 pixel values.

    Parameters
    ----------
    dia_source_id : int
    kind : str — 'Science', 'Template', or 'Difference'

    Returns
    -------
    np.ndarray of shape (H, W) dtype float32, or None on failure.
    """
    r = requests.get(
        f"{FINK_API}/cutouts",
        params={
            "diaSourceId": dia_source_id,
            "kind": kind,
            "output-format": "array",
        },
        timeout=30,
    )
    if r.status_code != 200 or not r.content:
        return None
    try:
        data = r.json()
        key = list(data.keys())[0]  # e.g. "b:cutoutScience"
        return np.array(data[key], dtype=np.float32)
    except Exception as e:
        print(f"    ✗ cutout {kind} parse error for diaSourceId={dia_source_id}: {e}")
        return None


def fetch_all_cutouts(dia_source_id: int) -> dict[str, np.ndarray] | None:
    """
    Fetch Science, Template and Difference cutouts for one diaSourceId.

    Returns
    -------
    dict {'Science': array, 'Template': array, 'Difference': array}
    or None if any cutout fails.
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
    Download all cutouts for a diaObjectId across all diaSources and bands.

    Parameters
    ----------
    dia_object_id : int
        The LSST diaObjectId to process.
    outdir : Path, optional
        Root output directory. Defaults to ./fullcutouts_{dia_object_id}/
    skip_existing : bool
        If True, skip diaSources whose cutout files already exist on disk.

    Returns
    -------
    Path to the output directory.
    """
    if outdir is None:
        outdir = Path(f"fullcutouts_{dia_object_id}")

    cutout_dir = outdir / "cutouts"
    cutout_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Downloading full cutouts for diaObjectId={dia_object_id}")
    print(f"Output directory : {outdir.resolve()}")
    print(f"{'='*60}")

    # ── Step 1: fetch all diaSources ─────────────────────────────────────────
    df_sources = fetch_sources(dia_object_id)
    if df_sources.empty:
        print("  ✗ No diaSources found. Aborting.")
        return outdir

    n_sources = len(df_sources)
    print(f"\n  Processing {n_sources} diaSources ...\n")

    # ── Step 2: download cutouts for each diaSource ───────────────────────────
    results = []  # list of dicts for the manifest

    for i, row in df_sources.iterrows():
        src_id = int(row["r:diaSourceId"])
        band = row["r:band"]
        mjd = row["r:midpointMjdTai"]
        snr = row.get("r:snr", float("nan"))

        print(
            f"  [{i+1:3d}/{n_sources}]  diaSourceId={src_id}  " f"band={band}  MJD={mjd:.4f}  SNR={snr:.1f}"
        )

        # Check if all 3 cutout files already exist
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
                "r:band": band,
                "r:ra": row.get("r:ra"),
                "r:dec": row.get("r:dec"),
                "r:psfFlux": row.get("r:psfFlux"),
                "r:psfFluxErr": row.get("r:psfFluxErr"),
                "r:snr": snr,
                "r:reliability": row.get("r:reliability"),
                "r:scienceFlux": row.get("r:scienceFlux"),
                "r:templateFlux": row.get("r:templateFlux"),
                "f:clf_snnSnVsOthers_score": row.get("f:clf_snnSnVsOthers_score"),
                "f:clf_earlySNIa_score": row.get("f:clf_earlySNIa_score"),
                "path_Science": str(paths["Science"]),
                "path_Template": str(paths["Template"]),
                "path_Difference": str(paths["Difference"]),
                "status": status,
            }
        )

    # ── Step 3: save manifest ─────────────────────────────────────────────────
    df_manifest = pd.DataFrame(results)
    df_manifest.to_parquet(outdir / "manifest.parquet", index=False)
    df_manifest.to_csv(outdir / "manifest.csv", index=False)

    # ── Summary ───────────────────────────────────────────────────────────────
    n_ok = (df_manifest["status"] == "ok").sum()
    n_skip = (df_manifest["status"] == "skipped").sum()
    n_fail = (df_manifest["status"] == "failed").sum()
    print(f"\n{'='*60}")
    print("Done.")
    print(f"  ✓ Downloaded : {n_ok}")
    print(f"  → Skipped    : {n_skip}")
    print(f"  ✗ Failed     : {n_fail}")
    print(f"  Total        : {n_sources}")
    print("\nBands observed:")
    for band, grp in df_manifest.groupby("r:band"):
        print(f"  {band} : {len(grp)} diaSources")
    print("\nManifest saved:")
    print(f"  {outdir / 'manifest.parquet'}")
    print(f"  {outdir / 'manifest.csv'}")
    print(f"{'='*60}")

    return outdir


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download all cutouts for a single LSST diaObjectId.")
    parser.add_argument(
        "--obj_id",
        type=int,
        required=True,
        help="diaObjectId to download (e.g. 170032915988086813)",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default=None,
        help="Output directory (default: ./fullcutouts_{obj_id}/)",
    )
    parser.add_argument(
        "--no_skip",
        action="store_true",
        help="Re-download even if cutout files already exist",
    )
    args = parser.parse_args()

    download_full_cutouts(
        dia_object_id=args.obj_id,
        outdir=Path(args.outdir) if args.outdir else None,
        skip_existing=not args.no_skip,
    )
