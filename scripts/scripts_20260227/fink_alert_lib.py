"""
fink_alert_lib.py
=================
Library for visualizing Fink/LSST (Rubin) alerts from a local dataset.

Provides plotting functions callable from a Jupyter notebook to display:
  - Light curves (flux in nJy and magnitude AB)
  - Cutouts (Science / Template / Difference)
  - Combined detail view (light curves + classifiers + cutouts)
  - Overview grid of all alerts for a given tag

Dataset structure expected:
  fink_dataset/
    alerts_catalog.parquet   # alert metadata + Fink scores
    lightcurves/             # one .parquet per diaObjectId
    cutouts/                 # one .npy per diaObjectId, shape (3, H, W)

Column naming convention (LSST DPDD schema):
  - Prefix 'r:' → diaSource table fields (NOT the spectral band 'r')
  - Prefix 'f:' → Fink-computed fields (classifiers, cross-matches)
  - Spectral band → value of column r:band ∈ {u, g, r, i, z, y}

Author : dagoret
Date   : 2026-02-27
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from astropy.visualization import ZScaleInterval

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

# Colors for each Rubin LSST spectral band (u g r i z y)
# Note: 'r:' column prefix is the diaSource table prefix, NOT band 'r'
BAND_COLORS: dict[str, str] = {
    "u": "#7B2FBE",    # violet
    "g": "#2CA02C",    # green
    "r": "#D62728",    # red
    "i": "#FF7F0E",    # orange
    "z": "#8C4A2F",    # brown
    "y": "#1A1A1A",    # near-black
}

# Approximate central wavelengths (nm) for the 6 Rubin bands
BAND_WAVELENGTHS: dict[str, int] = {
    "u": 365, "g": 480, "r": 620, "i": 750, "z": 880, "y": 1000,
}

# AB magnitude zero point for Rubin/LSST (uniform across all bands)
# mag_AB = -2.5 * log10(flux_nJy) + RUBIN_ZEROPOINT
RUBIN_ZEROPOINT: float = 31.4

# Dark theme colors
DARK_BG   = "#0d1117"
PANEL_BG  = "#161b22"
TEXT_COL  = "#e6edf3"
MUTED_COL = "#8b949e"
ACCENT    = "#58a6ff"
HIGHLIGHT = "#f0e040"
BORDER    = "#30363d"

# ─────────────────────────────────────────────────────────────────────────────
# Dataset loader
# ─────────────────────────────────────────────────────────────────────────────

class FinkDataset:
    """
    Loads and indexes a Fink/LSST alert dataset from disk.

    Parameters
    ----------
    dataset_dir : str or Path
        Path to the fink_dataset/ directory.
    """

    def __init__(self, dataset_dir: str | Path) -> None:
        self.dataset_dir = Path(dataset_dir)
        self.lc_dir      = self.dataset_dir / "lightcurves"
        self.cutout_dir  = self.dataset_dir / "cutouts"

        # Load catalog
        self.catalog = pd.read_parquet(self.dataset_dir / "alerts_catalog.parquet")

        # Build cutout index: {diaObjectId: {"path": Path, "label": int}}
        self.cutout_index: dict[int, dict] = {}
        for f in self.cutout_dir.glob("*.npy"):
            obj_id = int(f.stem.split("_label")[0])
            label  = int(f.stem.split("_label")[1])
            # Keep the entry even if the same obj_id appears twice with different labels
            # (prefer label=1 if both exist)
            if obj_id not in self.cutout_index or label == 1:
                self.cutout_index[obj_id] = {"path": f, "label": label}

    # ── Public helpers ────────────────────────────────────────────────────────

    @property
    def available_tags(self) -> list[str]:
        """Return the list of available Fink tags in the catalog."""
        return sorted(self.catalog["fink_tag"].unique().tolist())

    def get_object_ids(self, tag: str) -> np.ndarray:
        """Return unique diaObjectIds for a given tag."""
        return self.catalog[self.catalog["fink_tag"] == tag]["r:diaObjectId"].unique()

    def get_meta(self, obj_id: int) -> pd.Series:
        """Return the first catalog row for a given diaObjectId."""
        rows = self.catalog[self.catalog["r:diaObjectId"] == obj_id]
        if rows.empty:
            raise ValueError(f"diaObjectId {obj_id} not found in catalog.")
        return rows.iloc[0]

    def get_lightcurve(self, obj_id: int) -> pd.DataFrame:
        """Load the light curve parquet for a given diaObjectId."""
        lc_file = self.lc_dir / f"{obj_id}.parquet"
        if not lc_file.exists():
            return pd.DataFrame()
        return pd.read_parquet(lc_file)

    def get_cutouts(self, obj_id: int) -> np.ndarray | None:
        """
        Load cutout array for a given diaObjectId.

        Returns
        -------
        np.ndarray of shape (3, H, W) → [Science, Template, Difference]
        or None if not available.
        """
        entry = self.cutout_index.get(int(obj_id))
        if entry is None:
            return None
        return np.load(entry["path"])

    def summary(self) -> pd.DataFrame:
        """Return a summary DataFrame with counts per tag."""
        return (
            self.catalog
            .groupby("fink_tag")[["r:diaObjectId", "label"]]
            .agg(n_alerts=("r:diaObjectId", "count"), label=("label", "first"))
        )

    def list_objects(self, tag: str) -> pd.DataFrame:
        """
        Return a concise table of all objects for a given tag,
        sorted by SNN score descending.
        """
        sub = self.catalog[self.catalog["fink_tag"] == tag].copy()
        cols = [
            "r:diaObjectId", "r:band", "r:ra", "r:dec",
            "r:psfFlux", "r:snr", "r:midpointMjdTai",
            "f:clf_snnSnVsOthers_score", "f:clf_earlySNIa_score",
            "f:xm_tns_fullname", "f:xm_tns_type",
            "f:xm_legacydr8_zphot", "label",
        ]
        cols = [c for c in cols if c in sub.columns]
        return (
            sub[cols]
            .drop_duplicates("r:diaObjectId")
            .sort_values("f:clf_snnSnVsOthers_score", ascending=False)
            .reset_index(drop=True)
        )


# ─────────────────────────────────────────────────────────────────────────────
# Photometric utilities
# ─────────────────────────────────────────────────────────────────────────────

def flux_to_mag(
    flux: np.ndarray | float,
    flux_err: np.ndarray | float | None = None,
    zeropoint: float = RUBIN_ZEROPOINT,
) -> np.ndarray | tuple[np.ndarray, np.ndarray]:
    """
    Convert psfFlux (nJy) to AB magnitude.

    The AB photometric system gives a uniform zero point across all Rubin
    bands: mag_AB = -2.5 * log10(flux_nJy) + 31.4

    Negative or zero flux values (common in difference images) return NaN.

    Parameters
    ----------
    flux : array-like
        Flux in nJy.
    flux_err : array-like, optional
        Flux uncertainty in nJy.
    zeropoint : float
        AB zero point (default 31.4 for Rubin/LSST).

    Returns
    -------
    mag : np.ndarray
        AB magnitude (NaN where flux <= 0).
    mag_err : np.ndarray (only if flux_err is provided)
        Magnitude uncertainty.
    """
    flux = np.asarray(flux, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        mag = np.where(flux > 0, -2.5 * np.log10(flux) + zeropoint, np.nan)
        if flux_err is not None:
            flux_err = np.asarray(flux_err, dtype=float)
            mag_err = np.where(
                flux > 0,
                2.5 / np.log(10) * np.abs(flux_err / flux),
                np.nan,
            )
            return mag, mag_err
    return mag


def _zscale(img: np.ndarray, contrast: float = 0.25) -> tuple[float, float]:
    """Apply ZScale normalization to a 2D image array."""
    try:
        return ZScaleInterval(contrast=contrast).get_limits(img)
    except Exception:
        return float(np.nanpercentile(img, 1)), float(np.nanpercentile(img, 99))


# ─────────────────────────────────────────────────────────────────────────────
# Axis / theme helpers
# ─────────────────────────────────────────────────────────────────────────────

def _style_ax(ax: plt.Axes, title: str = "", xlabel: str = "", ylabel: str = "") -> None:
    """Apply the dark Fink-portal theme to a matplotlib Axes."""
    ax.set_facecolor(PANEL_BG)
    for sp in ax.spines.values():
        sp.set_edgecolor(BORDER)
    ax.tick_params(colors=MUTED_COL, labelsize=8)
    if title:
        ax.set_title(title, color=ACCENT, fontsize=10)
    if xlabel:
        ax.set_xlabel(xlabel, color=MUTED_COL, fontsize=9)
    if ylabel:
        ax.set_ylabel(ylabel, color=MUTED_COL, fontsize=9)


def _legend(ax: plt.Axes, **kwargs) -> None:
    """Add a dark-themed legend to an Axes."""
    ax.legend(
        fontsize=7,
        facecolor=DARK_BG,
        labelcolor=TEXT_COL,
        edgecolor=BORDER,
        markerscale=0.9,
        **kwargs,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Core plot functions
# ─────────────────────────────────────────────────────────────────────────────

def plot_lightcurve_flux(
    df_lc: pd.DataFrame,
    ax: plt.Axes | None = None,
    title: str = "Light curve — flux (nJy)",
    t0: float | None = None,
) -> plt.Axes:
    """
    Plot multi-band light curve in flux units (nJy).

    Parameters
    ----------
    df_lc : pd.DataFrame
        Light curve data with columns r:band, r:midpointMjdTai,
        r:psfFlux, r:psfFluxErr.
    ax : plt.Axes, optional
        Axes to draw on. Creates a new figure if None.
    title : str
        Axes title.
    t0 : float, optional
        MJD reference epoch. Defaults to the first epoch in df_lc.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 4), facecolor=DARK_BG)

    if df_lc.empty or "r:band" not in df_lc.columns:
        ax.text(0.5, 0.5, "No light curve data", transform=ax.transAxes,
                ha="center", va="center", color=MUTED_COL)
        _style_ax(ax, title=title)
        return ax

    if t0 is None:
        t0 = df_lc["r:midpointMjdTai"].min()

    for band in sorted(df_lc["r:band"].unique()):
        mask = df_lc["r:band"] == band
        t  = df_lc.loc[mask, "r:midpointMjdTai"] - t0
        f  = df_lc.loc[mask, "r:psfFlux"]
        fe = df_lc.loc[mask, "r:psfFluxErr"]
        ax.errorbar(
            t, f, yerr=fe,
            fmt="o", color=BAND_COLORS.get(band, "gray"),
            label=f"{band}  ({BAND_WAVELENGTHS.get(band, '?')} nm)",
            markersize=5, capsize=2, lw=1, alpha=0.9,
        )

    ax.axhline(0, color="#444", lw=0.8, ls="--")
    _style_ax(ax, title=title, xlabel="Δ MJD TAI (days)", ylabel="psfFlux (nJy)")
    _legend(ax)
    return ax


