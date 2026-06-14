"""
fink_download_full_cutouts_fits.py
====================================
Download ALL cutouts (Science + Template + Difference) AND forced photometry
for a single diaObject, across ALL its diaSources (all observations, all filters).

Cutouts are saved as FITS files with full WCS and FITS header metadata,
unlike the original fink_download_full_cutouts.py which saved raw .npy arrays.

For a given diaObjectId:
  1. Fetch the complete list of diaSources via /api/v1/sources
  2. For each diaSource (each observation epoch × filter):
       - Download the 3 cutouts as FITS (Science, Template, Difference)
       - Inject diaSource metadata (ra, dec, visit, band, MJD, dipole columns, …)
         into the primary FITS header of each file
  3. Fetch forced photometry (upper limits + detections) via /api/v1/fp
  4. Save:
       - manifest.{csv,parquet}        — diaSource metadata (incl. dipole columns)
       - manifest_fp.{csv,parquet}     — forced photometry table

Output structure:
  fullcutouts_fits_{diaObjectId}/
    manifest.parquet          # all diaSource metadata, time-sorted
    manifest.csv              # same, human-readable
    manifest_fp.parquet       # forced photometry, time-sorted
    manifest_fp.csv           # same, human-readable
    cutouts/
      {diaSourceId}_{band}_Science.fits
      {diaSourceId}_{band}_Template.fits
      {diaSourceId}_{band}_Difference.fits

FITS header convention:
  Each FITS file contains (at minimum):
    - Extension 0 (PRIMARY): the cutout image array with WCS keywords
    - Standard WCS keywords: CTYPE1/2, CRPIX1/2, CRVAL1/2, CD1_1/CD2_2 (if available)
    - Custom keywords injected from the diaSource manifest:
        OBJID    → r:diaObjectId
        SRCID    → r:diaSourceId
        MJD-OBS  → r:midpointMjdTai  [MJD, TAI]  (standard FITS keyword)
        TIMESYS  → 'TAI'
        DATE-OBS → UTC ISO string derived from midpointMjdTai
        BAND     → r:band
        RA_SRC   → r:ra  (source RA, deg)
        DEC_SRC  → r:dec (source Dec, deg)
        VISIT    → r:visit
        DETNUM   → r:detector
        SNR      → r:snr
        PSFFLUX  → r:psfFlux
        PSFFLXER → r:psfFluxErr
        ISDIPOLE → r:isDipole
        DIPLEN   → r:dipoleLength
        DIPANG   → r:dipoleAngle
        DIPPA    → Dipole direction toward zenith = r:dipoleAngle (CCW from East pixel axis)
        CUTTYPE  → kind ('Science', 'Template', 'Difference')
        OBS-LAT  → RUBIN_LAT_DEG  (notebook convention, used by plot_cutout_wcs_with_directions)
        OBS-LONG → RUBIN_LON_DEG
        OBS-ELEV → RUBIN_HEIGHT_M

Column naming convention (LSST DPDD schema):
  - Prefix 'r:' → diaSource / diaObject table field (NOT the spectral band 'r')
  - Prefix 'f:' → Fink-computed field (classifiers, cross-matches)
  - Spectral band → value of column r:band ∈ {u, g, r, i, z, y}

Usage:
  python fink_download_full_cutouts_fits.py --obj_id 170032915988086813
  python fink_download_full_cutouts_fits.py --obj_id 170032915988086813 --outdir ./my_output
  python fink_download_full_cutouts_fits.py --obj_id 170032915988086813 --no_skip
  python fink_download_full_cutouts_fits.py --obj_id 170032915988086813 --mjd_min 60800.0
  python fink_download_full_cutouts_fits.py --obj_id 170032915988086813 --mjd_min 60800.0 --mjd_max 60900.0

Dependencies:
  pip install astropy requests pandas pyarrow

Author : dagoret
Date   : 2026-06
"""

import argparse
import io
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from astropy.io import fits
from astropy.time import Time

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

FINK_API = "https://api.lsst.fink-portal.org/api/v1"

