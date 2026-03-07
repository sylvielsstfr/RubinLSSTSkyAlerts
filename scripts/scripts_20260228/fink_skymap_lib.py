"""
fink_skymap_lib.py
==================
Library for plotting Fink/LSST alert sky maps.

Features
--------
- Alert scatter with per-tag color coding
- Galactic plane and optional galactic band overlays (astropy)
- Real sky background via CDS hips2fits (astroquery) — robust multi-strategy
- RA/Dec coordinate grid, clearly visible, with tick labels
- Rubin LSST Deep Drilling Fields (DDF)
- Rectangular projection (zoomable) + Mollweide full-sky

Column naming convention (LSST DPDD schema)
--------------------------------------------
- Prefix ``r:``  → diaSource table field (NOT the spectral band r)
- Prefix ``f:``  → Fink-computed field
- Spectral band  → value of column ``r:band`` ∈ {u, g, r, i, z, y}

Dependencies
------------
    pip install astropy matplotlib numpy pandas astroquery

Author : dagoret
Date   : 2026-03-06
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from astropy import units as u
from astropy.coordinates import Galactic, SkyCoord
from matplotlib.lines import Line2D

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# Tag styles
# ─────────────────────────────────────────────────────────────────────────────

TAG_STYLES: dict[str, dict] = {
    "extragalactic_new_candidate": {
        "color": "#58a6ff", "marker": "o",
        "label": "Extragalactic new", "zorder": 5,
    },
    "extragalactic_lt20mag_candidate": {
        "color": "#3fb950", "marker": "s",
        "label": "Extragalactic <20 mag", "zorder": 5,
    },
    "sn_near_galaxy_candidate": {
        "color": "#f0e040", "marker": "*",
        "label": "SN near galaxy", "zorder": 6,
    },
    "in_tns": {
        "color": "#ff7b72", "marker": "D",
        "label": "In TNS", "zorder": 7,
    },
    "hostless_candidate": {
        "color": "#bc8cff", "marker": "^",
        "label": "Hostless", "zorder": 4,
    },
}
DEFAULT_TAG_STYLE: dict = {
    "color": "#8b949e", "marker": "o", "label": "Other", "zorder": 3,
}

# ─────────────────────────────────────────────────────────────────────────────
# Rubin LSST Deep Drilling Fields
# ─────────────────────────────────────────────────────────────────────────────

RUBIN_DDF: list[dict] = [
    {"name": "COSMOS",   "ra": 150.1191, "dec":   2.2058},
    {"name": "XMM-LSS",  "ra":  35.7083, "dec":  -4.7500},
    {"name": "ELAIS-S1", "ra":   9.4500, "dec": -44.0000},
    {"name": "ECDFS",    "ra":  53.1250, "dec": -28.1000},
    {"name": "EDFS-a",   "ra":  58.9000, "dec": -49.3150},
    {"name": "EDFS-b",   "ra":  63.6000, "dec": -47.6000},
]

# ─────────────────────────────────────────────────────────────────────────────
# Dark theme colours
# ─────────────────────────────────────────────────────────────────────────────

DARK_BG       = "#0d1117"
PANEL_BG      = "#161b22"
TEXT_COL      = "#e6edf3"
MUTED_COL     = "#8b949e"
BORDER_COL    = "#30363d"
GRID_COL      = "#4a5568"    # clearly visible grid lines
GALPLANE_COL  = "#f08000"    # orange  — galactic plane b=0
GALBAND_COL   = "#b05a00"    # darker  — galactic band ±b
GALCENTER_COL = "#ff4444"    # red     — galactic centre
DDF_COL       = "#00e5ff"    # cyan    — DDFs

# ─────────────────────────────────────────────────────────────────────────────
# Coordinate utilities
# ─────────────────────────────────────────────────────────────────────────────

def galactic_plane_radec(n: int = 2000) -> tuple[np.ndarray, np.ndarray]:
    """Return RA, Dec (deg, ICRS) of the galactic plane (b = 0)."""
    l = np.linspace(0, 360, n)
    c = SkyCoord(l=l * u.deg, b=0 * u.deg, frame=Galactic).icrs
    return c.ra.deg, c.dec.deg


def galactic_latitude_radec(b_deg: float, n: int = 1000) -> tuple[np.ndarray, np.ndarray]:
    """Return RA, Dec (deg, ICRS) along constant galactic latitude b_deg."""
    l = np.linspace(0, 360, n)
    c = SkyCoord(l=l * u.deg, b=b_deg * u.deg, frame=Galactic).icrs
    return c.ra.deg, c.dec.deg


def _split_segments(
    ra: np.ndarray, dec: np.ndarray, jump: float = 180.0
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Split arrays at RA wrap-around (large jumps > jump degrees)."""
    breaks = list(np.where(np.abs(np.diff(ra)) > jump)[0] + 1)
    idx = [0] + breaks + [len(ra)]
    return [(ra[idx[i]:idx[i+1]], dec[idx[i]:idx[i+1]])
            for i in range(len(idx) - 1)]