def plot_lightcurve_mag(
    df_lc: pd.DataFrame,
    ax: plt.Axes | None = None,
    title: str = "Light curve — mag AB",
    t0: float | None = None,
) -> plt.Axes:
    """
    Plot multi-band light curve in AB magnitude.

    Negative-flux detections are silently discarded (NaN in magnitude space).
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 4), facecolor=DARK_BG)

    if df_lc.empty or "r:band" not in df_lc.columns:
        ax.text(0.5, 0.5, "No light curve data", transform=ax.transAxes,
                ha="center", va="center", color=MUTED_COL)
        _style_ax(ax, title=title)
        return ax

    if t0 is None:
        t0 = df_lc["r:midpointMjdTai"].min()

    for band in sorted(df_lc["r:band"].unique()):
        mask = df_lc["r:band"] == band
        t    = df_lc.loc[mask, "r:midpointMjdTai"].values - t0
        f    = df_lc.loc[mask, "r:psfFlux"].values
        fe   = df_lc.loc[mask, "r:psfFluxErr"].values
        mag, mag_err = flux_to_mag(f, fe)
        valid = np.isfinite(mag)
        if valid.sum() > 0:
            ax.errorbar(
                t[valid], mag[valid], yerr=mag_err[valid],
                fmt="o", color=BAND_COLORS.get(band, "gray"),
                label=f"{band}  ({BAND_WAVELENGTHS.get(band, '?')} nm)",
                markersize=5, capsize=2, lw=1, alpha=0.9,
            )

    ax.invert_yaxis()
    _style_ax(ax, title=title, xlabel="Δ MJD TAI (days)", ylabel="mag AB")
    _legend(ax)
    return ax


def plot_cutouts(
    cutouts_arr: np.ndarray | None,
    band: str = "?",
    axes: list[plt.Axes] | None = None,
    figsize: tuple[float, float] = (15, 5),
    contrast: float = 0.25,
) -> list[plt.Axes]:
    """
    Plot Science, Template and Difference cutouts side by side.

    Parameters
    ----------
    cutouts_arr : np.ndarray of shape (3, H, W) or None
        Stacked cutout array [Science, Template, Difference].
    band : str
        Spectral band label for annotation (value of r:band).
    axes : list of 3 Axes, optional
        Existing axes to draw on. Creates a new figure if None.
    figsize : tuple
        Figure size if a new figure is created.
    contrast : float
        ZScale contrast parameter.
    """
    names = ["Science", "Template", "Difference"]
    cmaps = ["afmhot", "afmhot", "RdBu_r"]

    if axes is None:
        fig, axes = plt.subplots(1, 3, figsize=figsize, facecolor=DARK_BG)

    for idx, (name, cmap) in enumerate(zip(names, cmaps)):
        ax = axes[idx]
        ax.set_facecolor(PANEL_BG)

        if cutouts_arr is not None:
            img = cutouts_arr[idx]
            H, W = img.shape
            vmin, vmax = _zscale(img, contrast)
            if name == "Difference":
                absmax = max(abs(vmin), abs(vmax))
                vmin, vmax = -absmax, absmax

            im = ax.imshow(
                img, origin="lower", cmap=cmap,
                vmin=vmin, vmax=vmax, interpolation="nearest",
                extent=[0, W, 0, H],
            )
            cb = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            cb.set_label("ADU (counts)", color=MUTED_COL, fontsize=7)
            cb.ax.tick_params(labelsize=6, colors=MUTED_COL)

            # Crosshair at the center
            ax.plot(W / 2, H / 2, "+", color=HIGHLIGHT, ms=14, mew=2)
            # Indicative aperture circle (radius 3 pixels)
            circle = plt.Circle(
                (W / 2, H / 2), 3,
                color=HIGHLIGHT, fill=False, lw=1, ls="--", alpha=0.7,
            )
            ax.add_patch(circle)

            # Stats overlay
            ax.text(
                0.98, 0.02,
                f"{H}×{W} pix\nmin={img.min():.0f}\nmax={img.max():.0f}\nstd={img.std():.0f}",
                transform=ax.transAxes, color=MUTED_COL, fontsize=6,
                ha="right", va="bottom", fontfamily="monospace",
                bbox=dict(facecolor=DARK_BG, alpha=0.7, edgecolor="none", pad=2),
            )
        else:
            ax.text(0.5, 0.5, "No cutout\navailable",
                    transform=ax.transAxes, ha="center", va="center",
                    color=MUTED_COL, fontsize=10)

        _style_ax(ax, title=f"{name}  [band {band}]",
                  xlabel="x (pix)", ylabel="y (pix)")

    return list(axes)


def plot_classifiers(
    meta: pd.Series,
    ax: plt.Axes | None = None,
) -> plt.Axes:
    """
    Plot Fink classifier scores as a horizontal bar chart.

    Bars are colored blue (score ≥ 0.5) or red (score < 0.5).
    A dashed yellow line marks the 0.5 threshold.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(5, 3), facecolor=DARK_BG)

    scores = {
        "SNN\n(SN vs others)": float(meta.get("f:clf_snnSnVsOthers_score", 0)),
        "Early SN Ia":         max(0.0, float(meta.get("f:clf_earlySNIa_score", 0))),
        "CATS score":          float(meta.get("f:clf_cats_score", 0)),
    }
    labels = list(scores.keys())
    vals   = list(scores.values())
    colors = [ACCENT if v >= 0.5 else "#f85149" for v in vals]

    bars = ax.barh(labels, vals, color=colors, alpha=0.85, height=0.5)
    ax.axvline(0.5, color=HIGHLIGHT, lw=1.2, ls="--", alpha=0.8, label="threshold 0.5")
    ax.set_xlim(0, 1)

    for bar, val in zip(bars, vals):
        ax.text(
            min(val + 0.02, 0.92),
            bar.get_y() + bar.get_height() / 2,
            f"{val:.3f}",
            va="center", color=TEXT_COL, fontsize=9, fontfamily="monospace",
        )

    _style_ax(ax, title="Fink classifiers", xlabel="Score")
    _legend(ax)
    return ax