# Rubin Observatory site constants
RUBIN_LAT_DEG = -30.244728
RUBIN_LON_DEG = -70.749417
RUBIN_HEIGHT_M = 2647.0

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

# FITS cutout output-format string accepted by the Fink API
FINK_FITS_FORMAT = "FITS"

MISSING = -9999.0

# Flags for WCS adds
FLAG_SET_CTYPE = True
FLAG_SET_CUNIT = True
FLAG_SET_CRPIX = True
FLAG_SET_CRVAL = True
FLAG_SET_WCSAXES = True


# ─────────────────────────────────────────────────────────────────────────────
# API helpers
# ─────────────────────────────────────────────────────────────────────────────


def safe_float(x):
    """
    Sanitize floats againts nan/inf values which cannot be stored
    in FITS headers. Returns None if x is not a finite float.

    Args:
        x (float): The float value to sanitize.

    Returns:
        float or None: The sanitized float value or None if it's not a finite float.
    """
    try:
        val = float(x)
        return val if np.isfinite(val) else None
    except (TypeError, ValueError):
        return None


def fetch_sources(dia_object_id: int) -> pd.DataFrame:
    """
    Fetch all diaSources for a diaObjectId via /api/v1/sources.

    Parameters
    ----------
    dia_object_id : int
        The diaObjectId for which to fetch diaSources.

    Returns
    -------
    pd.DataFrame
        DataFrame sorted by midpointMjdTai, or empty on failure.
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
    pd.DataFrame
        DataFrame sorted by midpointMjdTai, or empty on failure.
    """
    print(f"  Fetching forced photometry for diaObjectId={dia_object_id} ...")
    r = requests.get(
        f"{FINK_API}/fp",
        params={
            "diaObjectId": dia_object_id,
            "columns": COLUMNS_FP,
            "output-format": "json",
        },
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


def fetch_single_cutout_fits(dia_source_id: int, kind: str) -> fits.HDUList | None:
    """
    Fetch one cutout stamp for a diaSourceId as a FITS HDUList.

    The Fink API /api/v1/cutouts endpoint supports output-format='fits',
    which returns the raw FITS bytes including the WCS information embedded
    by the LSST Science Pipelines during image processing.

    Parameters
    ----------
    dia_source_id : int
        The diaSourceId for which to fetch the cutout.
    kind : str
        Type of cutout: 'Science', 'Template', or 'Difference'.

    Returns
    -------
    fits.HDUList or None
        Parsed FITS HDUList (with WCS header intact), or None on failure.
    """
    r = requests.get(
        f"{FINK_API}/cutouts",
        params={
            "diaSourceId": dia_source_id,
            "kind": kind,
            "output-format": FINK_FITS_FORMAT,
        },
        timeout=30,
    )
    if r.status_code != 200 or not r.content:
        print(f"    ✗ cutout {kind} (FITS) HTTP {r.status_code} for diaSourceId={dia_source_id}")
        return None
    try:
        hdul = fits.open(io.BytesIO(r.content))
        return hdul
    except Exception as e:
        print(f"    ✗ cutout {kind} FITS parse error for diaSourceId={dia_source_id}: {e}")
        return None


def _ensure_wcs_keywords(hdr: fits.Header, ra_deg: float | None, dec_deg: float | None) -> None:
    """
    Ensure that the minimal set of WCS keywords required for a valid TAN projection
    is present in a FITS header.

    The Fink API returns cutout FITS files that contain CRPIX, CRVAL, and a CD
    matrix, but frequently omit CTYPE1/2 and CUNIT1/2.  Without these two pairs
    astropy.wcs.WCS cannot determine the projection or the angular units and
    silently falls back to a degenerate (pixel-only) WCS.

    This function fills in the missing keywords **only if they are absent**,
    so it never overwrites values that were already set by the pipeline.

    Conventions applied
    -------------------
    * CTYPE1 = 'RA---TAN'  /  CTYPE2 = 'DEC--TAN'   (gnomonic projection, ICRS)
    * CUNIT1 = 'deg'       /  CUNIT2 = 'deg'
    * CRVAL1/CRVAL2 are set from the diaSource RA/Dec when absent.
    * CRPIX1/CRPIX2 are set to the image centre when absent.
    * WCSAXES = 2  is added when absent.

    Parameters
    ----------
    hdr : fits.Header
        The primary FITS header to patch (modified in place).
    ra_deg : float or None
        RA of the diaSource in degrees (ICRS), used as CRVAL1 fallback.
    dec_deg : float or None
        Dec of the diaSource in degrees (ICRS), used as CRVAL2 fallback.
    """

    # ── Projection type ───────────────────────────────────────────────────────
    if FLAG_SET_CTYPE:
        if "CTYPE1" not in hdr:
            hdr["CTYPE1"] = ("RA---TAN", "Right ascension, gnomonic projection")
        if "CTYPE2" not in hdr:
            hdr["CTYPE2"] = ("DEC--TAN", "Declination, gnomonic projection")

    # ── Angular units ─────────────────────────────────────────────────────────
    if FLAG_SET_CUNIT:
        if "CUNIT1" not in hdr:
            hdr["CUNIT1"] = ("deg", "WCS axis 1 unit")
        if "CUNIT2" not in hdr:
            hdr["CUNIT2"] = ("deg", "WCS axis 2 unit")

    # ── Reference pixel (centre of stamp when absent) ─────────────────────────
    if FLAG_SET_CRPIX:
        if "CRPIX1" not in hdr:
            naxis1 = hdr.get("NAXIS1", None)
            hdr["CRPIX1"] = ((naxis1 + 1) / 2.0 if naxis1 else 1.0, "[pix] Reference pixel axis 1")
        if "CRPIX2" not in hdr:
            naxis2 = hdr.get("NAXIS2", None)
            hdr["CRPIX2"] = ((naxis2 + 1) / 2.0 if naxis2 else 1.0, "[pix] Reference pixel axis 2")

    # ── Reference sky coordinates ─────────────────────────────────────────────
    if FLAG_SET_CRVAL:
        if "CRVAL1" not in hdr and ra_deg is not None:
            hdr["CRVAL1"] = (float(ra_deg), "[deg] RA at reference pixel")
        if "CRVAL2" not in hdr and dec_deg is not None:
            hdr["CRVAL2"] = (float(dec_deg), "[deg] Dec at reference pixel")

    # ── Number of WCS axes ────────────────────────────────────────────────────
    if FLAG_SET_WCSAXES and "WCSAXES" not in hdr:
        # if "WCSAXES" not in hdr:
        hdr["WCSAXES"] = (2, "Number of WCS axes")


def inject_diasource_metadata(hdul: fits.HDUList, row: pd.Series, kind: str) -> fits.HDUList:
    """
    Inject diaSource metadata keywords into the primary FITS header.

    The original FITS header from the Fink API already contains WCS
    (CRPIX, CRVAL, CD matrix, CTYPE) for the cutout sub-image. This function
    adds custom COMMENT and keyword entries with diaSource provenance information
    (object ID, source ID, band, MJD, RA/Dec, dipole columns, etc.) without
    overwriting existing WCS keywords.

    Parameters
    ----------
    hdul : fits.HDUList
        The FITS object returned by the Fink API.
    row : pd.Series
        A single row from the diaSource manifest DataFrame.
    kind : str
        Cutout type ('Science', 'Template', 'Difference').

    Returns
    -------
    fits.HDUList
        The modified HDUList with injected metadata.
    """
    hdr = hdul[0].header

    # ── WCS completeness check ───────────────────────────────────────────────
    # Fink cutouts often lack CTYPE1/2 and CUNIT1/2; patch them before
    # any downstream astropy.wcs.WCS call would silently degrade.
    _ra = row.get("r:ra", None)
    _dec = row.get("r:dec", None)
    _ensure_wcs_keywords(
        hdr,
        ra_deg=float(_ra) if _ra is not None and not (isinstance(_ra, float) and np.isnan(_ra)) else None,
        dec_deg=float(_dec)
        if _dec is not None and not (isinstance(_dec, float) and np.isnan(_dec))
        else None,
    )

    # ── Provenance / identification ──────────────────────────────────────────
    hdr["CUTTYPE"] = (kind, "Cutout type: Science / Template / Difference")
    hdr["OBJID"] = (int(row.get("r:diaObjectId", -1)), "LSST diaObjectId")
    hdr["SRCID"] = (int(row.get("r:diaSourceId", -1)), "LSST diaSourceId")
    # MJD-OBS (standard keyword) is injected below at the observatory block
    hdr["BAND"] = (str(row.get("r:band", "")), "LSST photometric band {u,g,r,i,z,y}")
    hdr["VISIT"] = (int(row.get("r:visit", -1)), "Rubin visit identifier")
    hdr["DETNUM"] = (int(row.get("r:detector", -1)), "Rubin detector number")
    hdr["TARGET"] = (str(row.get("r:target_name", "")), "Deep Drilling Field or target name")

    # ── Sky coordinates of the diaSource ────────────────────────────────────
    hdr["RA_SRC"] = (safe_float(row.get("r:ra")), "[deg] diaSource RA (ICRS)")
    hdr["DEC_SRC"] = (safe_float(row.get("r:dec")), "[deg] diaSource Dec (ICRS)")

    # ── Pixel coordinates on the detector ───────────────────────────────────
    hdr["X_PIX"] = (safe_float(row.get("r:x")), "[pix] diaSource x on detector")
    hdr["Y_PIX"] = (safe_float(row.get("r:y")), "[pix] diaSource y on detector")
    hdr["X_PIXERR"] = (safe_float(row.get("r:xErr")), "[pix] uncertainty on x")
    hdr["Y_PIXERR"] = (safe_float(row.get("r:yErr")), "[pix] uncertainty on y")

    # ── Photometry ───────────────────────────────────────────────────────────
    hdr["SNR"] = (safe_float(row.get("r:snr")), "Signal-to-noise ratio (psfFlux / psfFluxErr)")
    hdr["PSFFLUX"] = (safe_float(row.get("r:psfFlux")), "[nJy] PSF flux")
    hdr["PSFFLXER"] = (safe_float(row.get("r:psfFluxErr")), "[nJy] PSF flux uncertainty")
    hdr["SCIFLUX"] = (safe_float(row.get("r:scienceFlux")), "[nJy] Science image flux")
    hdr["SCIFLERR"] = (safe_float(row.get("r:scienceFluxErr")), "[nJy] Science flux uncertainty")
    hdr["TPLFLUX"] = (safe_float(row.get("r:templateFlux")), "[nJy] Template image flux")
    hdr["TPLFLERR"] = (safe_float(row.get("r:templateFluxErr")), "[nJy] Template flux uncertainty")
    hdr["APFLUX"] = (safe_float(row.get("r:apFlux")), "[nJy] Aperture flux")
    hdr["APFLERR"] = (safe_float(row.get("r:apFluxErr")), "[nJy] Aperture flux uncertainty")
    hdr["PSFCHI2"] = (safe_float(row.get("r:psfChi2")), "PSF chi2 of source fit")
    hdr["RELIAB"] = (safe_float(row.get("r:reliability")), "Source reliability score [0,1]")
    hdr["EXTENDNS"] = (safe_float(row.get("r:extendedness")), "Extendedness flag [0=stellar,1=extended]")

    # ── Dipole columns ───────────────────────────────────────────────────────
    isdipole = row.get("r:isDipole", None)
    hdr["ISDIPOLE"] = (
        bool(isdipole) if isdipole is not None else False,
        "True if classified as a dipole artifact",
    )
    hdr["ISNEG"] = (bool(row.get("r:isNegative", False)), "True if source is negative (below template)")
    hdr["DIPFIT"] = (bool(row.get("r:dipoleFitAttempted", False)), "True if dipole fit was attempted")
    hdr["DIPLEN"] = (safe_float(row.get("r:dipoleLength")), "[arcsec] Dipole length (lobe separation)")
    hdr["DIPANG"] = (safe_float(row.get("r:dipoleAngle")), "[deg]    Dipole angle from dipoleFitter")
    # Dipole direction in principle should align toward the zenith.
    # r:dipoleAngle is measured relative to the Nort  axis in the tangent plahne.
    # It directly tracks the parallactic angle η (notebook 05b confirms r:dipoleAngle ≈ η),
    # which IS the direction from the source toward the zenith projected onto the sky.
    # No conversion is needed: DIPPA == r:dipoleAngle.
    # (The old formula (90 − dipoleAngle) % 360 was a misguided conversion to
    #  astronomical North-up PA convention and is physically wrong here.)
    raw_ang = row.get("r:dipoleAngle", None)
    if raw_ang is not None and not np.isnan(float(raw_ang)):
        hdr["DIPPA"] = (float(raw_ang) % 360.0, "[deg] Dipole dir toward zenith = r:dipoleAngle (CCW from E)")
    hdr["DIPFDIF"] = (safe_float(row.get("r:dipoleFluxDiff")), "[nJy] Dipole flux difference")
    hdr["DIPFDIFE"] = (
        safe_float(row.get("r:dipoleFluxDiffErr")),
        "[nJy] Dipole flux difference uncertainty",
    )
    hdr["DIPFMEAN"] = (safe_float(row.get("r:dipoleMeanFlux")), "[nJy] Dipole mean flux")
    hdr["DIPFMNER"] = (
        safe_float(row.get("r:dipoleMeanFluxErr")),
        "[nJy] Dipole mean flux uncertainty",
    )
    hdr["DIPNDATA"] = (int(row.get("r:dipoleNdata", -1)), "Number of pixels in dipole fit")
    hdr["DIPCHI2"] = (safe_float(row.get("r:dipoleChi2")), "Chi2 of dipole fit")

    # ── Fink classifier scores ───────────────────────────────────────────────
    hdr["SNN_SNVA"] = (
        safe_float(row.get("f:clf_snnSnVsOthers_score")),
        "Fink SNN SN-vs-Others score",
    )
    hdr["ESNIASC"] = (safe_float(row.get("f:clf_earlySNIa_score")), "Fink early SNIa score")
    hdr["CATSCLS"] = (str(row.get("f:clf_cats_class", "")), "Fink CATS classifier class")
    hdr["CATSSC"] = (safe_float(row.get("f:clf_cats_score")), "Fink CATS classifier score")

    # ── Gaia DR3 cross-match ─────────────────────────────────────────────────
    hdr["GAIANAME"] = (str(row.get("f:fxm_gaiadr3_DR3Name")), "Gaia DR3 source name (cross-match)")
    hdr["GAIAPLX"] = (safe_float(row.get("f:fxm_gaiadr3_Plx")), "[mas] Gaia DR3 parallax")
    hdr["GAIAEPLX"] = (
        safe_float(row.get("f:fxm_gaiadr3_e_Plx")),
        "[mas] Gaia DR3 parallax uncertainty",
    )
    gaia_vf = row.get("f:fxm_gaiadr3_VarFlag", None)
    hdr["GAIAVRFL"] = (str(gaia_vf) if gaia_vf is not None else "", "Gaia DR3 variability flag")

    # ── Observation time keywords (standard + notebook convention) ─────────────
    mjd_val = float(row.get("r:midpointMjdTai", float("nan")))
    if np.isfinite(mjd_val):
        obstime = Time(mjd_val, format="mjd", scale="tai")
        hdr["MJD-OBS"] = (mjd_val, "Observation midpoint [MJD, TAI]")
        hdr["TIMESYS"] = ("TAI", "Time system")
        hdr["DATE-OBS"] = (obstime.utc.isot, "UTC ISO observation time")
        hdr.add_comment("Time keywords from Fink r:midpointMjdTai")

    # ── Observatory metadata (OBS-LAT/LONG/ELEV matches notebook convention) ──
    hdr["TELESCOP"] = ("Rubin LSST", "Telescope name")
    hdr["OBS-LAT"] = (RUBIN_LAT_DEG, "[deg] Observatory geodetic latitude")
    hdr["OBS-LONG"] = (RUBIN_LON_DEG, "[deg] Observatory east longitude")
    hdr["OBS-ELEV"] = (RUBIN_HEIGHT_M, "[m]   Observatory altitude above sea level")

    # hdr.add_comment("LSST diaSource cutout with WCS and dipole metadata — fink_download_full_cutouts_fits.py")
    hdr.add_comment("fink_download_full_cutouts_fits.py")

    return hdul


def fetch_all_cutouts_fits(dia_source_id: int, row: pd.Series) -> dict[str, fits.HDUList] | None:
    """
    Fetch Science, Template, and Difference cutouts as FITS for one diaSourceId.

    Injects diaSource metadata into each FITS header after download.

    Parameters
    ----------
    dia_source_id : int
        The diaSourceId for which to fetch cutouts.
    row : pd.Series
        The diaSource manifest row (metadata to embed in FITS headers).

    Returns
    -------
    dict[str, fits.HDUList] or None
        {'Science': hdul, 'Template': hdul, 'Difference': hdul},
        or None if any of the three requests fails.
    """
    cutouts = {}
    for kind in ["Science", "Template", "Difference"]:
        hdul = fetch_single_cutout_fits(dia_source_id, kind)
        if hdul is None:
            return None
        hdul = inject_diasource_metadata(hdul, row, kind)
        cutouts[kind] = hdul
        time.sleep(SLEEP_BETWEEN_CALLS)
    return cutouts


# ─────────────────────────────────────────────────────────────────────────────
# Main download pipeline
# ─────────────────────────────────────────────────────────────────────────────


def download_full_cutouts_fits(
    dia_object_id: int,
    outdir: Path | None = None,
    skip_existing: bool = True,
    mjd_min: float | None = None,
    mjd_max: float | None = None,
) -> Path:
    """
    Download all cutouts (FITS format with WCS) + forced photometry for a diaObjectId.

    Steps
    -----
    1. Fetch all diaSources via /api/v1/sources  →  manifest.{csv,parquet}
    2. (Optional) Filter diaSources by MJD range [mjd_min, mjd_max]
    3. For each retained diaSource fetch the 3 stamps as FITS  →  cutouts/*.fits
       (WCS keywords preserved; diaSource metadata injected in PRIMARY header)
    4. Fetch forced photometry via /api/v1/fp    →  manifest_fp.{csv,parquet}

    Parameters
    ----------
    dia_object_id : int
        diaObjectId for which to download cutouts and forced photometry.
    outdir : Path, optional
        Output directory. Defaults to ./fullcutouts_fits_{dia_object_id}/
    skip_existing : bool
        If True, skip diaSources whose .fits files already exist on disk.
    mjd_min : float, optional
        If provided, only download diaSources with midpointMjdTai >= mjd_min.
    mjd_max : float, optional
        If provided, only download diaSources with midpointMjdTai <= mjd_max.

    Returns
    -------
    Path
        The output directory.
    """
    if outdir is None:
        outdir = Path(f"fullcutouts_fits_{dia_object_id}")
    cutout_dir = outdir / "cutouts"
    cutout_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"Downloading FITS cutouts + fp for diaObjectId={dia_object_id}")
    print(f"Output directory : {outdir.resolve()}")
    if mjd_min is not None or mjd_max is not None:
        lo = f"{mjd_min:.4f}" if mjd_min is not None else "-∞"
        hi = f"{mjd_max:.4f}" if mjd_max is not None else "+∞"
        print(f"MJD filter       : [{lo},  {hi}]")
    print(f"{'=' * 60}")

    # ── Step 1: fetch all diaSources ─────────────────────────────────────────
    df_sources = fetch_sources(dia_object_id)
    if df_sources.empty:
        print("  ✗ No diaSources found. Aborting.")
        return outdir

    n_total = len(df_sources)

    # ── Step 2: filter by MJD range ──────────────────────────────────────────
    if mjd_min is not None or mjd_max is not None:
        mask = pd.Series([True] * n_total, index=df_sources.index)
        if mjd_min is not None:
            mask &= df_sources["r:midpointMjdTai"] >= mjd_min
        if mjd_max is not None:
            mask &= df_sources["r:midpointMjdTai"] <= mjd_max
        n_filtered_out = (~mask).sum()
        df_sources = df_sources[mask].reset_index(drop=True)
        print(
            f"\n  MJD filter: {n_total} total diaSources → {len(df_sources)} kept, {n_filtered_out} skipped"
        )
        if df_sources.empty:
            print("  ✗ No diaSources remain after MJD filtering. Aborting.")
            return outdir

    n_sources = len(df_sources)
    print(f"\n  Processing {n_sources} diaSources ...\n")

    # ── Step 3: download FITS cutout stamps ──────────────────────────────────
    results = []
    # loop on row containing source info
    for i, row in df_sources.iterrows():
        src_id = int(row["r:diaSourceId"])
        band = row["r:band"]
        mjd = row["r:midpointMjdTai"]
        snr = row.get("r:snr", float("nan"))

        print(f"  [{i + 1:3d}/{n_sources}]  diaSourceId={src_id}  band={band}  MJD={mjd:.4f}  SNR={snr:.1f}")

        paths = {
            kind: cutout_dir / f"{src_id}_{band}_{kind}.fits"
            for kind in ["Science", "Template", "Difference"]
        }

        if skip_existing and all(p.exists() for p in paths.values()):
            print("           → already on disk, skipping")
            status = "skipped"
            # Retrieve shape info from existing file for the manifest
            try:
                with fits.open(paths["Science"]) as hdul_ex:
                    h, w = hdul_ex[0].data.shape[-2], hdul_ex[0].data.shape[-1]
                shape_str = f"{h}×{w}"
            except Exception:
                shape_str = "unknown"
        else:
            cutouts = fetch_all_cutouts_fits(src_id, row)
            if cutouts is None:
                print("           → ✗ cutout download failed")
                status = "failed"
                shape_str = "n/a"
            else:
                for kind, hdul in cutouts.items():
                    hdul.writeto(paths[kind], overwrite=True)
                    hdul.close()
                # Get image shape from Science cutout just saved
                try:
                    with fits.open(paths["Science"]) as hdul_ex:
                        h, w = hdul_ex[0].data.shape[-2], hdul_ex[0].data.shape[-1]
                    shape_str = f"{h}×{w}"
                except Exception:
                    shape_str = "unknown"
                print(f"           → ✓ saved FITS  ({shape_str} pix)")
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

    # ── Step 4: save diaSource manifest ──────────────────────────────────────
    df_manifest = pd.DataFrame(results)
    df_manifest.to_parquet(outdir / "manifest_src.parquet", index=False)
    df_manifest.to_csv(outdir / "manifest_src.csv", index=False)
    print(f"\n  manifest saved → {outdir / 'manifest_src.csv'}")

    # ── Step 5: fetch and save forced photometry ──────────────────────────────
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
    print(f"  ✓ FITS cutouts downloaded : {n_ok}")
    print(f"  → FITS cutouts skipped    : {n_skip}")
    print(f"  ✗ FITS cutouts failed     : {n_fail}")
    print(f"  Total diaSources          : {n_sources}  (out of {n_total} fetched)")
    if not df_fp.empty:
        print(f"  fp points downloaded      : {len(df_fp)}")
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
        description=(
            "Download all FITS cutouts (with WCS) + forced photometry "
            "for a single LSST diaObjectId via the Fink broker API."
        )
    )
    parser.add_argument("--obj_id", type=int, required=True, help="diaObjectId (e.g. 170032915988086813)")
    parser.add_argument(
        "--outdir", type=str, default=None, help="Output directory (default: ./fullcutouts_fits_{obj_id}/)"
    )
    parser.add_argument(
        "--no_skip", action="store_true", help="Re-download even if FITS cutout files already exist"
    )
    parser.add_argument(
        "--mjd_min", type=float, default=None, help="Only download diaSources with midpointMjdTai >= MJD_MIN"
    )
    parser.add_argument(
        "--mjd_max", type=float, default=None, help="Only download diaSources with midpointMjdTai <= MJD_MAX"
    )
    args = parser.parse_args()

    download_full_cutouts_fits(
        dia_object_id=args.obj_id,
        outdir=Path(args.outdir) if args.outdir else None,
        skip_existing=not args.no_skip,
        mjd_min=args.mjd_min,
        mjd_max=args.mjd_max,
    )