def ra_deg_to_hms(ra_deg: float) -> str:
    """RA degrees → 'HHhMMm' string."""
    c = SkyCoord(ra=float(ra_deg) * u.deg, dec=0 * u.deg)
    h = c.ra.hms
    return f"{int(h.h):02d}h{int(h.m):02d}m"


# ─────────────────────────────────────────────────────────────────────────────
# Axis formatters
# ─────────────────────────────────────────────────────────────────────────────

class _RAFormatter(mticker.Formatter):
    def __call__(self, x, pos=None):
        return ra_deg_to_hms(x % 360)

class _RAFormatterDeg(mticker.Formatter):
    def __call__(self, x, pos=None):
        return f"{x % 360:.1f}°"

class _DecFormatter(mticker.Formatter):
    def __call__(self, x, pos=None):
        return f"{x:+.1f}°"


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def load_catalog(dataset_dir: str | Path) -> pd.DataFrame:
    """
    Load alert catalog, deduplicate on diaObjectId keeping the row
    with the highest SNN score.
    """
    cat = pd.read_parquet(Path(dataset_dir) / "alerts_catalog.parquet")
    cat = (
        cat.sort_values("f:clf_snnSnVsOthers_score", ascending=False)
           .drop_duplicates("r:diaObjectId")
           .reset_index(drop=True)
    )
    return cat


def catalog_summary(catalog: pd.DataFrame) -> pd.DataFrame:
    """Per-tag statistics."""
    rows = []
    for tag, grp in catalog.groupby("fink_tag"):
        s = TAG_STYLES.get(tag, DEFAULT_TAG_STYLE)
        rows.append({
            "tag":       tag,
            "label":     s["label"],
            "color":     s["color"],
            "n_objects": len(grp),
            "ra_min":    grp["r:ra"].min(),
            "ra_max":    grp["r:ra"].max(),
            "dec_min":   grp["r:dec"].min(),
            "dec_max":   grp["r:dec"].max(),
            "snn_mean":  grp["f:clf_snnSnVsOthers_score"].mean(),
            "n_tns":     grp["f:xm_tns_fullname"].notna().sum()
                         if "f:xm_tns_fullname" in grp else 0,
        })
    return pd.DataFrame(rows).set_index("tag")


# ─────────────────────────────────────────────────────────────────────────────
# HiPS background — robust multi-strategy implementation
# ─────────────────────────────────────────────────────────────────────────────

def _normalise_image_cube(data: np.ndarray) -> np.ndarray:
    """
    Convert a raw FITS cube to a display-ready (H, W, 4) RGBA float32 array.

    Handles shapes: (3, H, W), (H, W, 3), (H, W) — grayscale.
    Applies an asinh stretch per channel.  Alpha = 1 everywhere except
    fully-masked (all-zero) pixels.
    """
    data = np.asarray(data, dtype=np.float32)

    # Bring to (H, W, C)
    if data.ndim == 3 and data.shape[0] in (1, 2, 3, 4):
        data = np.moveaxis(data, 0, -1)          # (C, H, W) → (H, W, C)
    if data.ndim == 2:
        data = np.stack([data, data, data], axis=-1)  # grayscale → RGB

    # Keep only first 3 channels if more
    data = data[..., :3]

    # Replace NaN/Inf
    data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)

    # Asinh stretch per channel
    rgb = np.zeros_like(data, dtype=np.float32)
    for ch in range(3):
        plane = data[..., ch]
        positive = plane[plane > 0]
        if positive.size > 10:
            lo = np.percentile(positive, 1)
            hi = np.percentile(positive, 99)
        else:
            lo, hi = plane.min(), plane.max()
        span = hi - lo if hi > lo else 1.0
        norm = (plane - lo) / span
        stretched = np.arcsinh(norm * 3.0) / np.arcsinh(3.0)
        rgb[..., ch] = np.clip(stretched, 0.0, 1.0)

    # RGBA
    alpha = (rgb.sum(axis=-1) > 0.01).astype(np.float32)
    rgba  = np.concatenate([rgb, alpha[..., np.newaxis]], axis=-1)
    return rgba