# ─────────────────────────────────────────────────────────────────────────────
# Composite views
# ─────────────────────────────────────────────────────────────────────────────

def plot_alert_overview(
    dataset: FinkDataset,
    obj_id: int,
    figsize: tuple[float, float] = (20, 5),
    save: bool = False,
) -> plt.Figure:
    """
    Compact overview of one alert (5 panels, portal-style).

    Layout: [flux LC] [mag LC] [Science] [Template] [Difference]

    Parameters
    ----------
    dataset : FinkDataset
    obj_id : int
        diaObjectId to display.
    figsize : tuple
    save : bool
        If True, saves the figure to fink_dataset/{obj_id}_viewer.png.
    """
    meta       = dataset.get_meta(obj_id)
    df_lc      = dataset.get_lightcurve(obj_id)
    cutouts    = dataset.get_cutouts(obj_id)
    band       = meta.get("r:band", "?")

    fig = plt.figure(figsize=figsize, facecolor=DARK_BG)
    gs  = gridspec.GridSpec(1, 5, figure=fig, wspace=0.3,
                            left=0.05, right=0.97, top=0.88, bottom=0.15)

    # Title
    tns     = meta.get("f:xm_tns_fullname", "")
    tns_str = f"  →  TNS: {tns}" if pd.notna(tns) and tns else ""
    label_str = "EXTRAGALACTIC" if meta["label"] == 1 else "OTHER"
    fig.suptitle(
        f"diaObjectId {obj_id}{tns_str}     [{label_str}]  |  tag: {meta['fink_tag']}",
        fontsize=10, color=TEXT_COL, fontfamily="monospace", y=0.97,
    )

    # Flux light curve
    ax1 = fig.add_subplot(gs[0, 0])
    plot_lightcurve_flux(df_lc, ax=ax1)

    # Magnitude light curve
    ax2 = fig.add_subplot(gs[0, 1])
    plot_lightcurve_mag(df_lc, ax=ax2)

    # Cutouts
    cutout_axes = [fig.add_subplot(gs[0, i + 2]) for i in range(3)]
    plot_cutouts(cutouts, band=band, axes=cutout_axes)

    if save:
        out = dataset.dataset_dir / f"{obj_id}_viewer.png"
        fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
        print(f"  ✓ Saved: {out}")

    return fig


