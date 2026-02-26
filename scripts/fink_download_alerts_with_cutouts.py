"""
fink_download_alerts_with_cutouts.py
=====================================
Téléchargement d'alertes ZTF depuis le broker Fink avec :
  - courbes de lumière multi-bande (g, r)
  - cutouts (Science, Template, Difference)
  - scores des classifieurs Fink (snn, rf, drb...)

Objectif : constituer un dataset d'entraînement pour un classifieur
multimodal (CNN + Transformer) orienté LSST/Rubin.

API Fink (depuis janvier 2025) : https://api.fink-portal.org
Doc interactive                 : https://api.fink-portal.org
Tutoriels                       : https://github.com/astrolabsoftware/fink-tutorials

Auteur : dagoret
Date   : 2026-02
"""

import io
import os
import gzip
import datetime
import requests
import numpy as np
import pandas as pd
from pathlib import Path
from astropy.io import fits
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

FINK_API = "https://api.fink-portal.org/api/v1"

# Classes à télécharger et leur label binaire (1=extragalactique, 0=autre)
CLASSES_CONFIG = {
    "SN candidate"       : 1,   # candidats SN — extragalactique
    "Early SN Ia candidate": 1, # SN Ia précoces — extragalactique
    "QSO"                : 1,   # quasars — extragalactique
    "AGN"                : 1,   # AGN — extragalactique
    "RRLyrae"            : 0,   # variables galactiques
    "EclBin"             : 0,   # binaires à éclipses — galactique
    "LongPeriodV*"       : 0,   # Miras etc. — galactique
    "Star"               : 0,   # étoiles non classifiées
}

# Nombre d'alertes par classe à télécharger
N_PER_CLASS = 200

# Fenêtre temporelle (pour éviter de tout télécharger)
STARTDATE = "2025-01-01"
STOPDATE  = "2026-02-25"