def fetch_hips_image(
    ra_center: float,
    dec_center: float,
    fov_deg: float,
    hips_survey: str = "CDS/P/DSS2/color",
    width_px: int = 1024,
    height_px: int = 768,
    projection: str = "TAN",
    verbose: bool = True,
) -> np.ndarray | None:
    """
    Download a HiPS image from the CDS hips2fits service.

    Tries multiple strategies because the astroquery API and the server
    response format have changed across versions:

    Strategy 1 — astroquery hips2fits, format='fits'
    Strategy 2 — astroquery hips2fits, format='jpg', then PIL decode
    Strategy 3 — direct HTTP GET to https://alasky.cds.unistra.fr/hips-image-services/hips2fits
    Strategy 4 — direct HTTP GET to legacy https://alasky.u-strasbg.fr/hips-image-services/hips2fits

    Parameters
    ----------
    ra_center, dec_center : float   Field centre in degrees (ICRS).
    fov_deg : float                 Field of view in degrees.
    hips_survey : str               HiPS survey ID.
    width_px, height_px : int       Output image size in pixels.
    projection : str                WCS projection code (TAN, CAR, MOL, ...).
    verbose : bool                  Print progress / error messages.

    Returns
    -------
    np.ndarray of shape (H, W, 4) float32 RGBA in [0, 1], or None on failure.
    """

    def _vprint(*args):
        if verbose:
            print("[HiPS]", *args)

    # ── Strategy 1: astroquery format='fits' ─────────────────────────────────
    try:
        from astroquery.hips2fits import hips2fits
        _vprint(f"Strategy 1 — astroquery FITS  ({hips_survey})")
        result = hips2fits.query(
            hips       = hips_survey,
            ra         = ra_center * u.deg,
            dec        = dec_center * u.deg,
            fov        = fov_deg * u.deg,
            width      = width_px,
            height     = height_px,
            projection = projection,
            format     = "fits",
        )
        hdu = result[0] if hasattr(result, "__getitem__") else result
        if hdu.data is not None and hdu.data.size > 0:
            _vprint(f"  → HDU data shape: {hdu.data.shape}  dtype: {hdu.data.dtype}")
            for kw in ['CRVAL1','CRVAL2','CRPIX1','CRPIX2',
                       'CDELT1','CDELT2','CTYPE1','CTYPE2',
                       'NAXIS1','NAXIS2']:
                if kw in hdu.header:
                    _vprint(f"  FITS header  {kw} = {hdu.header[kw]}")
            return _normalise_image_cube(hdu.data)
        _vprint("  → HDU data is None or empty")
    except Exception as exc:
        _vprint(f"  → Strategy 1 failed: {exc}")

    # ── Strategy 2: astroquery format='jpg' ──────────────────────────────────
    try:
        from astroquery.hips2fits import hips2fits
        import io
        from PIL import Image  # type: ignore
        _vprint("Strategy 2 — astroquery JPG + PIL decode")
        result = hips2fits.query(
            hips       = hips_survey,
            ra         = ra_center * u.deg,
            dec        = dec_center * u.deg,
            fov        = fov_deg * u.deg,
            width      = width_px,
            height     = height_px,
            projection = projection,
            format     = "jpg",
        )
        if isinstance(result, (bytes, bytearray)):
            img = np.array(Image.open(io.BytesIO(result)), dtype=np.float32) / 255.0
        elif hasattr(result, "data") and result.data is not None:
            img = result.data.astype(np.float32)
            if img.max() > 1.0:
                img /= 255.0
        else:
            raise ValueError(f"Unexpected result type: {type(result)}")
        _vprint(f"  → image shape: {img.shape}")
        if img.ndim == 2:
            img = np.stack([img, img, img], axis=-1)
        rgba = np.concatenate([img[..., :3],
                               np.ones((*img.shape[:2], 1), dtype=np.float32)], axis=-1)
        return np.clip(rgba, 0, 1)
    except Exception as exc:
        _vprint(f"  → Strategy 2 failed: {exc}")

    # ── Strategy 3/4: direct HTTP ─────────────────────────────────────────────
    for base_url in [
        "https://alasky.cds.unistra.fr/hips-image-services/hips2fits",
        "https://alasky.u-strasbg.fr/hips-image-services/hips2fits",
    ]:
        _vprint(f"Strategy 3/4 — direct HTTP  {base_url}")
        try:
            import requests
            import io
            params = {
                "hips"      : hips_survey,
                "ra"        : ra_center,
                "dec"       : dec_center,
                "fov"       : fov_deg,
                "width"     : width_px,
                "height"    : height_px,
                "projection": projection,
                "format"    : "fits",
            }
            resp = requests.get(base_url, params=params, timeout=60)
            resp.raise_for_status()
            _vprint(f"  → HTTP {resp.status_code}  "
                    f"Content-Type: {resp.headers.get('Content-Type', '?')}  "
                    f"bytes: {len(resp.content)}")
            from astropy.io import fits as afits
            with afits.open(io.BytesIO(resp.content)) as hdul:
                data = hdul[0].data
                if data is not None and data.size > 0:
                    _vprint(f"  → FITS data shape: {data.shape}")
                    return _normalise_image_cube(data)
                _vprint("  → FITS data is None")
        except Exception as exc:
            _vprint(f"  → failed: {exc}")

    _vprint("All strategies failed.  Sky background unavailable.")
    return None