def plot_alert_detail(
    dataset: FinkDataset,
    obj_id: int,
    figsize: tuple[float, float] = (16, 9),
    save: bool = False,
) -> plt.Figure:
    """
    Detailed 2×3 view of one alert.

    Layout:
      Row 0: [flux LC]  [mag LC]  [classifier scores]
      Row 1: [Science]  [Template]  [Difference]

    Parameters
    ----------
    dataset : FinkDataset
    obj_id : int
        diaObjectId to display.
    figsize : tuple
    save : bool
        If True, saves the figure to fink_dataset/{obj_id}_detail.png.
    """
    meta    = dataset.get_meta(obj_id)
    df_lc   = dataset.get_lightcurve(obj_id)
    cutouts = dataset.get_cutouts(obj_id)
    band    = meta.get("r:band", "?")

    fig, axes = plt.subplots(2, 3, figsize=figsize, facecolor=DARK_BG)
    fig.patch.set_facecolor(DARK_BG)

    tns     = meta.get("f:xm_tns_fullname", "")
    tns_str = f"  →  TNS: {tns}" if pd.notna(tns) and tns else ""
    zphot   = meta.get("f:xm_legacydr8_zphot", "—")
    fig.suptitle(
        f"Fink/LSST  —  diaObjectId {obj_id}{tns_str}"
        f"     RA={meta['r:ra']:.4f}°  Dec={meta['r:dec']:.4f}°"
        f"     zphot={zphot}",
        fontsize=11, color=TEXT_COL, fontfamily="monospace", y=0.99,
    )

    # Row 0: light curves + classifiers
    plot_lightcurve_flux(df_lc, ax=axes[0, 0])
    plot_lightcurve_mag(df_lc, ax=axes[0, 1])
    plot_classifiers(meta, ax=axes[0, 2])

    # Row 1: cutouts
    plot_cutouts(cutouts, band=band, axes=[axes[1, 0], axes[1, 1], axes[1, 2]])

    plt.tight_layout(rect=[0, 0, 1, 0.97])

    if save:
        out = dataset.dataset_dir / f"{obj_id}_detail.png"
        fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
        print(f"  ✓ Saved: {out}")

    return fig


