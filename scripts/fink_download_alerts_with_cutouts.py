"""
fink_download_alerts_with_cutouts.py
=====================================
Téléchargement d'alertes LSST/Rubin depuis le broker Fink avec :
  - métadonnées et scores Fink (via /api/v1/tags)
  - courbes de lumière multi-bande (via /api/v1/sources)
  - cutouts (Science, Template, Difference) (via /api/v1/cutouts)

API Fink LSST : https://api.lsst.fink-portal.org/api/v1
Swagger       : https://api.lsst.fink-portal.org/swagger.json

Différences majeures vs ZTF :
  - Pas de /latests : on utilise /tags (GET query params)
  - objectId → diaObjectId / diaSourceId
  - i:jd → r:midpointMjdTai  (MJD TAI)
  - i:fid (int 1/2) → r:band  (str parmi ugrizy — les 6 bandes Rubin LSST)
  - i:magpsf / i:sigmapsf → r:psfFlux / r:psfFluxErr  (en nJy, pas des magnitudes)
  - Cutouts : retournés en JSON (array 2D float32), pas en FITS gzippé
  - /cutouts prend diaSourceId (pas diaObjectId)

Convention de nommage des colonnes LSST (IMPORTANT) :
  - Préfixe 'r:' = champ de la table diaSource (schéma LSST DPDD)
                   !! PAS la bande spectrale r de Rubin !!
  - Préfixe 'f:' = champ calculé par Fink (classifieurs, cross-matches)
  - La bande spectrale est la VALEUR du champ r:band ∈ {u, g, r, i, z, y}

Auteur : dagoret
Date   : 2026-02
"""

import io
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from matplotlib import gridspec

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

FINK_API = "https://api.lsst.fink-portal.org/api/v1"

# Tags disponibles et leur label binaire (1=extragalactique, 0=autre/galactique)
# GET /api/v1/tags pour la liste complète
TAGS_CONFIG = {
    "extragalactic_new_candidate"  : 1,  # nouveau (< 48h) + extragalactique
    "extragalactic_lt20mag_candidate": 1, # rising, bright (mag < 20) + extragalactique
    "sn_near_galaxy_candidate"     : 1,  # proche galaxie + SNe-like
    "in_tns"                       : 1,  # contrepartie connue dans TNS
    "hostless_candidate"           : 0,  # sans hôte (ELEPHANT)
}

# Nombre d'alertes par tag à télécharger
N_PER_TAG = 200

# Colonnes à récupérer via /tags
# ATTENTION : le préfixe 'r:' est le nom de la table diaSource dans le schéma LSST,
#             il n'a aucun rapport avec la bande spectrale 'r' de Rubin.
#             La bande spectrale est la valeur de r:band ∈ {u, g, r, i, z, y}.
# Préfixe f: = champs calculés par Fink (classifieurs, cross-matches)
COLUMNS_TAGS = ",".join([
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
    "r:visit",
    # Scores classifieurs Fink LSST
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
])

# Colonnes pour les courbes de lumière (/sources)
# r:band contiendra la bande spectrale Rubin : u, g, r, i, z ou y
COLUMNS_SOURCES = ",".join([
    "r:diaObjectId",
    "r:diaSourceId",
    "r:midpointMjdTai",
    "r:band",
    "r:psfFlux",
    "r:psfFluxErr",
    "r:snr",
    "r:reliability",
])

# Répertoires de sortie
OUTPUT_DIR = Path("fink_dataset")
CUTOUT_DIR = OUTPUT_DIR / "cutouts"
LC_DIR     = OUTPUT_DIR / "lightcurves"
OUTPUT_DIR.mkdir(exist_ok=True)
CUTOUT_DIR.mkdir(exist_ok=True)
LC_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# FONCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def fetch_by_tag(tag: str, n: int) -> pd.DataFrame:
    """Récupère les n dernières alertes d'un tag donné."""
    print(f"  → Fetching {n} alerts for tag '{tag}' ...")
    r = requests.get(
        f"{FINK_API}/tags",
        params={
            "tag"          : tag,
            "n"            : n,
            "columns"      : COLUMNS_TAGS,
            "output-format": "json",
        },
        timeout=60,
    )
    if r.status_code != 200 or not r.text.strip():
        print(f"    ✗ Erreur HTTP {r.status_code} pour tag '{tag}'")
        return pd.DataFrame()
    try:
        df = pd.read_json(io.BytesIO(r.content))
    except Exception as e:
        print(f"    ✗ Erreur parsing JSON pour tag '{tag}': {e}")
        return pd.DataFrame()
    print(f"    ✓ {len(df)} alertes reçues")
    return df


