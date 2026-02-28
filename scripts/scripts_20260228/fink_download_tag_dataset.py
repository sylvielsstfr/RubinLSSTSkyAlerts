#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
fink_download_tag_dataset.py
============================

Download Fink LSST alerts for a user-selected tag (filter) and store them
in a structured dataset directory organised by tag name.

Output layout
-------------
fink_dataset/
└── <tag_config>/
    ├── catalog.parquet          # one row per diaObject (latest diaSource metadata)
    ├── light_curves/
    │   └── lc_<diaObjectId>.parquet   # full multi-band light curve per object
    └── cutouts/
        └── cutout_<diaObjectId>.npy   # dict {Science, Template, Difference}

Usage examples
--------------
# List all available tags and quit
python fink_download_tag_dataset.py --list-tags

# Download 50 alerts for the extragalactic new-candidate filter
python fink_download_tag_dataset.py \\
    --tag extragalactic_new_candidate --n 50

# Download 200 SN-near-galaxy alerts into a custom base directory
python fink_download_tag_dataset.py \\
    --tag sn_near_galaxy_candidate --n 200 \\
    --outdir /data/fink_dataset

# Dry-run: show what would be done without writing anything
python fink_download_tag_dataset.py \\
    --tag in_tns --n 20 --dry-run

API reference
-------------
Base URL : https://api.lsst.fink-portal.org/api/v1
Swagger  : https://api.lsst.fink-portal.org/swagger.json

All endpoints accept GET requests with parameters as URL query-string arguments.
Column naming convention:
  r:<name>  — field from the diaSource table (LSST DPDD schema).
               NOTE: the 'r:' prefix is the TABLE name, NOT the r spectral band.
               The spectral band is the VALUE of r:band ∈ {u, g, r, i, z, y}.
  f:<name>  — field computed by Fink (classifiers, cross-matches, etc.)