def overlay_hips_background(
    ax: plt.Axes,
    ra_min: float,
    ra_max: float,
    dec_min: float,
    dec_max: float,
    hips_survey: str = "CDS/P/DSS2/color",
    alpha: float = 0.65,
    width_px: int = 1024,
    height_px: int = 768,
    verbose: bool = True,
) -> bool:
    """Fetch a HiPS image and overlay it on *ax* as an imshow background. Returns True on success."""
    ra_c  = 0.5 * (ra_min + ra_max)
    dec_c = 0.5 * (dec_min + dec_max)
    fov   = max(ra_max - ra_min, dec_max - dec_min) * 1.10

    img = fetch_hips_image(
        ra_c, dec_c, fov,
        hips_survey=hips_survey,
        width_px=width_px, height_px=height_px,
        verbose=verbose,
    )
    if img is None:
        return False

    ax.imshow(
        img,
        origin="upper",
        extent=[ra_max, ra_min, dec_min, dec_max],
        aspect="auto",
        zorder=0,
        alpha=alpha,
        interpolation="bilinear",
    )
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Coordinate grid — clearly visible
# ─────────────────────────────────────────────────────────────────────────────

def draw_radec_grid(
    ax: plt.Axes,
    ra_min: float,
    ra_max: float,
    dec_min: float,
    dec_max: float,
    ra_step: float = 5.0,
    dec_step: float = 5.0,
    ra_unit: str = "hms",
) -> None:
    """Draw a clearly visible RA/Dec coordinate grid on a rectangular axes."""
    ra_start  = np.ceil(ra_min   / ra_step)  * ra_step
    ra_end    = np.floor(ra_max  / ra_step)  * ra_step
    ra_ticks  = np.arange(ra_start,  ra_end  + ra_step  * 0.01, ra_step)
    dec_start = np.ceil(dec_min  / dec_step) * dec_step
    dec_end   = np.floor(dec_max / dec_step) * dec_step
    dec_ticks = np.arange(dec_start, dec_end + dec_step * 0.01, dec_step)

    for ra_t in ra_ticks:
        ax.axvline(ra_t, color=GRID_COL, lw=0.9, ls="-", alpha=0.70, zorder=2)
    for dec_t in dec_ticks:
        ax.axhline(dec_t, color=GRID_COL, lw=0.9, ls="-", alpha=0.70, zorder=2)

    ax.set_xticks(ra_ticks)
    ax.set_yticks(dec_ticks)
    ax.xaxis.set_major_formatter(
        _RAFormatter() if ra_unit == "hms" else _RAFormatterDeg()
    )
    ax.yaxis.set_major_formatter(_DecFormatter())
    ax.tick_params(axis="x", colors=TEXT_COL, labelsize=8.5, direction="out", pad=4, length=4)
    ax.tick_params(axis="y", colors=TEXT_COL, labelsize=8.5, direction="out", pad=4, length=4)


# ─────────────────────────────────────────────────────────────────────────────
# Galactic & DDF overlays
# ─────────────────────────────────────────────────────────────────────────────

def _draw_galactic_rect(ax, ra_min, ra_max, dec_min, dec_max, show_plane=True, show_band=False, band_b=15.0):
    def _plot_curve(ra_arr, dec_arr, col, lw, ls, alpha, zo):
        for ra_s, dec_s in _split_segments(ra_arr, dec_arr):
            m = ((ra_s >= ra_min) & (ra_s <= ra_max) &
                 (dec_s >= dec_min) & (dec_s <= dec_max))
            if m.sum() > 1:
                ax.plot(ra_s[m], dec_s[m], color=col, lw=lw, ls=ls, alpha=alpha, zorder=zo)

    if show_plane:
        _plot_curve(*galactic_plane_radec(3000), GALPLANE_COL, 2.2, "-", 0.90, 8)
    if show_band:
        for b in [+band_b, -band_b]:
            _plot_curve(*galactic_latitude_radec(b, 1000), GALBAND_COL, 1.0, "--", 0.65, 7)

    gc = SkyCoord(l=0*u.deg, b=0*u.deg, frame=Galactic).icrs
    if ra_min <= gc.ra.deg <= ra_max and dec_min <= gc.dec.deg <= dec_max:
        ax.scatter(gc.ra.deg, gc.dec.deg, marker="x", s=160,
                   color=GALCENTER_COL, linewidths=2.5, zorder=10)
        ax.annotate("GC", (gc.ra.deg, gc.dec.deg), xytext=(5, 4),
                    textcoords="offset points", color=GALCENTER_COL,
                    fontsize=8, fontfamily="monospace")


def _draw_ddf_rect(ax, ra_min, ra_max, dec_min, dec_max):
    for ddf in RUBIN_DDF:
        if ra_min <= ddf["ra"] <= ra_max and dec_min <= ddf["dec"] <= dec_max:
            ax.scatter(ddf["ra"], ddf["dec"], marker="P", s=160, color=DDF_COL,
                       edgecolors="white", linewidths=0.9, zorder=11)
            ax.annotate(ddf["name"], (ddf["ra"], ddf["dec"]), xytext=(6, 4),
                        textcoords="offset points", color=DDF_COL,
                        fontsize=8.5, fontfamily="monospace", fontweight="bold")