# Colonnes photométriques + scores Fink à récupérer
COLUMNS = ",".join([
    "i:objectId",
    "i:candid",
    "i:jd",
    "i:ra",
    "i:dec",
    "i:fid",           # filtre : 1=g, 2=r
    "i:magpsf",
    "i:sigmapsf",
    "i:magnr",         # magnitude de la source de référence
    "i:distnr",        # distance à la source de référence (arcsec)
    "i:distpsnr1",     # distance au PS1 le plus proche
    "i:sgscore1",      # score star/galaxy PS1 [0=étoile, 1=galaxie]
    "i:classtar",      # SExtractor star/galaxy
    "i:rb",            # Real/Bogus ZTF CNN (braai)
    "i:drb",           # Deep Real/Bogus ZTF
    "i:ndethist",      # nombre de détections historiques
    "i:isdiffpos",     # signe de la différence
    "d:rf_snia_vs_nonia",   # Random Forest SN Ia vs non-Ia
    "d:snn_snia_vs_nonia",  # SuperNNova SN Ia vs non-Ia
    "d:snn_sn_vs_all",      # SuperNNova SN vs tout
    "d:cdsxmatch",          # cross-match SIMBAD
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

def fetch_latests(class_name: str, n: int, startdate: str, stopdate: str) -> pd.DataFrame:
    """Récupère les n dernières alertes d'une classe donnée."""
    print(f"  → Fetching {n} alerts for class '{class_name}' ...")
    r = requests.post(
        f"{FINK_API}/latests",
        json={
            "class"      : class_name,
            "n"          : n,
            "columns"    : COLUMNS,
            "startdate"  : startdate,
            "stopdate"   : stopdate,
            "output-format": "json",
        },
        timeout=60,
    )
    if r.status_code != 200 or not r.text.strip():
        print(f"    ✗ Erreur HTTP {r.status_code} pour '{class_name}'")
        return pd.DataFrame()
    df = pd.read_json(io.BytesIO(r.content))
    print(f"    ✓ {len(df)} alertes reçues")
    return df


def fetch_cutouts(object_id: str) -> dict:
    """
    Récupère les 3 cutouts (Science, Template, Difference) pour un objectId.
    Retourne un dict {"Science": array2D, "Template": array2D, "Difference": array2D}
    ou None si erreur.
    
    Note : le cutout le plus récent est retourné par défaut.
    """
    cutouts = {}
    for kind in ["Science", "Template", "Difference"]:
        r = requests.post(
            f"{FINK_API}/cutouts",
            json={
                "objectId"     : object_id,
                "kind"         : kind,
                "output-format": "array",   # retourne un array numpy sérialisé
            },
            timeout=30,
        )
        if r.status_code != 200 or not r.content:
            return None
        # Le contenu est un fichier FITS gzippé
        try:
            with gzip.open(io.BytesIO(r.content)) as f:
                with fits.open(f) as hdul:
                    cutouts[kind] = hdul[0].data.astype(np.float32)
        except Exception as e:
            print(f"    ✗ Erreur cutout {kind} pour {object_id}: {e}")
            return None
    return cutouts


def save_cutouts_npy(object_id: str, cutouts: dict, label: int):
    """Sauvegarde les cutouts en .npy pour un objectId."""
    arr = np.stack([
        cutouts["Science"],
        cutouts["Template"],
        cutouts["Difference"],
    ], axis=0)  # shape: (3, H, W)
    np.save(CUTOUT_DIR / f"{object_id}_label{label}.npy", arr)


def plot_alert_summary(object_id: str, df_lc: pd.DataFrame, cutouts: dict, label: int):
    """Visualisation rapide : courbe de lumière + 3 cutouts."""
    fig = plt.figure(figsize=(14, 5))
    gs  = gridspec.GridSpec(1, 4, figure=fig, wspace=0.35)

    # Courbe de lumière
    ax_lc = fig.add_subplot(gs[0, 0])
    band_colors = {1: ("g", "green"), 2: ("r", "red")}
    df_lc_valid = df_lc[df_lc["d:tag"] == "valid"] if "d:tag" in df_lc.columns else df_lc
    for fid, (band_name, color) in band_colors.items():
        mask = df_lc_valid["i:fid"] == fid
        if mask.sum() > 0:
            ax_lc.errorbar(
                df_lc_valid.loc[mask, "i:jd"] - df_lc_valid["i:jd"].min(),
                df_lc_valid.loc[mask, "i:magpsf"],
                yerr=df_lc_valid.loc[mask, "i:sigmapsf"],
                fmt="o", color=color, label=band_name, markersize=4,
            )
    ax_lc.invert_yaxis()
    ax_lc.set_xlabel("JD - JD0")
    ax_lc.set_ylabel("mag PSF")
    ax_lc.set_title(f"{object_id}\nlabel={'extragal' if label else 'galactic/other'}")
    ax_lc.legend(fontsize=8)

    # Cutouts
    for i, kind in enumerate(["Science", "Template", "Difference"]):
        ax = fig.add_subplot(gs[0, i + 1])
        img = cutouts[kind]
        vmin, vmax = np.nanpercentile(img, [1, 99])
        ax.imshow(img, origin="lower", cmap="gray", vmin=vmin, vmax=vmax)
        ax.set_title(kind, fontsize=9)
        ax.axis("off")

    plt.suptitle(f"Fink alert — {object_id}", fontsize=11, y=1.02)
    plt.savefig(OUTPUT_DIR / f"{object_id}_summary.png", bbox_inches="tight", dpi=100)
    plt.close()


def fetch_full_lightcurve(object_id: str) -> pd.DataFrame:
    """Récupère la courbe de lumière complète d'un objet (toutes alertes historiques)."""
    r = requests.post(
        f"{FINK_API}/objects",
        json={
            "objectId"     : object_id,
            "columns"      : COLUMNS,
            "output-format": "json",
        },
        timeout=30,
    )
    if r.status_code != 200 or not r.text.strip():
        return pd.DataFrame()
    return pd.read_json(io.BytesIO(r.content))


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def main():
    all_meta = []
    n_cutout_ok = 0
    n_cutout_fail = 0

    for class_name, label in CLASSES_CONFIG.items():
        print(f"\n{'='*60}")
        print(f"Classe : {class_name}  (label={label})")
        print(f"{'='*60}")

        # 1. Récupère la liste des alertes (sans cutouts, rapide)
        df_class = fetch_latests(class_name, N_PER_CLASS, STARTDATE, STOPDATE)
        if df_class.empty:
            continue

        df_class["label"]      = label
        df_class["class_name"] = class_name

        # Dédoublonnage sur objectId (on veut 1 entrée par objet)
        object_ids = df_class["i:objectId"].unique()
        print(f"  → {len(object_ids)} objets uniques")

        for obj_id in object_ids[:N_PER_CLASS]:  # limite stricte
            # 2. Courbe de lumière complète
            df_lc = fetch_full_lightcurve(obj_id)
            if not df_lc.empty:
                df_lc.to_parquet(LC_DIR / f"{obj_id}.parquet", index=False)

            # 3. Cutouts (le plus récent par défaut)
            cutouts = fetch_cutouts(obj_id)
            if cutouts is not None:
                save_cutouts_npy(obj_id, cutouts, label)
                n_cutout_ok += 1

                # Visualisation pour les 5 premiers de chaque classe
                if n_cutout_ok <= 5 and not df_lc.empty:
                    try:
                        plot_alert_summary(obj_id, df_lc, cutouts, label)
                    except Exception as e:
                        print(f"    ✗ Plot échoué pour {obj_id}: {e}")
            else:
                n_cutout_fail += 1
                print(f"    ✗ Cutouts indisponibles pour {obj_id}")

        all_meta.append(df_class)

    # Sauvegarde du catalogue complet
    print(f"\n{'='*60}")
    if all_meta:
        df_all = pd.concat(all_meta, ignore_index=True)
        df_all.to_parquet(OUTPUT_DIR / "alerts_catalog.parquet", index=False)
        df_all.to_csv(OUTPUT_DIR / "alerts_catalog.csv", index=False)
        print(f"✓ Catalogue sauvegardé : {len(df_all)} alertes")
        print(f"  → {OUTPUT_DIR / 'alerts_catalog.parquet'}")

    print(f"\n✓ Cutouts réussis  : {n_cutout_ok}")
    print(f"✗ Cutouts échoués  : {n_cutout_fail}")
    print(f"\nDataset dans : {OUTPUT_DIR.resolve()}")
    print("Structure :")
    print("  fink_dataset/")
    print("    alerts_catalog.parquet   # métadonnées + scores Fink")
    print("    cutouts/                 # arrays .npy shape (3, H, W)")
    print("    lightcurves/             # courbes de lumière .parquet par objet")
    print("    *_summary.png            # visualisations rapides")


if __name__ == "__main__":
    print(f"Fink API : {FINK_API}")
    print(f"Période  : {STARTDATE} → {STOPDATE}")
    print(f"Classes  : {list(CLASSES_CONFIG.keys())}")
    print(f"N/classe : {N_PER_CLASS}")
    print(f"Output   : {OUTPUT_DIR.resolve()}")
    print()
    main()