def plot_tag_grid(
    dataset: FinkDataset,
    tag: str,
    ncols: int = 5,
    highlight_id: int | None = None,
    figsize_per_cell: tuple[float, float] = (3.5, 3.5),
    save: bool = False,
) -> plt.Figure:
    """
    Overview grid of all alerts for a given tag.

    Each cell shows the Science cutout with overlaid metadata.
    The currently selected alert (highlight_id) is outlined in yellow.

    Parameters
    ----------
    dataset : FinkDataset
    tag : str
        Fink tag to display.
    ncols : int
        Number of columns in the grid.
    highlight_id : int, optional
        diaObjectId to highlight with a yellow border.
    figsize_per_cell : tuple
        Size of each grid cell in inches.
    save : bool
        If True, saves the figure to fink_dataset/overview_{tag}.png.
    """
    oids  = dataset.get_object_ids(tag)
    n     = len(oids)
    nrows = int(np.ceil(n / ncols))

    fig, axes = plt.subplots(
        nrows, ncols,
        figsize=(ncols * figsize_per_cell[0], nrows * figsize_per_cell[1]),
        facecolor=DARK_BG,
        squeeze=False,
    )
    fig.suptitle(
        f"Tag: {tag}  ({n} objects)",
        fontsize=12, color=TEXT_COL, fontfamily="monospace", y=1.01,
    )

    axes_flat = axes.flatten()
    zscale    = ZScaleInterval(contrast=0.25)

    for i, oid in enumerate(oids):
        ax  = axes_flat[i]
        ax.set_facecolor(PANEL_BG)
        row = dataset.get_meta(int(oid))

        # Science cutout thumbnail
        cutouts = dataset.get_cutouts(int(oid))
        if cutouts is not None:
            img = cutouts[0]  # Science
            try:
                vmin, vmax = zscale.get_limits(img)
            except Exception:
                vmin, vmax = np.nanpercentile(img, [1, 99])
            ax.imshow(img, origin="lower", cmap="afmhot",
                      vmin=vmin, vmax=vmax, aspect="auto",
                      interpolation="nearest")
            cy, cx = np.array(img.shape) / 2
            ax.plot(cx, cy, "+", color=HIGHLIGHT, ms=10, mew=1.5)
        else:
            ax.text(0.5, 0.5, "no cutout", ha="center", va="center",
                    color=MUTED_COL, transform=ax.transAxes)

        # Metadata overlay
        snn     = row.get("f:clf_snnSnVsOthers_score", float("nan"))
        snr     = row.get("r:snr", float("nan"))
        band    = row.get("r:band", "?")
        tns     = row.get("f:xm_tns_fullname", "")
        tns_str = f"\n{tns}" if pd.notna(tns) and tns else ""
        ax.text(
            0.02, 0.98,
            f"#{i}  …{str(oid)[-6:]}\nSNN={snn:.2f}  SNR={snr:.0f}\nband {band}{tns_str}",
            transform=ax.transAxes, color=TEXT_COL, fontsize=6.5,
            va="top", fontfamily="monospace",
            bbox=dict(facecolor=DARK_BG, alpha=0.7, edgecolor="none", pad=1.5),
        )

        # Border: yellow if highlighted, dark otherwise
        border_color = HIGHLIGHT if int(oid) == highlight_id else BORDER
        border_width = 2.5 if int(oid) == highlight_id else 0.8
        for sp in ax.spines.values():
            sp.set_edgecolor(border_color)
            sp.set_linewidth(border_width)
        ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

    # Hide unused axes
    for j in range(len(oids), len(axes_flat)):
        axes_flat[j].set_visible(False)

    plt.tight_layout()

    if save:
        out = dataset.dataset_dir / f"overview_{tag}.png"
        fig.savefig(out, dpi=120, bbox_inches="tight", facecolor=DARK_BG)
        print(f"  ✓ Saved: {out}")

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Loop helpers
# ─────────────────────────────────────────────────────────────────────────────