def _draw_alerts_rect(ax, catalog, tags, marker_size, marker_alpha):
    n = 0
    for tag in tags:
        s   = TAG_STYLES.get(tag, DEFAULT_TAG_STYLE)
        sub = catalog[catalog["fink_tag"] == tag]
        if sub.empty:
            continue
        ax.scatter(sub["r:ra"], sub["r:dec"], c=s["color"], marker=s["marker"],
                   s=marker_size, alpha=marker_alpha, zorder=s["zorder"],
                   edgecolors="white", linewidths=0.3,
                   label=f"{s['label']}  (n={len(sub)})")
        n += len(sub)
    return n


def _build_legend(ax, show_ddf, show_plane, show_band=False, band_b=15.0):
    handles, labels = ax.get_legend_handles_labels()
    if show_plane:
        handles.append(Line2D([0], [0], color=GALPLANE_COL, lw=2.2))
        labels.append("Galactic plane (b = 0°)")
    if show_band:
        handles.append(Line2D([0], [0], color=GALBAND_COL, lw=1.2, ls="--"))
        labels.append(f"Galactic band (|b| = {band_b:.0f}°)")
    if show_ddf:
        handles.append(Line2D([0], [0], marker="P", color="w",
                               markerfacecolor=DDF_COL, markersize=9, linestyle="None"))
        labels.append("Rubin DDF")
    handles.append(Line2D([0], [0], marker="x", color=GALCENTER_COL,
                           markersize=9, linestyle="None", markeredgewidth=2))
    labels.append("Galactic centre")
    ax.legend(handles, labels, loc="lower left", fontsize=7.5,
              facecolor=DARK_BG, labelcolor=TEXT_COL,
              edgecolor=BORDER_COL, framealpha=0.92, ncol=2)


# ─────────────────────────────────────────────────────────────────────────────
# plot_skymap_rect
# ─────────────────────────────────────────────────────────────────────────────

def plot_skymap_rect(
    catalog: pd.DataFrame,
    ra_min: float | None = None,
    ra_max: float | None = None,
    dec_min: float | None = None,
    dec_max: float | None = None,
    marker_size: float = 40,
    marker_alpha: float = 0.85,
    show_galactic_plane: bool = True,
    show_galactic_band: bool = False,
    galactic_band_b: float = 15.0,
    show_ddf: bool = True,
    show_grid: bool = True,
    ra_unit: str = "hms",
    ra_grid_step: float = 5.0,
    dec_grid_step: float = 5.0,
    sky_background: bool = False,
    hips_survey: str = "CDS/P/DSS2/color",
    hips_alpha: float = 0.65,
    hips_verbose: bool = True,
    title: str | None = None,
    figsize: tuple[float, float] = (14, 8),
    ax: plt.Axes | None = None,
    tags_to_show: list[str] | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize, facecolor=DARK_BG)
        fig.patch.set_facecolor(DARK_BG)
    else:
        fig = ax.get_figure()
    ax.set_facecolor(PANEL_BG)

    mrg_ra, mrg_dec = 2.0, 1.5
    if ra_min  is None: ra_min  = catalog["r:ra"].min()  - mrg_ra
    if ra_max  is None: ra_max  = catalog["r:ra"].max()  + mrg_ra
    if dec_min is None: dec_min = catalog["r:dec"].min() - mrg_dec
    if dec_max is None: dec_max = catalog["r:dec"].max() + mrg_dec

    if sky_background:
        ok = overlay_hips_background(
            ax, ra_min, ra_max, dec_min, dec_max,
            hips_survey=hips_survey, alpha=hips_alpha, verbose=hips_verbose,
        )
        if not ok:
            print("[HiPS] Background not available — plain background kept.")

    if show_grid:
        draw_radec_grid(ax, ra_min, ra_max, dec_min, dec_max,
                        ra_step=ra_grid_step, dec_step=dec_grid_step, ra_unit=ra_unit)

    _draw_galactic_rect(ax, ra_min, ra_max, dec_min, dec_max,
                        show_plane=show_galactic_plane, show_band=show_galactic_band,
                        band_b=galactic_band_b)

    if show_ddf:
        _draw_ddf_rect(ax, ra_min, ra_max, dec_min, dec_max)

    tags      = tags_to_show or sorted(catalog["fink_tag"].unique().tolist())
    n_plotted = _draw_alerts_rect(ax, catalog, tags, marker_size, marker_alpha)

    ax.invert_xaxis()
    ax.set_xlim(ra_max, ra_min)
    ax.set_ylim(dec_min, dec_max)

    ra_label = "Right Ascension (HH:MM)" if ra_unit == "hms" else "Right Ascension (degrees)"
    ax.set_xlabel(ra_label, color=TEXT_COL, fontsize=10)
    ax.set_ylabel("Declination (degrees)", color=TEXT_COL, fontsize=10)
    for sp in ax.spines.values():
        sp.set_edgecolor(BORDER_COL)

    _build_legend(ax, show_ddf, show_galactic_plane, show_galactic_band, galactic_band_b)

    if title is None:
        title = (f"Fink/LSST Alert Sky Map  —  {n_plotted} objects"
                 f"\nRA: {ra_min:.1f}°–{ra_max:.1f}°   Dec: {dec_min:.1f}°–{dec_max:.1f}°")
    ax.set_title(title, color=TEXT_COL, fontsize=11, fontfamily="monospace", pad=8)

    return fig, ax