def fetch_lightcurve(dia_object_id: int) -> pd.DataFrame:
    """
    Récupère la courbe de lumière complète d'un diaObjectId
    (toutes les diaSource associées).
    """
    r = requests.get(
        f"{FINK_API}/sources",
        params={
            "diaObjectId"  : dia_object_id,
            "columns"      : COLUMNS_SOURCES,
            "output-format": "json",
        },
        timeout=30,
    )
    if r.status_code != 200 or not r.text.strip():
        return pd.DataFrame()
    try:
        return pd.read_json(io.BytesIO(r.content))
    except Exception:
        return pd.DataFrame()


def fetch_cutouts(dia_source_id: int) -> dict | None:
    """
    Récupère les 3 cutouts (Science, Template, Difference) pour un diaSourceId.
    Retourne un dict {"Science": array2D, "Template": array2D, "Difference": array2D}
    ou None si erreur.

    Note : l'API retourne du JSON avec des arrays 2D (float32), pas du FITS gzippé.
    """
    cutouts = {}
    for kind in ["Science", "Template", "Difference"]:
        r = requests.get(
            f"{FINK_API}/cutouts",
            params={
                "diaSourceId"  : dia_source_id,
                "kind"         : kind,
                "output-format": "array",
            },
            timeout=30,
        )
        if r.status_code != 200 or not r.content:
            return None
        try:
            data = r.json()
            # L'API retourne {"b:cutoutScience": [[...], ...]} ou similaire
            key = list(data.keys())[0]
            cutouts[kind] = np.array(data[key], dtype=np.float32)
        except Exception as e:
            print(f"    ✗ Erreur cutout {kind} pour diaSourceId={dia_source_id}: {e}")
            return None
    return cutouts


def save_cutouts_npy(dia_object_id: int, cutouts: dict, label: int):
    """Sauvegarde les cutouts en .npy (shape: 3, H, W)."""
    arr = np.stack([
        cutouts["Science"],
        cutouts["Template"],
        cutouts["Difference"],
    ], axis=0)
    np.save(CUTOUT_DIR / f"{dia_object_id}_label{label}.npy", arr)


def flux_to_mag(flux, flux_err=None, zero_point=31.4):
    """
    Conversion psfFlux (nJy) → magnitude AB.

    Le flux Rubin/LSST est en nanoJansky (nJy), système photométrique AB.
    Le zero point est uniforme à 31.4 pour toutes les bandes (u, g, r, i, z, y)
    car le système AB est défini par : mag_AB = -2.5 * log10(f_nu / 3631 Jy)
    soit avec f_nu en nJy : mag_AB = -2.5 * log10(flux_nJy) + 31.4

    Note : cette fonction travaille sur des arrays numpy et gère flux <= 0
    (détections négatives dans les images de différence) en retournant NaN.
    """
    with np.errstate(invalid="ignore", divide="ignore"):
        mag = np.where(flux > 0, -2.5 * np.log10(flux) + zero_point, np.nan)
        if flux_err is not None:
            mag_err = np.where(flux > 0, 2.5 / np.log(10) * flux_err / flux, np.nan)
            return mag, mag_err
    return mag


