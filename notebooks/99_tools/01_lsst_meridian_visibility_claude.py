"""
lsst_meridian_visibility.py  v2
────────────────────────────────────────────────────────────────────────────
RA culminant au méridien local d'El Pachón à minuit local, en fonction du MJD.

v2 : suppression de l'artefact de fond (dégradé noir→marron→jaune) dû à
     l'accumulation de axvspan semi-transparents superposés. On utilise des
     matplotlib.patches.Rectangle précis, limités à la fenêtre ±HALF_WINDOW_DEG
     en RA, ce qui évite toute accumulation de transparences parasites sur le fond.

Dépendances : numpy, matplotlib uniquement (pas d'astropy).
────────────────────────────────────────────────────────────────────────────
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.patches as mpatches
from datetime import datetime, timedelta

# ═══════════════════════════════════════════════════════════════════════════
# PARAMÈTRES UTILISATEUR
# ═══════════════════════════════════════════════════════════════════════════
DATE_START      = "2025-04-01"   # début de la plage (ISO YYYY-MM-DD)
DATE_END        = "2026-04-01"   # fin   de la plage
LON_DEG         = -70.7494       # El Pachón longitude Est (négatif = Ouest)
LAT_DEG         = -30.2444
ALT_M           = 2663.0
UTC_OFFSET_H    = 3.0            # CLT = UTC−3 ; minuit local = 03:00 UTC
HALF_WINDOW_DEG = 30.0           # ±30° en RA ≈ ±2h d'angle horaire

DEEP_FIELDS = {
    "COSMOS"  : (150.1191,   2.2058),
    "ELAIS-S1": (  9.4500, -44.0000),
    "XMM-LSS" : ( 35.7080,  -4.7500),
    "ECDFS"   : ( 53.1250, -27.8000),
    "EDFS-a"  : ( 58.9000, -49.3150),
    "EDFS-b"  : ( 63.6000, -47.6000),
    "M49"     : (187.4000,   8.0000),
}
FIELD_COLORS = [
    "#e74c3c", "#3498db", "#2ecc71", "#e67e22",
    "#9b59b6", "#1abc9c", "#f39c12",
]

# ═══════════════════════════════════════════════════════════════════════════
# FONCTIONS
# ═══════════════════════════════════════════════════════════════════════════
def iso_to_mjd(s):
    """Date ISO (YYYY-MM-DD) → MJD UTC."""
    dt = datetime.strptime(s, "%Y-%m-%d")
    y, m, d = dt.year, dt.month, dt.day
    jd = 367*y - (7*(y+(m+9)//12))//4 + 275*m//9 + d + 1721013.5
    return jd - 2400000.5

def gmst_deg(mjd):
    """GMST en degrés [0,360) depuis le MJD UTC — formule IAU 1982."""
    D = mjd - 51544.5
    T = D / 36525.0
    g = (280.46061837 + 360.98564736629*D
         + 0.000387933*T**2 - T**3/38710000.0)
    return g % 360.0

def lst_deg(mjd, lon):
    """Temps Sidéral Local en degrés [0,360)."""
    return (gmst_deg(mjd) + lon) % 360.0

# ═══════════════════════════════════════════════════════════════════════════
# CALCUL
# ═══════════════════════════════════════════════════════════════════════════
mjd_start  = iso_to_mjd(DATE_START)
mjd_end    = iso_to_mjd(DATE_END)
n_nights   = int(np.ceil(mjd_end - mjd_start))
mjd_nights = mjd_start + np.arange(n_nights, dtype=float)
mjd_mid    = mjd_nights + UTC_OFFSET_H / 24.0
ra_merid   = lst_deg(mjd_mid, LON_DEG)    # RA au méridien, 0–360°

# ═══════════════════════════════════════════════════════════════════════════
# FIGURE
# ═══════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(15, 7.5))
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#0d1117")

# ── Champs DDF : bandes de visibilité via Rectangle (pas axvspan) ─────────
# Raison : axvspan couvre toute la hauteur de l'axe et les couches semi-
# transparentes s'accumulent sur le fond, créant un dégradé parasite.
# Rectangle permet de limiter la bande à ±HALF_WINDOW_DEG en RA exactement.
for (name, (ra, dec)), color in zip(DEEP_FIELDS.items(), FIELD_COLORS):

    ax.axhline(ra, color=color, lw=0.7, ls="--", alpha=0.6, zorder=2)

    diff    = ((ra_merid - ra) + 180) % 360 - 180
    visible = np.abs(diff) < HALF_WINDOW_DEG

    pad    = np.concatenate([[False], visible, [False]])
    starts = np.where(~pad[:-1] & pad[1:])[0]
    ends   = np.where(pad[:-1]  & ~pad[1:])[0]

    for s, e in zip(starts, ends):
        x0 = mjd_nights[s]
        x1 = mjd_nights[min(e, n_nights-1)] + 1.0
        rect = mpatches.Rectangle(
            (x0, ra - HALF_WINDOW_DEG),
            x1 - x0,
            2 * HALF_WINDOW_DEG,
            linewidth=0, facecolor=color, alpha=0.18, zorder=1,
        )
        ax.add_patch(rect)

    ax.annotate(
        f" {name}  RA={ra:.1f}°",
        xy=(1.002, ra / 360.0),
        xycoords=("axes fraction", "axes fraction"),
        fontsize=7.8, color=color, va="center",
        fontweight="bold", annotation_clip=False,
    )

# ── Courbe principale ────────────────────────────────────────────────────
ax.plot(mjd_nights, ra_merid, color="#58a6ff", lw=1.6, zorder=5,
        label="RA au méridien (minuit local CLT)")

# ─── Axes ────────────────────────────────────────────────────────────────
ax.set_xlim(mjd_nights[0], mjd_nights[-1])
ax.set_ylim(0, 360)
ax.set_xlabel("MJD (UTC)", color="white", fontsize=11, labelpad=6)
ax.xaxis.set_major_locator(ticker.MultipleLocator(30))
ax.xaxis.set_minor_locator(ticker.MultipleLocator(10))
ax.tick_params(axis="x", which="both", colors="white", labelsize=9)

ax_top = ax.twiny()
ax_top.set_xlim(ax.get_xlim())
epoch, tick_mjds, tick_labels = datetime(1858, 11, 17), [], []
dt, dt_end = (datetime.strptime(DATE_START, "%Y-%m-%d").replace(day=1),
              datetime.strptime(DATE_END, "%Y-%m-%d"))
while dt <= dt_end:
    m = (dt - epoch).total_seconds() / 86400.0
    if mjd_nights[0] <= m <= mjd_nights[-1]:
        tick_mjds.append(m); tick_labels.append(dt.strftime("%Y-%m-%d"))
    mo = dt.month + 1 if dt.month < 12 else 1
    yr = dt.year + (1 if dt.month == 12 else 0)
    dt = dt.replace(year=yr, month=mo, day=1)
ax_top.set_xticks(tick_mjds)
ax_top.set_xticklabels(tick_labels, rotation=35, ha="left", fontsize=8.5)
ax_top.tick_params(axis="x", colors="#adbac7", labelsize=8.5)
ax_top.set_facecolor("#0d1117")

ax.set_ylabel("Ascension droite au méridien [°]", color="white", fontsize=11)
yticks = np.arange(0, 361, 30)
ax.set_yticks(yticks)
ax.set_yticklabels([f"{d:.0f}°  ({d/15:.0f}h)" for d in yticks], fontsize=8.2)
ax.tick_params(axis="y", which="both", colors="white", labelsize=8.5)
ax.yaxis.set_minor_locator(ticker.MultipleLocator(10))

ax_r = ax.twinx()
ax_r.set_ylim(0, 24)
ax_r.set_ylabel("Ascension droite au méridien [h]", color="#adbac7", fontsize=10)
ax_r.yaxis.set_major_locator(ticker.MultipleLocator(2))
ax_r.yaxis.set_minor_locator(ticker.MultipleLocator(1))
ax_r.tick_params(axis="y", which="both", colors="#adbac7", labelsize=9)
ax_r.set_facecolor("#0d1117")

ax.grid(True, which="major", color="#30363d", lw=0.7, zorder=0)
ax.grid(True, which="minor", color="#21262d", lw=0.4, zorder=0)

ax.set_title(
    f"Visibilité nocturne — El Pachón  (Rubin/LSST)\n"
    f"RA culminant au méridien à minuit local (CLT = UTC−3)   ·   "
    f"{DATE_START}  →  {DATE_END}   ·   MJD {int(mjd_start)}–{int(mjd_end)}",
    color="white", fontsize=11.5, pad=10)
ax.legend(loc="upper left", fontsize=9, framealpha=0.35,
          facecolor="#161b22", edgecolor="#30363d", labelcolor="white")
ax.text(0.01, 0.015,
        "TSL calculé via IAU 1982 (GMST)  ·  "
        f"El Pachón : lon={LON_DEG}°, lat={LAT_DEG}°, alt={ALT_M:.0f} m  ·  "
        f"Bandes : fenêtre ±{HALF_WINDOW_DEG:.0f}° en RA",
        transform=ax.transAxes, fontsize=6.8, color="#768390", va="bottom")

plt.tight_layout(rect=[0, 0, 0.91, 1])

import os
out_dir = os.path.dirname(os.path.abspath(__file__))
for ext, kw in [("png", {"dpi": 160}), ("pdf", {})]:
    path = os.path.join(out_dir, f"lsst_meridian_visibility.{ext}")
    plt.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor(), **kw)
    print(f"Saved: {path}")
plt.show()