# ─────────────────────────────────────────────────────────────────────────────
# plot_skymap_mollweide
# ─────────────────────────────────────────────────────────────────────────────

def _ra_to_moll(ra_deg):
    """RA degrees → Mollweide radians (0h centre, East left)."""
    ra = np.asarray(ra_deg, dtype=float) % 360
    ra = np.where(ra > 180, ra - 360, ra)
    return -np.deg2rad(ra)

def _dec_to_moll(dec_deg):
    return np.deg2rad(np.asarray(dec_deg, dtype=float))


def plot_skymap_mollweide(
    catalog: pd.DataFrame,
    marker_size: float = 30,
    marker_alpha: float = 0.85,
    show_galactic_plane: bool = True,
    show_galactic_band: bool = False,
    galactic_band_b: float = 15.0,
    show_ddf: bool = True,
    show_grid: bool = True,
    ra_unit: str = "hms",
    sky_background: bool = False,
    hips_survey: str = "CDS/P/DSS2/color",
    hips_alpha: float = 0.65,
    hips_verbose: bool = True,
    title: str | None = None,
    figsize: tuple[float, float] = (14, 7),
    tags_to_show: list[str] | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Full-sky Mollweide projection with optional HiPS background."""
    fig = plt.figure(figsize=figsize, facecolor=DARK_BG)
    fig.patch.set_facecolor(DARK_BG)
    ax  = fig.add_subplot(111, projection="mollweide")
    ax.set_facecolor(PANEL_BG)

    if sky_background:
        img = fetch_hips_image(
            ra_center=0.0, dec_center=0.0, fov_deg=360.0,
            hips_survey=hips_survey, width_px=2048, height_px=1024,
            projection="CAR", verbose=hips_verbose,
        )
        if img is not None:
            H_src, W_src = img.shape[:2]
            H_out, W_out = 512, 1024

            # FITS WCS: CRVAL1=0, CRPIX1=1024, CDELT1<0  /  CRVAL2=0, CRPIX2=512, CDELT2>0 (South at row 0)
            CRVAL1, CRPIX1, CDELT1 = 0.0, 1024.0, -360.0 / W_src
            CRVAL2, CRPIX2, CDELT2 = 0.0,  512.0, +180.0 / H_src

            x_ax = np.linspace(0, 1, W_out)
            y_ax = np.linspace(1, 0, H_out)
            xv, yv = np.meshgrid(x_ax, y_ax)
            x_moll = (xv - 0.5) * 2.0 * np.pi
            y_moll = (yv - 0.5) * np.pi

            ellipse_mask = (x_moll/np.pi)**2 + (y_moll/(np.pi/2))**2 <= 1.0

            # Inverse Mollweide (Newton): 2θ + sin(2θ) = π·sin(y_moll)
            theta = y_moll.copy()
            for _ in range(10):
                cos2t = np.cos(2.0 * theta)
                denom = np.where(np.abs(cos2t + 1) < 1e-12, 1e-12, 2.0 + 2.0 * cos2t)
                theta -= (2.0*theta + np.sin(2.0*theta) - np.pi * np.sin(y_moll)) / denom

            dec_deg_grid = np.rad2deg(np.arcsin(np.clip(
                (2.0*theta + np.sin(2.0*theta)) / np.pi, -1.0, 1.0)))

            costheta = np.cos(theta)
            ra_rad = np.where(np.abs(costheta) < 1e-9, 0.0, -x_moll / costheta)
            ra_deg_grid = np.rad2deg(ra_rad)  # [-180, 180]

            col_f = (ra_deg_grid  - CRVAL1) / CDELT1 + CRPIX1 - 1
            row_f = (dec_deg_grid - CRVAL2) / CDELT2 + CRPIX2 - 1
            col_f = col_f % W_src

            col0 = np.clip(col_f.astype(int), 0, W_src - 2)
            col1 = col0 + 1
            row0 = np.clip(row_f.astype(int), 0, H_src - 2)
            row1 = row0 + 1
            wc   = (col_f - col0)[..., np.newaxis]
            wr   = (row_f - row0)[..., np.newaxis]

            resampled = (
                img[row0, col0] * (1-wr) * (1-wc) +
                img[row0, col1] * (1-wr) *    wc  +
                img[row1, col0] *    wr  * (1-wc) +
                img[row1, col1] *    wr  *    wc
            ).astype(np.float32)

            resampled[..., 3] = np.where(ellipse_mask, resampled[..., 3] * hips_alpha, 0.0)

            ax.imshow(resampled, origin="upper", extent=[0, 1, 0, 1],
                      aspect="auto", zorder=0, interpolation="bilinear",
                      transform=ax.transAxes)
        else:
            if hips_verbose:
                print("[HiPS] Background not available — plain background kept.")

    if show_galactic_plane:
        ra_gp, dec_gp = galactic_plane_radec(3000)
        for ra_s, dec_s in _split_segments(ra_gp, dec_gp):
            ax.plot(_ra_to_moll(ra_s), _dec_to_moll(dec_s),
                    color=GALPLANE_COL, lw=2.0, alpha=0.9, zorder=5)

    if show_galactic_band:
        for b in [+galactic_band_b, -galactic_band_b]:
            ra_b, dec_b = galactic_latitude_radec(b, 1000)
            for ra_s, dec_s in _split_segments(ra_b, dec_b):
                ax.plot(_ra_to_moll(ra_s), _dec_to_moll(dec_s),
                        color=GALBAND_COL, lw=1.0, ls="--", alpha=0.65, zorder=4)

    gc = SkyCoord(l=0*u.deg, b=0*u.deg, frame=Galactic).icrs
    ax.scatter(_ra_to_moll([gc.ra.deg]), _dec_to_moll([gc.dec.deg]),
               marker="x", s=140, color=GALCENTER_COL, linewidths=2.5, zorder=10)

    if show_ddf:
        for ddf in RUBIN_DDF:
            ax.scatter(_ra_to_moll([ddf["ra"]]), _dec_to_moll([ddf["dec"]]),
                       marker="P", s=110, color=DDF_COL, edgecolors="white",
                       linewidths=0.8, zorder=11)
            ax.annotate(ddf["name"],
                        (_ra_to_moll([ddf["ra"]])[0], _dec_to_moll([ddf["dec"]])[0]),
                        xytext=(4, 4), textcoords="offset points",
                        color=DDF_COL, fontsize=6.5, fontfamily="monospace")

    tags      = tags_to_show or sorted(catalog["fink_tag"].unique().tolist())
    n_plotted = 0
    for tag in tags:
        s   = TAG_STYLES.get(tag, DEFAULT_TAG_STYLE)
        sub = catalog[catalog["fink_tag"] == tag]
        if sub.empty:
            continue
        ax.scatter(_ra_to_moll(sub["r:ra"].values), _dec_to_moll(sub["r:dec"].values),
                   c=s["color"], marker=s["marker"], s=marker_size, alpha=marker_alpha,
                   zorder=s["zorder"], edgecolors="white", linewidths=0.3,
                   label=f"{s['label']}  (n={len(sub)})")
        n_plotted += len(sub)

    if show_grid:
        ax.grid(True, color=GRID_COL, lw=0.8, alpha=0.65, ls="-", zorder=1)
        ra_deg  = np.arange(0, 360, 30)
        ax.set_xticks(_ra_to_moll(ra_deg))
        xlabels = [ra_deg_to_hms(r) for r in ra_deg] if ra_unit == "hms" else [f"{r:.0f}°" for r in ra_deg]
        ax.set_xticklabels(xlabels, color=TEXT_COL, fontsize=8)
        dec_deg = np.arange(-60, 90, 30)
        ax.set_yticks(_dec_to_moll(dec_deg))
        ax.set_yticklabels([f"{d:+.0f}°" for d in dec_deg], color=TEXT_COL, fontsize=8)
    else:
        ax.grid(False)

    ax.tick_params(colors=TEXT_COL, labelsize=8)
    _build_legend(ax, show_ddf, show_galactic_plane, show_galactic_band, galactic_band_b)

    if title is None:
        title = f"Fink/LSST Alert Sky Map — Mollweide  ({n_plotted} objects)"
    ax.set_title(title, color=TEXT_COL, fontsize=11, fontfamily="monospace", pad=10)

    return fig, ax


# ─────────────────────────────────────────────────────────────────────────────
# plot_skymap_combined
# ─────────────────────────────────────────────────────────────────────────────

def plot_skymap_combined(
    catalog: pd.DataFrame,
    ra_unit: str = "hms",
    show_galactic_plane: bool = True,
    show_galactic_band: bool = False,
    galactic_band_b: float = 15.0,
    show_ddf: bool = True,
    show_grid: bool = True,
    sky_background: bool = False,
    hips_survey: str = "CDS/P/DSS2/color",
    hips_alpha: float = 0.65,
    hips_verbose: bool = True,
    ra_grid_step: float = 5.0,
    dec_grid_step: float = 5.0,
    tags_to_show: list[str] | None = None,
    figsize: tuple[float, float] = (16, 12),
    save_path: str | Path | None = None,
) -> plt.Figure:
    """Two-panel sky map: Mollweide (top) + Rectangular zoom (bottom)."""
    fig = plt.figure(figsize=figsize, facecolor=DARK_BG)
    fig.patch.set_facecolor(DARK_BG)

    ax_moll = fig.add_subplot(2, 1, 1, projection="mollweide")
    ax_moll.set_facecolor(PANEL_BG)

    if show_galactic_plane:
        ra_gp, dec_gp = galactic_plane_radec(3000)
        for ra_s, dec_s in _split_segments(ra_gp, dec_gp):
            ax_moll.plot(_ra_to_moll(ra_s), _dec_to_moll(dec_s),
                         color=GALPLANE_COL, lw=2.0, alpha=0.9, zorder=5)
    if show_galactic_band:
        for b in [+galactic_band_b, -galactic_band_b]:
            ra_b, dec_b = galactic_latitude_radec(b, 1000)
            for ra_s, dec_s in _split_segments(ra_b, dec_b):
                ax_moll.plot(_ra_to_moll(ra_s), _dec_to_moll(dec_s),
                             color=GALBAND_COL, lw=1.0, ls="--", alpha=0.65, zorder=4)
    gc = SkyCoord(l=0*u.deg, b=0*u.deg, frame=Galactic).icrs
    ax_moll.scatter(_ra_to_moll([gc.ra.deg]), _dec_to_moll([gc.dec.deg]),
                    marker="x", s=140, color=GALCENTER_COL, linewidths=2.5, zorder=10)

    if show_ddf:
        for ddf in RUBIN_DDF:
            ax_moll.scatter(_ra_to_moll([ddf["ra"]]), _dec_to_moll([ddf["dec"]]),
                            marker="P", s=90, color=DDF_COL,
                            edgecolors="white", linewidths=0.8, zorder=11)
            ax_moll.annotate(ddf["name"],
                (_ra_to_moll([ddf["ra"]])[0], _dec_to_moll([ddf["dec"]])[0]),
                xytext=(4, 4), textcoords="offset points",
                color=DDF_COL, fontsize=6, fontfamily="monospace")

    tags = tags_to_show or sorted(catalog["fink_tag"].unique().tolist())
    for tag in tags:
        s   = TAG_STYLES.get(tag, DEFAULT_TAG_STYLE)
        sub = catalog[catalog["fink_tag"] == tag]
        if sub.empty:
            continue
        ax_moll.scatter(_ra_to_moll(sub["r:ra"].values), _dec_to_moll(sub["r:dec"].values),
                        c=s["color"], marker=s["marker"], s=22, alpha=0.85,
                        zorder=s["zorder"], edgecolors="white", linewidths=0.3,
                        label=f"{s['label']}  (n={len(sub)})")

    if show_grid:
        ax_moll.grid(True, color=GRID_COL, lw=0.8, alpha=0.65, ls="-", zorder=1)
        ra_deg = np.arange(0, 360, 30)
        ax_moll.set_xticks(_ra_to_moll(ra_deg))
        xlabels = ([ra_deg_to_hms(r) for r in ra_deg] if ra_unit == "hms"
                   else [f"{r:.0f}°" for r in ra_deg])
        ax_moll.set_xticklabels(xlabels, color=TEXT_COL, fontsize=7)
        dec_deg = np.arange(-60, 90, 30)
        ax_moll.set_yticks(_dec_to_moll(dec_deg))
        ax_moll.set_yticklabels([f"{d:+.0f}°" for d in dec_deg], color=TEXT_COL, fontsize=7)
    ax_moll.tick_params(colors=TEXT_COL, labelsize=7)
    _build_legend(ax_moll, show_ddf, show_galactic_plane, show_galactic_band, galactic_band_b)
    ax_moll.set_title("Full sky — Mollweide projection",
                      color=TEXT_COL, fontsize=10, fontfamily="monospace")

    ax_rect = fig.add_subplot(2, 1, 2)
    plot_skymap_rect(
        catalog,
        show_galactic_plane=show_galactic_plane,
        show_galactic_band=show_galactic_band,
        galactic_band_b=galactic_band_b,
        show_ddf=show_ddf,
        show_grid=show_grid,
        ra_unit=ra_unit,
        ra_grid_step=ra_grid_step,
        dec_grid_step=dec_grid_step,
        sky_background=sky_background,
        hips_survey=hips_survey,
        hips_alpha=hips_alpha,
        hips_verbose=hips_verbose,
        tags_to_show=tags_to_show,
        title="Zoom on data region — rectangular RA/Dec",
        ax=ax_rect,
    )

    fig.suptitle(
        f"Fink/LSST Alert Sky Map  —  "
        f"{catalog['r:diaObjectId'].nunique()} objects  —  "
        f"{catalog['fink_tag'].nunique()} tags",
        color=TEXT_COL, fontsize=13, fontfamily="monospace", y=1.005,
    )
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
        print(f"✓ Saved: {save_path}")

    return fig