def plot_alert_summary(dia_object_id: int, df_lc: pd.DataFrame,
                       cutouts: dict, label: int, tag: str):
    """Visualisation rapide : courbe de lumière (flux) + 3 cutouts."""
    fig = plt.figure(figsize=(14, 5))
    gs  = gridspec.GridSpec(1, 4, figure=fig, wspace=0.35)

    # Courbe de lumière en flux (nJy)
    # r:band contient la bande spectrale Rubin : u, g, r, i, z, y
    # (le préfixe 'r:' est le nom de table LSST, pas la bande r)
    ax_lc = fig.add_subplot(gs[0, 0])
    RUBIN_BAND_COLORS = {
        "u": "purple", "g": "green", "r": "red",
        "i": "darkorange", "z": "saddlebrown", "y": "black",
    }
    if not df_lc.empty and "r:band" in df_lc.columns:
        for band, color in RUBIN_BAND_COLORS.items():
            mask = df_lc["r:band"] == band
            if mask.sum() > 0:
                t = df_lc.loc[mask, "r:midpointMjdTai"]
                ax_lc.errorbar(
                    t - t.min(),
                    df_lc.loc[mask, "r:psfFlux"],       # flux en nJy
                    yerr=df_lc.loc[mask, "r:psfFluxErr"],  # incertitude en nJy
                    fmt="o", color=color, label=band, markersize=4,
                )
    ax_lc.axhline(0, color="gray", lw=0.5, ls="--")
    ax_lc.set_xlabel("ΔmjdTai (days)")
    ax_lc.set_ylabel("psfFlux (nJy)  [bandes u/g/r/i/z/y Rubin]")
    ax_lc.set_title(f"diaObj {dia_object_id}\n{tag} | label={'extragal' if label else 'other'}")
    ax_lc.legend(fontsize=7)

    # Cutouts
    for i, kind in enumerate(["Science", "Template", "Difference"]):
        ax = fig.add_subplot(gs[0, i + 1])
        img = cutouts[kind]
        vmin, vmax = np.nanpercentile(img, [1, 99])
        ax.imshow(img, origin="lower", cmap="gray", vmin=vmin, vmax=vmax)
        ax.set_title(kind, fontsize=9)
        ax.axis("off")

    plt.suptitle(f"Fink/LSST alert — diaObjectId={dia_object_id}", fontsize=10, y=1.02)
    plt.savefig(OUTPUT_DIR / f"{dia_object_id}_summary.png", bbox_inches="tight", dpi=100)
    plt.close()


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def main():
    all_meta     = []
    n_cutout_ok  = 0
    n_cutout_fail = 0
    n_plot       = 0

    for tag, label in TAGS_CONFIG.items():
        print(f"\n{'='*60}")
        print(f"Tag : {tag}  (label={label})")
        print(f"{'='*60}")

        # 1. Récupère la liste des alertes pour ce tag
        df_tag = fetch_by_tag(tag, N_PER_TAG)
        if df_tag.empty:
            continue

        df_tag["label"]    = label
        df_tag["fink_tag"] = tag

        # Dédoublonnage sur diaObjectId
        obj_ids = df_tag["r:diaObjectId"].unique()
        print(f"  → {len(obj_ids)} diaObjectIds uniques")

        for obj_id in obj_ids[:N_PER_TAG]:
            # diaSourceId : prendre la source la plus récente pour les cutouts
            rows = df_tag[df_tag["r:diaObjectId"] == obj_id]
            latest_row = rows.sort_values("r:midpointMjdTai").iloc[-1]
            src_id = int(latest_row["r:diaSourceId"])

            # 2. Courbe de lumière complète (toutes sources)
            df_lc = fetch_lightcurve(obj_id)
            if not df_lc.empty:
                df_lc.to_parquet(LC_DIR / f"{obj_id}.parquet", index=False)

            # 3. Cutouts (source la plus récente)
            cutouts = fetch_cutouts(src_id)
            if cutouts is not None:
                save_cutouts_npy(obj_id, cutouts, label)
                n_cutout_ok += 1

                # Visualisation pour les 3 premiers par tag
                if n_plot < 3 * len(TAGS_CONFIG):
                    try:
                        plot_alert_summary(obj_id, df_lc, cutouts, label, tag)
                        n_plot += 1
                    except Exception as e:
                        print(f"    ✗ Plot échoué pour {obj_id}: {e}")
            else:
                n_cutout_fail += 1
                print(f"    ✗ Cutouts indisponibles pour diaSourceId={src_id}")

        all_meta.append(df_tag)

    # ── Sauvegarde du catalogue complet ──────────────────────────────────────
    print(f"\n{'='*60}")
    if all_meta:
        df_all = pd.concat(all_meta, ignore_index=True)
        df_all.to_parquet(OUTPUT_DIR / "alerts_catalog.parquet", index=False)
        df_all.to_csv(OUTPUT_DIR / "alerts_catalog.csv", index=False)
        print(f"✓ Catalogue sauvegardé : {len(df_all)} alertes")
        print(f"  → {OUTPUT_DIR / 'alerts_catalog.parquet'}")

        # Résumé par tag
        print("\nRésumé par tag :")
        print(df_all.groupby("fink_tag")[["r:diaObjectId", "label"]].agg(
            n_alerts=("r:diaObjectId", "count"),
            label=("label", "first"),
        ).to_string())

    print(f"\n✓ Cutouts réussis  : {n_cutout_ok}")
    print(f"✗ Cutouts échoués  : {n_cutout_fail}")
    print(f"\nDataset dans : {OUTPUT_DIR.resolve()}")
    print("Structure :")
    print("  fink_dataset/")
    print("    alerts_catalog.parquet   # métadonnées + scores Fink")
    print("    alerts_catalog.csv       # idem en CSV")
    print("    cutouts/                 # arrays .npy shape (3, H, W)")
    print("    lightcurves/             # courbes de lumière .parquet par diaObjectId")
    print("    *_summary.png            # visualisations rapides")


if __name__ == "__main__":
    print(f"Fink API (LSST) : {FINK_API}")
    print(f"Tags     : {list(TAGS_CONFIG.keys())}")
    print(f"N/tag    : {N_PER_TAG}")
    print(f"Output   : {OUTPUT_DIR.resolve()}")
    print()
    main()
