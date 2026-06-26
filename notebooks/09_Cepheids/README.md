# 09_Cepheids — Recherche d'étoiles Céphéides dans les alertes Fink/LSST

**Author:** Sylvie Dagoret-Campagne — IJCLab / IN2P3 / CNRS — Université Paris-Saclay  
**Created:** 2026-06-15  
**Context:** Rubin/LSST Fink broker — Deep Drilling Fields + galactic survey fields

---

## Objectif scientifique

Ce répertoire explore la détection de **Céphéides** (étoiles variables pulsantes)
dans le flux d'alertes LSST traité par le broker [Fink](https://api.lsst.fink-portal.org).

Les Céphéides sont des **indicateurs de distance standards** (loi de Leavitt :
log P vs M<sub>abs</sub>) et des cas tests idéaux pour valider la pipeline
photométrique LSST :

- courbe de lumière caractéristique en dents de scie, bien répétable,
- périodes de quelques jours à quelques centaines de jours,
- amplitude multi-bande exploitable pour la loi P–L,
- périodes connues dans les catalogues GCVS, VSX, OGLE — permettent la validation.

---

## Notebooks

### `01_cepheids_in_DDF.ipynb` — Recherche initiale dans les DDFs

Recherche de Céphéides dans les **six Deep Drilling Fields extragalactiques** de LSST
(COSMOS, ELAIS-S1, XMM-LSS, ECDFS, EDFS, M49) via le Fink API.

**Stratégie :**

1. Cone-search de chaque DDF via `/api/v1/conesearch` (rayon 1°, `nDiaSources ≥ 50`).
2. Déduplication par `diaObjectId`.
3. Sélection des Céphéides par croisement sur :
   - `f:xm_simbad_otype` : types SIMBAD `Cep`, `deltaCep`, `WVir`, `bCep`
   - `f:xm_gcvs_type` et `f:xm_vsx_Type` : codes VSX/GCVS
   - colonne `cdsxmatch` : `"Cepheid"`, `"Classical Cepheid"`, `"Type II Cepheid"`
4. Téléchargement des courbes de lumière complètes via `/api/v1/sources` + `/api/v1/fp`.
5. Recherche de période par **Lomb-Scargle** (`astropy.timeseries.LombScargle`),
   sur la grille P ∈ [0.5, 100] jours.
6. Courbes de lumière repliées à la période meilleure.
7. Exploration du **diagramme Période–Luminosité** (loi de Leavitt).

> **Résultat :** aucune Céphéide MW trouvée dans les DDFs extragalactiques —
> résultat attendu (voir notebook 02 pour l'explication).

**Colonnes Fink utilisées :**

| Préfixe | Signification |
|---------|---------------|
| `r:` | champ LSST diaSource/diaObject (table Rubin) |
| `f:xm_simbad_otype` | type d'objet SIMBAD (croisement < 1″) |
| `f:xm_gcvs_type` | type GCVS (croisement < 1″) |
| `f:xm_vsx_Type` | type VSX (croisement < 1″) |
| `f:xm_gaiadr3_*` | Gaia DR3 (parallaxe, drapeau variabilité) |
| `f:clf_cats_class` | classification CATS (21 = Periodic) |

Sorties dans `data_CEPHEIDS_DDF_01/` et `figs_CEPHEIDS_DDF_01/`.

---

### `02_cepheids_extended_search.ipynb` — Recherche étendue : DDFs + champs galactiques

Notebook de suivi motivé par l'échec du notebook 01 :
les DDFs LSST sont extragalactiques — les Céphéides MW classiques
(brillantes, connues dans SIMBAD/GCVS) se trouvent dans les
**champs galactiques du programme SV Rubin**.

**Champs ajoutés :**

| Champ | Type | RA (deg) | Dec (deg) | Rayon |
|-------|------|----------|-----------|-------|
| Carina | galactique | 161.5 | −59.7 | 3° |
| Trifid-Lagoon | galactique | 270.5 | −23.0 | 3° |
| Rubin_SV_280_−48 | SV | 280.0 | −48.0 | 1° |
| Rubin_SV_320_−15 | SV | 320.0 | −15.0 | 1° |
| Rubin_SV_225_−40 | SV | 225.0 | −40.0 | 1° |

**Stratégie étendue :**

1. Cone-search adaptatif (1° pour DDFs, 3° pour champs galactiques).
2. Tag `/api/v1/tags?tag=cataloged` pour récupérer tous les objets
   croisés avec un catalogue.
3. Filtrage élargi incluant **toute la bande d'instabilité** :
   RR Lyrae (`RRAB`, `RRC`, `RRD`), delta Scuti (`DSCT`, `SXPHE`),
   Mira/LPV (`M`, `SR*`), RV Tauri (`RVA`, `RVB`), beta Céphéi (`BCEP`),
   en plus des Céphéides classiques (`CEP`, `DCEP`, `CW`, `ACEP`).
4. Inspection du schéma API complet via `/api/v1/schema`.
5. Résolution par nom via `/api/v1/resolver?resolver=simbad&name_or_id=…`
   pour les Céphéides GCVS connues dans l'empreinte LSST.
6. Lomb-Scargle étendu : P ∈ [0.3, 200] jours, sur-échantillonnage × 20.

**Types pulsants ciblés (VSX/GCVS) :**

`CEP`, `DCEP`, `DCEPS`, `CW`, `CWA`, `CWB`, `ACEP`, `RRAB`, `RRC`, `RRD`,
`DSCT`, `SXPHE`, `M`, `SR*`, `RV`, `BCEP`, `BLBOO`, `WVir`.

Sorties dans `data_CEPHEIDS_DDF_02/` et `figs_CEPHEIDS_DDF_02/`.

---

## Fichiers ancillaires

| Fichier / Répertoire | Description |
|----------------------|-------------|
| `swagger.json` | Schéma OpenAPI complet de l'API Fink LSST (utilisé pour explorer les endpoints disponibles) |
| `data_CEPHEIDS_DDF_01/` | Données produites par le notebook 01 |
| `data_CEPHEIDS_DDF_02/` | Données produites par le notebook 02 |
| `figs_CEPHEIDS_DDF_01/` | Figures produites par le notebook 01 |
| `figs_CEPHEIDS_DDF_02/` | Figures produites par le notebook 02 |

---

## Notes sur la recherche de Céphéides dans LSST DP2

Les DDFs LSST étant extragalactiques, les Céphéides MW brillantes
(les seules répertoriées dans SIMBAD avec un nom propre) ne s'y trouvent pas.
Les Céphéides extragalactiques (par exemple dans M101 ou les nuages de Magellan)
sont typiquement au-delà de m > 25 dans les bandes optiques — à la limite
de sensibilité de LSST — et ne possèdent pas de croisement SIMBAD à < 1″.

Les champs galactiques SV (Carina, Trifid-Lagoon) constituent donc la cible
principale pour une détection robuste dans Fink/LSST DP2.

---

## Environnement logiciel

Python 3.13, kernel `conda_py313`.  
Dépendances principales : `astropy` (LombScargle, Time), `matplotlib`, `pandas`, `numpy`, `requests`, `ipympl`.