def plot_tag_loop(
    dataset: FinkDataset,
    tag: str,
    plot_type: str = "detail",
    max_alerts: int | None = None,
    save: bool = False,
    close_after: bool = True,
) -> None:
    """
    Iterate over all alerts of a tag and display a chosen plot type.

    Parameters
    ----------
    dataset : FinkDataset
    tag : str
        Fink tag to iterate over.
    plot_type : str
        One of:
          'overview' → compact 5-panel row (flux, mag, 3 cutouts)
          'detail'   → full 2×3 grid (LCs + classifiers + cutouts)
          'lc_flux'  → light curve in flux only
          'lc_mag'   → light curve in magnitude only
          'cutouts'  → cutouts only (1×3)
    max_alerts : int, optional
        Maximum number of alerts to display. None = all.
    save : bool
        If True, saves each figure to disk.
    close_after : bool
        If True, closes each figure after display to save memory.
    """
    oids = dataset.get_object_ids(tag)
    if max_alerts is not None:
        oids = oids[:max_alerts]

    print(f"Plotting {len(oids)} alerts for tag '{tag}'  (plot_type='{plot_type}')")

    for i, oid in enumerate(oids):
        obj_id = int(oid)
        print(f"  [{i+1:3d}/{len(oids)}]  diaObjectId={obj_id}")

        if plot_type == "overview":
            fig = plot_alert_overview(dataset, obj_id, save=save)
        elif plot_type == "detail":
            fig = plot_alert_detail(dataset, obj_id, save=save)
        elif plot_type == "lc_flux":
            df_lc = dataset.get_lightcurve(obj_id)
            fig, ax = plt.subplots(figsize=(8, 4), facecolor=DARK_BG)
            plot_lightcurve_flux(df_lc, ax=ax)
            meta = dataset.get_meta(obj_id)
            ax.set_title(
                f"Flux LC — diaObjectId {obj_id}  |  tag: {meta['fink_tag']}",
                color=ACCENT, fontsize=10,
            )
            if save:
                out = dataset.dataset_dir / f"{obj_id}_lc_flux.png"
                fig.savefig(out, dpi=120, bbox_inches="tight", facecolor=DARK_BG)
        elif plot_type == "lc_mag":
            df_lc = dataset.get_lightcurve(obj_id)
            fig, ax = plt.subplots(figsize=(8, 4), facecolor=DARK_BG)
            plot_lightcurve_mag(df_lc, ax=ax)
            meta = dataset.get_meta(obj_id)
            ax.set_title(
                f"Mag LC — diaObjectId {obj_id}  |  tag: {meta['fink_tag']}",
                color=ACCENT, fontsize=10,
            )
            if save:
                out = dataset.dataset_dir / f"{obj_id}_lc_mag.png"
                fig.savefig(out, dpi=120, bbox_inches="tight", facecolor=DARK_BG)
        elif plot_type == "cutouts":
            cutouts = dataset.get_cutouts(obj_id)
            meta    = dataset.get_meta(obj_id)
            fig, axes = plt.subplots(1, 3, figsize=(15, 5), facecolor=DARK_BG)
            plot_cutouts(cutouts, band=meta.get("r:band", "?"), axes=list(axes))
            fig.suptitle(
                f"Cutouts — diaObjectId {obj_id}  |  tag: {meta['fink_tag']}",
                color=TEXT_COL, fontsize=10, fontfamily="monospace",
            )
            if save:
                out = dataset.dataset_dir / f"{obj_id}_cutouts.png"
                fig.savefig(out, dpi=120, bbox_inches="tight", facecolor=DARK_BG)
        else:
            raise ValueError(
                f"Unknown plot_type '{plot_type}'. "
                "Choose from: 'overview', 'detail', 'lc_flux', 'lc_mag', 'cutouts'."
            )

        plt.show()
        if close_after:
            plt.close(fig)