"""

import argparse
import io
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Fink LSST REST API base URL
# NOTE: This is different from the ZTF portal (fink-portal.org).
#       Always use api.lsst.fink-portal.org for LSST data.
# ---------------------------------------------------------------------------
FINK_API = "https://api.lsst.fink-portal.org/api/v1"

# ---------------------------------------------------------------------------
# Available user-defined tags (Fink LSST filters).
# Keys are the short tag names used by the /tags endpoint.
# ---------------------------------------------------------------------------
FINK_TAGS = {
    "extragalactic_lt20mag_candidate": (
        "Rising, bright (mag < 20), extragalactic candidates"
    ),
    "extragalactic_new_candidate": (
        "New (< 48 h first detection) and potentially extragalactic"
    ),
    "hostless_candidate": (
        "Hostless alerts according to ELEPHANT (arXiv:2404.18165)"
    ),
    "in_tns": (
        "Alerts with a known counterpart in TNS (AT or confirmed)"
    ),
    "sn_near_galaxy_candidate": (
        "Alerts matching a galaxy catalog and consistent with SNe"
    ),
}

# ---------------------------------------------------------------------------
# Columns requested from the /tags endpoint (catalog metadata per alert).
#
# IMPORTANT — column prefix convention:
#   r:<col>  = diaSource table field (LSST DPDD).  The 'r:' is the TABLE prefix,
#              it has nothing to do with the r spectral band of Rubin/LSST.
#   f:<col>  = Fink-computed field (classifiers, cross-matches).
#   The spectral band is the string VALUE of the column r:band ∈ {u,g,r,i,z,y}.
# ---------------------------------------------------------------------------
CATALOG_COLUMNS = ",".join(
    [
        "r:diaObjectId",
        "r:diaSourceId",
        "r:midpointMjdTai",
        "r:ra",
        "r:dec",
        "r:band",
        "r:psfFlux",
        "r:psfFluxErr",
        "r:snr",
        "r:reliability",
        "r:extendedness",
        # Fink classifier scores
        "f:clf_snnSnVsOthers_score",
        "f:clf_earlySNIa_score",
        "f:clf_cats_class",
        "f:clf_cats_score",
        # Cross-matches
        "f:xm_simbad_otype",
        "f:xm_tns_type",
        "f:xm_tns_fullname",
        "f:xm_legacydr8_zphot",
        "f:xm_legacydr8_pstar",
        "f:xm_mangrove_lum_dist",
    ]
)

# ---------------------------------------------------------------------------
# Columns requested for the light-curve endpoint (/sources).
# r:band contains the Rubin spectral band: u, g, r, i, z, or y.
# ---------------------------------------------------------------------------
LC_COLUMNS = ",".join(
    [
        "r:diaObjectId",
        "r:diaSourceId",
        "r:midpointMjdTai",
        "r:band",
        "r:psfFlux",
        "r:psfFluxErr",
        "r:snr",
        "r:reliability",
    ]
)


# ===========================================================================
# Helper functions
# ===========================================================================


def list_tags() -> None:
    """Print all available tag names with descriptions and exit."""
    print("\nAvailable Fink LSST tags (user-defined filters):\n")
    for tag, desc in FINK_TAGS.items():
        print(f"  {tag}")
        print(f"      -> {desc}\n")


def _get(url: str, params: dict, timeout: int = 60) -> requests.Response:
    """
    Perform a GET request and return the response, with basic error reporting.

    Parameters
    ----------
    url : str
        Full endpoint URL.
    params : dict
        Query-string parameters.
    timeout : int
        Request timeout in seconds.

    Returns
    -------
    requests.Response
    """
    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp


def fetch_latest_alerts(tag: str, n: int) -> pd.DataFrame:
    """
    Query the Fink LSST /api/v1/tags endpoint for a given tag.

    The endpoint is GET /tags?tag=<tag>&n=<n>&columns=<cols>&output-format=json
    It returns a JSON array, one element per alert.

    Parameters
    ----------
    tag : str
        Short tag name (key of FINK_TAGS).
    n : int
        Maximum number of alerts to retrieve.

    Returns
    -------
    pd.DataFrame
        One row per alert (latest diaSource per diaObject).
    """
    params = {
        "tag": tag,
        "n": n,
        "columns": CATALOG_COLUMNS,
        "output-format": "json",
    }
    resp = _get(f"{FINK_API}/tags", params, timeout=120)

    if not resp.text.strip():
        return pd.DataFrame()

    try:
        df = pd.read_json(io.BytesIO(resp.content))
    except Exception as exc:
        raise RuntimeError(
            f"Cannot decode JSON from {resp.url}\n"
            f"  status : {resp.status_code}\n"
            f"  body   : {resp.text[:400]!r}"
        ) from exc

    return df


def fetch_light_curve(obj_id: int) -> pd.DataFrame:
    """
    Query the Fink LSST /api/v1/sources endpoint for the full light curve
    of one diaObject (all diaSources in all bands, sorted by MJD).

    Parameters
    ----------
    obj_id : int
        The diaObjectId to query.

    Returns
    -------
    pd.DataFrame
        All diaSources for this object, sorted chronologically.
    """
    params = {
        "diaObjectId": obj_id,
        "columns": LC_COLUMNS,
        "output-format": "json",
    }
    resp = _get(f"{FINK_API}/sources", params, timeout=60)

    if not resp.text.strip():
        return pd.DataFrame()

    try:
        df = pd.read_json(io.BytesIO(resp.content))
    except Exception:
        return pd.DataFrame()

    # Sort chronologically by MJD
    if "r:midpointMjdTai" in df.columns:
        df = df.sort_values("r:midpointMjdTai").reset_index(drop=True)

    return df


def fetch_cutouts(src_id: int) -> dict | None:
    """
    Download the Science, Template, and Difference cutout stamps for a single
    diaSourceId via the Fink LSST /api/v1/cutouts endpoint.

    The endpoint returns a JSON object with one key mapping to a 2-D list
    of float32 values (not raw numpy bytes, unlike the ZTF portal).

    Parameters
    ----------
    src_id : int
        The diaSourceId for which to retrieve cutouts.

    Returns
    -------
    dict with keys 'Science', 'Template', 'Difference', each mapping to a
    2-D numpy float32 array, or None if any request failed.
    """
    cutouts = {}
    for kind in ("Science", "Template", "Difference"):
        params = {
            "diaSourceId": src_id,
            "kind": kind,
            "output-format": "array",
        }
        try:
            resp = _get(f"{FINK_API}/cutouts", params, timeout=30)
            if not resp.content:
                return None
            # The LSST portal returns JSON: {"b:cutout<Kind>": [[...], ...]}
            data = resp.json()
            key = list(data.keys())[0]
            cutouts[kind] = np.array(data[key], dtype=np.float32)
        except Exception as exc:
            print(f"      [warn] cutout {kind} for diaSourceId={src_id}: {exc}")
            return None

    return cutouts


# ===========================================================================
# Main download routine
# ===========================================================================


def download_dataset(
    tag: str,
    n: int,
    outdir: Path,
    retry_delay: float = 0.5,
    dry_run: bool = False,
) -> None:
    """
    Download a complete tagged alert dataset from Fink LSST and save to disk.

    Creates the following layout under *outdir* / *tag* /::

        catalog.parquet
        light_curves/lc_<diaObjectId>.parquet
        cutouts/cutout_<diaObjectId>.npy

    Parameters
    ----------
    tag : str
        Short Fink LSST filter tag name (key of FINK_TAGS).
    n : int
        Number of alerts to fetch.
    outdir : Path
        Base output directory (default: ./fink_dataset).
    retry_delay : float
        Seconds to wait between consecutive API calls (rate-limit safety).
    dry_run : bool
        If True, show what would be done without writing any file.
    """
    # --- Validate tag ---------------------------------------------------------
    if tag not in FINK_TAGS:
        print(f"[error] Unknown tag: '{tag}'")
        print("        Run with --list-tags to see valid options.")
        sys.exit(1)

    # --- Build output directories ---------------------------------------------
    tag_dir = outdir / tag
    lc_dir = tag_dir / "light_curves"
    cutout_dir = tag_dir / "cutouts"

    if dry_run:
        print("[dry-run] Would create directories:")
        print(f"  {tag_dir}")
        print(f"  {lc_dir}")
        print(f"  {cutout_dir}")
    else:
        lc_dir.mkdir(parents=True, exist_ok=True)
        cutout_dir.mkdir(parents=True, exist_ok=True)

    # --- Fetch catalog --------------------------------------------------------
    print(f"\n{'='*62}")
    print(f"  Tag        : {tag}")
    print(f"  N alerts   : {n}")
    print(f"  Output dir : {tag_dir}")
    print(f"{'='*62}\n")

    print(f"[1/3] Fetching up to {n} latest alerts from Fink API ...")
    catalog = fetch_latest_alerts(tag, n)

    if catalog.empty:
        print("[warn] No alerts returned. The tag may have no recent data.")
        return

    # Deduplicate: keep one row per diaObjectId (most recent midpointMjdTai)
    if "r:midpointMjdTai" in catalog.columns:
        catalog = (
            catalog.sort_values("r:midpointMjdTai")
            .drop_duplicates(subset="r:diaObjectId", keep="last")
            .reset_index(drop=True)
        )

    n_objects = len(catalog)
    print(f"      -> {n_objects} unique diaObjects retrieved.\n")

    if not dry_run:
        catalog.to_parquet(tag_dir / "catalog.parquet", index=False)
        print(f"      catalog saved -> {tag_dir / 'catalog.parquet'}")

    # --- Download light curves ------------------------------------------------
    print(f"\n[2/3] Downloading light curves for {n_objects} objects ...")
    lc_ok, lc_skip, lc_fail = 0, 0, 0

    for _, row in catalog.iterrows():
        obj_id = int(row["r:diaObjectId"])
        lc_path = lc_dir / f"lc_{obj_id}.parquet"

        if lc_path.exists():
            lc_skip += 1
            continue

        if dry_run:
            lc_ok += 1
            continue

        try:
            lc_df = fetch_light_curve(obj_id)
            if not lc_df.empty:
                lc_df.to_parquet(lc_path, index=False)
                lc_ok += 1
            else:
                lc_fail += 1
        except Exception as exc:
            print(f"      [warn] lc for diaObjectId={obj_id}: {exc}")
            lc_fail += 1

        time.sleep(retry_delay)

        done = lc_ok + lc_skip + lc_fail
        if done % 20 == 0:
            print(f"      progress: {done}/{n_objects} "
                  f"(ok={lc_ok}, skip={lc_skip}, fail={lc_fail})")

    print(f"      light curves done -- ok={lc_ok}, skip={lc_skip}, fail={lc_fail}")

    # --- Download cutouts -----------------------------------------------------
    print(f"\n[3/3] Downloading cutouts for {n_objects} objects ...")
    cut_ok, cut_skip, cut_fail = 0, 0, 0

    for _, row in catalog.iterrows():
        obj_id = int(row["r:diaObjectId"])
        cutout_path = cutout_dir / f"cutout_{obj_id}.npy"

        if cutout_path.exists():
            cut_skip += 1
            continue

        # Fetch cutouts for the most recent diaSourceId in the catalog
        src_id = int(row["r:diaSourceId"])

        if dry_run:
            cut_ok += 1
            continue

        cutouts = fetch_cutouts(src_id)
        if cutouts is not None:
            # Save as a dict with keys Science/Template/Difference
            np.save(cutout_path, cutouts)
            cut_ok += 1
        else:
            cut_fail += 1

        time.sleep(retry_delay)

        done = cut_ok + cut_skip + cut_fail
        if done % 20 == 0:
            print(f"      progress: {done}/{n_objects} "
                  f"(ok={cut_ok}, skip={cut_skip}, fail={cut_fail})")

    print(f"      cutouts done -- ok={cut_ok}, skip={cut_skip}, fail={cut_fail}")

    # --- Summary --------------------------------------------------------------
    print(f"\n{'='*62}")
    print("  Download complete.")
    print(f"  Tag           : {tag}")
    print(f"  Objects       : {n_objects}")
    print(f"  Light curves  : {lc_ok} saved, {lc_skip} skipped, {lc_fail} failed")
    print(f"  Cutouts       : {cut_ok} saved, {cut_skip} skipped, {cut_fail} failed")
    print(f"  Output        : {tag_dir.resolve()}")
    print(f"{'='*62}\n")


# ===========================================================================
# CLI entry point
# ===========================================================================


def build_parser() -> argparse.ArgumentParser:
    """Build and return the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="fink_download_tag_dataset.py",
        description=(
            "Download Fink LSST alerts (light curves + cutouts) for a chosen\n"
            "tag filter and store them under fink_dataset/<tag>/.\n\n"
            "Output layout:\n"
            "  fink_dataset/<tag>/\n"
            "      catalog.parquet\n"
            "      light_curves/lc_<diaObjectId>.parquet\n"
            "      cutouts/cutout_<diaObjectId>.npy\n\n"
            "Examples:\n"
            "  python fink_download_tag_dataset.py --list-tags\n\n"
            "  python fink_download_tag_dataset.py \\\n"
            "      --tag extragalactic_new_candidate --n 50\n\n"
            "  python fink_download_tag_dataset.py \\\n"
            "      --tag sn_near_galaxy_candidate --n 200 \\\n"
            "      --outdir /data/fink_dataset\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--list-tags",
        action="store_true",
        default=False,
        help="Print all available tag names with descriptions and exit.",
    )
    parser.add_argument(
        "--tag",
        type=str,
        default=None,
        metavar="TAG_CONFIG",
        help="Fink LSST tag to download. Use --list-tags to see valid choices.",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=50,
        metavar="N_PER_TAG",
        help="Number of alerts to fetch for the chosen tag (default: 50).",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("fink_dataset"),
        metavar="DIR",
        help=(
            "Base output directory. A sub-directory named after the tag is\n"
            "created inside it (default: ./fink_dataset)."
        ),
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        metavar="SECONDS",
        help="Delay in seconds between API calls to avoid rate limiting (default: 0.5).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be done without writing any files.",
    )
    return parser


def main() -> None:
    """Parse arguments and run the download."""
    parser = build_parser()
    args = parser.parse_args()

    if args.list_tags:
        list_tags()
        sys.exit(0)

    if args.tag is None:
        parser.print_help()
        print("\n[error] You must specify --tag. Use --list-tags to see options.")
        sys.exit(1)

    if args.n <= 0:
        print(f"[error] --n must be a positive integer, got {args.n}.")
        sys.exit(1)

    download_dataset(
        tag=args.tag,
        n=args.n,
        outdir=args.outdir,
        retry_delay=args.delay,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
