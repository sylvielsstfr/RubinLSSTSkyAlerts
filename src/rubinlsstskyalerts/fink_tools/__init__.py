"""
rubinlsstskyalerts.fink_tools
==============================
Sub-package regroupant les outils Fink/LSST pour :
  - la visualisation d'alertes (fink_alert_lib)
  - la cartographie céleste (fink_skymap_lib)
  - le téléchargement de datasets par tag (fink_download_tag_dataset)
  - le téléchargement d'alertes avec cutouts (fink_download_alerts_with_cutouts)
  - le téléchargement exhaustif des cutouts (fink_download_full_cutouts)

Usage depuis un notebook ou un script quelconque :
    from rubinlsstskyalerts.fink_tools import FinkDataset, plot_alert_detail
    from rubinlsstskyalerts.fink_tools import plot_skymap_rect, load_catalog
    from rubinlsstskyalerts.fink_tools import download_dataset, fetch_cutouts
"""

# ── fink_alert_lib ────────────────────────────────────────────────────────────
from .fink_alert_lib import (
    # Constants – bands
    BAND_COLORS,
    BAND_WAVELENGTHS,
    RUBIN_ZEROPOINT,
    # Constants – dark theme colours
    DARK_BG,
    PANEL_BG,
    TEXT_COL,
    MUTED_COL,
    ACCENT,
    HIGHLIGHT,
    BORDER,
    # Dataset class
    FinkDataset,
    # Photometric utilities
    flux_to_mag,
    # Plot functions
    plot_lightcurve_flux,
    plot_lightcurve_mag,
    plot_cutouts,
    plot_classifiers,
    plot_alert_overview,
    plot_alert_detail,
    plot_tag_grid,
    plot_tag_loop,
)

# ── fink_skymap_lib ───────────────────────────────────────────────────────────
from .fink_skymap_lib import (
    # Constants – tag styles
    TAG_STYLES,
    DEFAULT_TAG_STYLE,
    RUBIN_DDF,
    # Constants – dark theme colours (skymap variants)
    DARK_BG as _DARK_BG_SKY,       # même valeur, évite collision de nom
    PANEL_BG as _PANEL_BG_SKY,
    TEXT_COL as _TEXT_COL_SKY,
    MUTED_COL as _MUTED_COL_SKY,
    BORDER_COL,
    GRID_COL,
    GALPLANE_COL,
    GALBAND_COL,
    GALCENTER_COL,
    DDF_COL,
    # Coordinate utilities
    galactic_plane_radec,
    galactic_latitude_radec,
    _split_segments,
    ra_deg_to_hms,
    _ra_to_moll,
    _dec_to_moll,
    # Data loading
    load_catalog,
    catalog_summary,
    # HiPS background
    fetch_hips_image,
    overlay_hips_background,
    # Grid
    draw_radec_grid,
    # Legend helper
    _build_legend,
    # Plot functions
    plot_skymap_rect,
    plot_skymap_mollweide,
    plot_skymap_combined,
)

# ── fink_download_tag_dataset ─────────────────────────────────────────────────
from .fink_download_tag_dataset import (
    FINK_TAGS,
    fetch_latest_alerts,
    fetch_light_curve,
    fetch_cutouts,
    download_dataset,
    list_tags,
)

# ── fink_download_alerts_with_cutouts ─────────────────────────────────────────
from .fink_download_alerts_with_cutouts import (
    TAGS_CONFIG,
    fetch_by_tag,
    fetch_lightcurve,
    fetch_cutouts as fetch_cutouts_raw,
    save_cutouts_npy,
    plot_alert_summary,
)

# ── fink_download_full_cutouts ────────────────────────────────────────────────
from .fink_download_full_cutouts import (
    fetch_sources,
    fetch_single_cutout,
    fetch_all_cutouts,
    download_full_cutouts,
)

__all__ = [
    # alert lib – constants
    "BAND_COLORS", "BAND_WAVELENGTHS", "RUBIN_ZEROPOINT",
    "DARK_BG", "PANEL_BG", "TEXT_COL", "MUTED_COL", "ACCENT", "HIGHLIGHT", "BORDER",
    # alert lib – classes & functions
    "FinkDataset",
    "flux_to_mag",
    "plot_lightcurve_flux", "plot_lightcurve_mag",
    "plot_cutouts", "plot_classifiers",
    "plot_alert_overview", "plot_alert_detail",
    "plot_tag_grid", "plot_tag_loop",
    # skymap lib – constants
    "TAG_STYLES", "DEFAULT_TAG_STYLE", "RUBIN_DDF",
    "BORDER_COL", "GRID_COL",
    "GALPLANE_COL", "GALBAND_COL", "GALCENTER_COL", "DDF_COL",
    # skymap lib – coordinate utilities
    "galactic_plane_radec", "galactic_latitude_radec",
    "_split_segments", "ra_deg_to_hms", "_ra_to_moll", "_dec_to_moll",
    # skymap lib – data & plot
    "load_catalog", "catalog_summary",
    "fetch_hips_image", "overlay_hips_background", "draw_radec_grid",
    "_build_legend",
    "plot_skymap_rect", "plot_skymap_mollweide", "plot_skymap_combined",
    # download – tag dataset
    "FINK_TAGS",
    "fetch_latest_alerts", "fetch_light_curve", "fetch_cutouts",
    "download_dataset", "list_tags",
    # download – alerts with cutouts
    "TAGS_CONFIG",
    "fetch_by_tag", "fetch_lightcurve", "fetch_cutouts_raw",
    "save_cutouts_npy", "plot_alert_summary",
    # download – full cutouts
    "fetch_sources", "fetch_single_cutout", "fetch_all_cutouts",
    "download_full_cutouts",
]
