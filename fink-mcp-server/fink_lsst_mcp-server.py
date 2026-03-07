"""
Fink/LSST MCP Server v2
========================
Serveur MCP pour accéder à l'API Fink/LSST (https://api.lsst.fink-portal.org)
Basé sur le swagger officiel v2.5.0

Endpoints couverts :
  /api/v1/sources     — courbes de lumière par diaObjectId (diaSources)
  /api/v1/objects     — données agrégées par diaObjectId (diaObjects)
  /api/v1/fp          — photométrie forcée par diaObjectId
  /api/v1/conesearch  — recherche spatiale RA/Dec/radius
  /api/v1/cutouts     — vignettes par diaSourceId
  /api/v1/sso         — objets Système Solaire (astéroïdes, comètes)
  /api/v1/schema      — schéma des colonnes d'un endpoint
  /api/v1/statistics  — statistiques par nuit/mois/année
  /api/v1/tags        — dernières alertes par tag Fink
  /api/v1/resolver    — résolution de noms (Simbad, TNS, SSodnet)
  /api/v1/skymap      — alertes dans une skymap d'onde gravitationnelle
  /api/v1/classes     — liste des classes disponibles (GET simple)
  /api/v1/blocks      — définition des blocs (GET simple)

Installation:
    pip install mcp httpx

Lancement (test avec MCP Inspector) :
    cd /dossier/du/fichier
    npx @modelcontextprotocol/inspector python fink_lsst_mcp.py

Configuration Claude Desktop :
    {
      "mcpServers": {
        "fink-lsst": {
          "command": "/Users/dagoret/miniconda3/envs/conda_py3120_fink/bin/python",
          "args": ["/Users/dagoret/MacOSX/GitHub/LSST/2026/fink/RubinLSSTSkyAlerts/fink-mcp-server/fink_lsst_mcp-server.py"]
        }
      }
    }
"""

import json

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

# ─────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────

BASE_URL = "https://api.lsst.fink-portal.org/api/v1"
TIMEOUT = 30.0

# ─────────────────────────────────────────────────────────────
# Initialisation
# ─────────────────────────────────────────────────────────────

mcp = FastMCP("fink_lsst_mcp")

# ─────────────────────────────────────────────────────────────
# Helpers HTTP
# ─────────────────────────────────────────────────────────────


async def _post(endpoint: str, payload: dict) -> dict | list:
    """POST vers l'API Fink en éliminant les valeurs None."""
    clean = {k: v for k, v in payload.items() if v is not None}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{BASE_URL}/{endpoint}", json=clean)
        r.raise_for_status()
        return r.json()


async def _get(endpoint: str, params: dict | None = None) -> dict | list:
    """GET vers l'API Fink."""
    clean = {k: v for k, v in (params or {}).items() if v is not None}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(f"{BASE_URL}/{endpoint}", params=clean)
        r.raise_for_status()
        return r.json()


def _fmt(data: dict | list) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def _handle_error(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        try:
            detail = e.response.json()
        except Exception:
            detail = e.response.text[:300]
        if status == 400:
            return f"Erreur 400 : Paramètres invalides. Détail : {detail}"
        if status == 404:
            return f"Erreur 404 : Ressource introuvable. Vérifiez l'identifiant. Détail : {detail}"
        if status == 422:
            return f"Erreur 422 : Paramètres invalides. Détail : {detail}"
        if status == 429:
            return "Erreur 429 : Limite de requêtes atteinte. Attendez avant de réessayer."
        if status == 500:
            return "Erreur 500 : Erreur interne du serveur Fink. Réessayez plus tard."
        return f"Erreur HTTP {status} : {detail}"
    if isinstance(e, httpx.TimeoutException):
        return "Timeout : La requête a pris trop de temps. L'API Fink est peut-être surchargée."
    if isinstance(e, httpx.ConnectError):
        return "Erreur de connexion : Impossible d'atteindre api.lsst.fink-portal.org."
    return f"Erreur inattendue ({type(e).__name__}) : {e!s}"


# ─────────────────────────────────────────────────────────────
# Modèles Pydantic
# ─────────────────────────────────────────────────────────────


class SourcesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    diaObjectId: str = Field(
        ...,
        description="Identifiant numérique Rubin diaObjectId (STRING), ou liste séparée par des virgules. Ex: '169298433216610349'. Obtenir via fink_resolver ou fink_conesearch.",
        min_length=1,
    )
    midpointMjdTai: float | None = Field(
        default=None,
        description="Si fourni, ne retourne que la source à cette date MJD. Ne fonctionne pas si diaObjectId est une liste.",
    )
    columns: str | None = Field(
        default=None,
        description="Colonnes à retourner (préfixe 'r:'). Ex: 'r:midpointMjdTai,r:psfFlux,r:band,r:ra,r:dec'. Par défaut toutes (lent).",
    )
    output_format: str = Field(
        default="json", description="Format de sortie : 'json', 'csv', 'parquet', 'votable'."
    )


class ObjectsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    diaObjectId: str = Field(
        ...,
        description="Identifiant numérique Rubin diaObjectId, ou liste séparée par des virgules. Ex: '396895411240977'. Retourne données agrégées (pas la courbe de lumière — utiliser fink_get_sources pour ça).",
        min_length=1,
    )
    columns: str | None = Field(
        default=None,
        description="Colonnes à retourner (préfixe 'i:'). Ex: 'i:firstDiaSourceMjdTai,i:nDiaSources,i:g_psfFluxMax'.",
    )
    output_format: str = Field(
        default="json", description="Format de sortie : 'json', 'csv', 'parquet', 'votable'."
    )


class FpInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    diaObjectId: str = Field(
        ...,
        description="Identifiant numérique Rubin diaObjectId (STRING), ou liste séparée par des virgules.",
        min_length=1,
    )
    columns: str | None = Field(
        default=None,
        description="Colonnes à retourner. Ex: 'r:midpointMjdTai,r:psfFlux,r:band'. Par défaut toutes (lent).",
    )
    output_format: str = Field(
        default="json", description="Format de sortie : 'json', 'csv', 'parquet', 'votable'."
    )


class ConeSearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ra: float = Field(
        ..., description="Ascension droite en degrés décimaux (J2000). Ex: 7.893627", ge=0.0, le=360.0
    )
    dec: float = Field(
        ..., description="Déclinaison en degrés décimaux (J2000). Ex: -44.771556", ge=-90.0, le=90.0
    )
    radius: float = Field(
        ...,
        description="Rayon de recherche en arcsec. Maximum : 18000 arcsec (5°). Ex: 10.0",
        gt=0.0,
        le=18000.0,
    )
    n: int | None = Field(
        default=None, description="Nombre maximum d'alertes à retourner. Défaut : 1000.", ge=1
    )
    startdate: str | None = Field(
        default=None,
        description="Date de début UTC (iso, jd, ou MJD). Restreint aux objets dont la PREMIÈRE détection est dans cet intervalle. Ex: '2025-09-05 12:30:00'.",
    )
    stopdate: str | None = Field(
        default=None, description="Date de fin UTC (iso, jd, ou MJD). Défaut : maintenant."
    )
    window: float | None = Field(
        default=None,
        description="Fenêtre temporelle en jours depuis aujourd'hui (alternative à stopdate).",
        gt=0.0,
    )
    columns: str | None = Field(
        default=None, description="Colonnes à retourner. Ex: 'i:midpointMjdTai,i:psfFlux,i:band'."
    )
    output_format: str = Field(
        default="json", description="Format de sortie : 'json', 'csv', 'parquet', 'votable'."
    )


class CutoutsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    diaSourceId: str = Field(
        ...,
        description="Identifiant diaSource (entier long en STRING). Ex: '169298437355340113'. Obtenir depuis fink_get_sources (colonne 'r:diaSourceId').",
        min_length=1,
    )
    kind: str = Field(
        default="Science",
        description="Type de vignette : 'Science', 'Template', 'Difference', ou 'All' (seulement pour output-format=array).",
    )
    output_format: str = Field(
        default="PNG", description="Format de sortie : 'PNG' (défaut, base64), 'FITS', 'array'."
    )
    stretch: str | None = Field(
        default=None, description="Étirement : 'sigmoid' (défaut), 'linear', 'sqrt', 'power', 'log'."
    )
    colormap: str | None = Field(
        default=None, description="Colormap matplotlib. Ex: 'Blues', 'viridis'. Défaut : niveaux de gris."
    )
    pmin: float | None = Field(
        default=None,
        description="Percentile minimum pour le niveau de coupe. Défaut : 0.5. Sans effet pour sigmoid.",
    )
    pmax: float | None = Field(
        default=None,
        description="Percentile maximum pour le niveau de coupe. Défaut : 99.5. Sans effet pour sigmoid.",
    )
    convolution_kernel: str | None = Field(
        default=None, description="Noyau de convolution : 'gauss' ou 'box'. Par défaut aucune convolution."
    )


class SSOInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    n_or_d: str = Field(
        ...,
        description="Numéro IAU ou désignation provisoire du SSO. Forme packed acceptée (ex: 'K15W16Q'). Ex: '8467' (astéroïde), '10P' (comète), '2010JO69', 'C/2020V2'. Liste séparée par virgules acceptée.",
        min_length=1,
    )
    withEphem: bool = Field(
        default=False, description="Attacher les éphémérides Miriade/IMCCE comme colonnes supplémentaires."
    )
    withResiduals: bool = Field(
        default=False, description="Retourner les résidus obs-modèle (sHG1G2). Un seul objet seulement."
    )
    columns: str | None = Field(
        default=None,
        description="Colonnes à retourner. Ex: 'r:midpointMjdTai,r:scienceFlux,r:band,r:ra,r:dec'.",
    )
    output_format: str = Field(
        default="json", description="Format de sortie : 'json', 'csv', 'parquet', 'votable'."
    )


class SchemaInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    endpoint: str = Field(
        ...,
        description="Nom de l'endpoint dont on veut le schéma. Valeurs valides : 'sources', 'objects', 'fp', 'conesearch', 'sso', 'tags', 'statistics'.",
        min_length=1,
    )
    major_version: int | None = Field(
        default=None, description="Version majeure LSST. Défaut : dernière version."
    )
    minor_version: int | None = Field(
        default=None, description="Version mineure LSST. Défaut : dernière version."
    )


class StatisticsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    date: str = Field(
        ...,
        description="Date d'observation : 'YYYYMMDD' (nuit), 'YYYYMM' (mois), 'YYYY' (année), ou '' (tout). Ex: '20260120', '202601', '2026', ''.",
    )
    columns: str | None = Field(
        default=None, description="Colonnes à retourner. Ex: 'f:alerts,f:night'. Par défaut toutes."
    )
    output_format: str = Field(
        default="json", description="Format de sortie : 'json', 'csv', 'parquet', 'votable'."
    )


class TagsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    tag: str = Field(
        ...,
        description="Tag Fink de classification. Voir fink_list_classes pour les tags disponibles. Ex: 'cataloged', 'SN candidate', 'kilonova candidate'.",
        min_length=1,
    )
    n: int | None = Field(default=100, description="Nombre d'alertes à retourner. Défaut : 100.", ge=1)
    startdate: str | None = Field(
        default=None, description="Date de début UTC (iso, jd, ou MJD). Ex: '2026-01-01 00:00:00'."
    )
    stopdate: str | None = Field(
        default=None, description="Date de fin UTC (iso, jd, ou MJD). Défaut : maintenant."
    )
    columns: str | None = Field(
        default=None, description="Colonnes à retourner. Ex: 'r:diaObjectId,r:scienceFlux,r:midpointMjdTai'."
    )
    output_format: str = Field(
        default="json", description="Format de sortie : 'json', 'csv', 'parquet', 'votable'."
    )


class ResolverInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    resolver: str = Field(
        ...,
        description="Resolver : 'simbad' (étoiles/galaxies), 'ssodnet' (Système Solaire), 'tns' (Transient Name Server).",
        min_length=1,
    )
    name_or_id: str = Field(
        ...,
        description="Nom ou ID à résoudre. Si reverse=True, fournir un diaObjectId LSST. Ex: 'SN 2024abtt' (TNS), 'NGC 1365' (Simbad), '8467' (SSodnet).",
        min_length=1,
    )
    reverse: bool = Field(
        default=False, description="Si True, résout un diaObjectId LSST en nom astronomique."
    )
    nmax: int | None = Field(default=10, description="Nombre maximum de correspondances. Défaut : 10.", ge=1)
    output_format: str = Field(
        default="json", description="Format de sortie : 'json', 'csv', 'parquet', 'votable'."
    )


class SkymapInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    event_name: str | None = Field(
        default=None, description="Nom GraceDB de l'événement GW. Ex: 'S251112cm'. Incompatible avec 'file'."
    )
    credible_level: float = Field(
        ...,
        description="Seuil de région de crédibilité GW [0.0, 1.0]. Ex: 0.90 pour la région à 90% de probabilité.",
        ge=0.0,
        le=1.0,
    )
    n_day_before: float | None = Field(
        default=1.0, description="Jours à chercher AVANT l'événement. Défaut : 1, max : 7.", ge=0.0, le=7.0
    )
    n_day_after: float | None = Field(
        default=6.0, description="Jours à chercher APRÈS l'événement. Défaut : 6, max : 14.", ge=0.0, le=14.0
    )
    output_format: str = Field(
        default="json", description="Format de sortie : 'json', 'csv', 'parquet', 'votable'."
    )


# ─────────────────────────────────────────────────────────────
# Outils MCP
# ─────────────────────────────────────────────────────────────


@mcp.tool(
    name="fink_get_sources",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def fink_get_sources(params: SourcesInput) -> str:
    """
    Récupère la courbe de lumière détaillée (diaSources) pour un diaObjectId LSST.

    Outil principal pour obtenir les données photométriques : flux, bande, date.
    Chaque ligne = une alerte individuelle (diaSource).

    Colonnes clés (préfixe 'r:') : r:midpointMjdTai (date MJD), r:psfFlux (flux en nJy),
    r:psfFluxErr, r:band (filtre u/g/r/i/z/y), r:ra, r:dec, r:diaSourceId (pour fink_get_cutout).

    Args:
        params (SourcesInput): diaObjectId (obligatoire), midpointMjdTai, columns, output_format.

    Returns:
        str: JSON avec liste de diaSources.

    """
    try:
        data = await _post(
            "sources",
            {
                "diaObjectId": params.diaObjectId,
                "midpointMjdTai": params.midpointMjdTai,
                "columns": params.columns,
                "output-format": params.output_format,
            },
        )
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="fink_get_objects",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def fink_get_objects(params: ObjectsInput) -> str:
    """
    Récupère les données agrégées (diaObject) pour un diaObjectId LSST.

    Retourne statistiques agrégées sur l'objet : nombre de détections, flux max par bande,
    dates première/dernière détection. Pour la courbe de lumière détaillée, utiliser fink_get_sources.

    Colonnes clés (préfixe 'i:') : i:diaObjectId, i:firstDiaSourceMjdTai, i:nDiaSources,
    i:g_psfFluxMax, i:r_psfFluxMax, etc.

    Args:
        params (ObjectsInput): diaObjectId (obligatoire), columns, output_format.

    Returns:
        str: JSON avec données agrégées de l'objet.

    """
    try:
        data = await _post(
            "objects",
            {
                "diaObjectId": params.diaObjectId,
                "columns": params.columns,
                "output-format": params.output_format,
            },
        )
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="fink_get_forced_photometry",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def fink_get_forced_photometry(params: FpInput) -> str:
    """
    Récupère la photométrie forcée pour un diaObjectId LSST.

    Mesure le flux à la position connue de l'objet même sans détection significative.
    Permet d'obtenir des limites supérieures et des courbes de lumière plus complètes
    avant/après le pic. Colonnes similaires à fink_get_sources (préfixe 'r:').

    Args:
        params (FpInput): diaObjectId (obligatoire), columns, output_format.

    Returns:
        str: JSON avec mesures de photométrie forcée.

    """
    try:
        data = await _post(
            "fp",
            {
                "diaObjectId": params.diaObjectId,
                "columns": params.columns,
                "output-format": params.output_format,
            },
        )
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="fink_conesearch",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def fink_conesearch(params: ConeSearchInput) -> str:
    """
    Recherche spatiale (cone search) dans Fink/LSST autour d'une position céleste.

    Retourne les alertes dont la PREMIÈRE détection est dans le cône et l'intervalle de temps.
    Attention : ne retourne pas tous les transients visibles pendant la période,
    mais ceux DÉCOUVERTS pendant cette période.

    Idéal pour : trouver transients autour d'une galaxie hôte, chercher contreparties
    optiques d'événements multi-messagers. Le radius est en arcsec (max 18000").

    Args:
        params (ConeSearchInput): ra, dec (degrés J2000), radius (arcsec), dates optionnelles.

    Returns:
        str: JSON avec alertes dans le cône.

    """
    try:
        data = await _post(
            "conesearch",
            {
                "ra": params.ra,
                "dec": params.dec,
                "radius": params.radius,
                "n": params.n,
                "startdate": params.startdate,
                "stopdate": params.stopdate,
                "window": params.window,
                "columns": params.columns,
                "output-format": params.output_format,
            },
        )
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="fink_get_cutout",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def fink_get_cutout(params: CutoutsInput) -> str:
    """
    Récupère une vignette d'image pour une alerte LSST (diaSource).

    Retourne l'image Science, Template ou Difference autour de la source.
    Requiert le diaSourceId (pas diaObjectId) — obtenir depuis fink_get_sources
    (colonne 'r:diaSourceId'). Pour PNG, l'image est encodée en base64.

    Args:
        params (CutoutsInput): diaSourceId (obligatoire), kind, output_format, options visuelles.

    Returns:
        str: JSON avec image encodée ou données tableau.

    """
    try:
        data = await _post(
            "cutouts",
            {
                "diaSourceId": params.diaSourceId,
                "kind": params.kind,
                "output-format": params.output_format,
                "stretch": params.stretch,
                "colormap": params.colormap,
                "pmin": params.pmin,
                "pmax": params.pmax,
                "convolution_kernel": params.convolution_kernel,
            },
        )
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="fink_get_sso",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def fink_get_sso(params: SSOInput) -> str:
    """
    Récupère les observations Fink/LSST pour un objet du Système Solaire (SSO).

    Cherche les observations d'astéroïdes et comètes connus dans la base MPC.
    Peut ajouter les éphémérides Miriade/IMCCE. Formats n_or_d : '8467' (numéro),
    '2010JO69' (désignation sans espace), '10P' (comète), 'C/2020V2', 'K15W16Q' (packed).

    Args:
        params (SSOInput): n_or_d (obligatoire), withEphem, withResiduals, columns.

    Returns:
        str: JSON avec observations LSST. Colonnes : r:midpointMjdTai, r:scienceFlux, r:band, r:ra, r:dec.

    """
    try:
        data = await _post(
            "sso",
            {
                "n_or_d": params.n_or_d,
                "withEphem": params.withEphem,
                "withResiduals": params.withResiduals,
                "columns": params.columns,
                "output-format": params.output_format,
            },
        )
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="fink_get_schema",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def fink_get_schema(params: SchemaInput) -> str:
    """
    Récupère le schéma des colonnes disponibles pour un endpoint Fink/LSST.

    Indispensable pour connaître les noms exacts de colonnes à utiliser dans
    les autres outils. Chaque endpoint a son schéma avec des préfixes spécifiques
    ('r:' pour sources/fp, 'i:' pour objects/conesearch, etc.).

    Endpoints valides : 'sources', 'objects', 'fp', 'conesearch', 'sso', 'tags', 'statistics'.

    Args:
        params (SchemaInput): endpoint (obligatoire), major_version, minor_version.

    Returns:
        str: JSON avec schéma : liste de colonnes avec nom, type, description.

    """
    try:
        data = await _post(
            "schema",
            {
                "endpoint": params.endpoint,
                "major_version": params.major_version,
                "minor_version": params.minor_version,
            },
        )
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="fink_get_statistics",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def fink_get_statistics(params: StatisticsInput) -> str:
    """
    Récupère les statistiques Fink/LSST pour une période donnée.

    Métriques agrégées sur le volume d'alertes traitées. Formats de date :
    'YYYYMMDD' (nuit), 'YYYYMM' (mois), 'YYYY' (année), '' (tout).
    Colonnes typiques (préfixe 'f:') : f:night, f:alerts, f:nSources.

    Args:
        params (StatisticsInput): date (obligatoire), columns, output_format.

    Returns:
        str: JSON avec statistiques pour la période.

    """
    try:
        data = await _post(
            "statistics",
            {"date": params.date, "columns": params.columns, "output-format": params.output_format},
        )
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="fink_get_by_tag",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def fink_get_by_tag(params: TagsInput) -> str:
    """
    Récupère les N dernières alertes Fink/LSST filtrées par tag de classification.

    Tags produits par les modules scientifiques Fink. Utiliser fink_list_classes
    pour voir tous les tags disponibles. Exemples : 'cataloged', 'SN candidate',
    'kilonova candidate', 'solar system', 'unknown'.

    Args:
        params (TagsInput): tag (obligatoire), n, startdate, stopdate, columns.

    Returns:
        str: JSON avec les N dernières alertes du tag, triées par date.

    """
    try:
        data = await _post(
            "tags",
            {
                "tag": params.tag,
                "n": params.n,
                "startdate": params.startdate,
                "stopdate": params.stopdate,
                "columns": params.columns,
                "output-format": params.output_format,
            },
        )
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="fink_resolver",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def fink_resolver(params: ResolverInput) -> str:
    """
    Résout un nom astronomique en diaObjectId LSST, ou l'inverse.

    Fait le lien entre noms conventionnels et identifiants LSST internes.
    Cas d'usage : trouver le diaObjectId de 'SN 2024abtt' (TNS), de 'NGC 1365' (Simbad),
    ou identifier un diaObjectId inconnu (reverse=True).

    Resolvers : 'simbad' (étoiles/galaxies), 'ssodnet' (SSO), 'tns' (transients/SNe).

    Args:
        params (ResolverInput): resolver, name_or_id (obligatoires), reverse, nmax.

    Returns:
        str: JSON avec correspondances et diaObjectId LSST.

    """
    try:
        data = await _post(
            "resolver",
            {
                "resolver": params.resolver,
                "name_or_id": params.name_or_id,
                "reverse": params.reverse,
                "nmax": params.nmax,
                "output-format": params.output_format,
            },
        )
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="fink_skymap_gw",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def fink_skymap_gw(params: SkymapInput) -> str:
    """
    Cherche les alertes Fink/LSST dans la région de probabilité d'une onde gravitationnelle.

    Croise les alertes LSST avec la skymap GW (LIGO/Virgo/KAGRA) dans une fenêtre
    temporelle autour de l'événement. Parfait pour rechercher des contreparties
    électromagnétiques (kilonovae, etc.). Spécifier l'événement par son nom GraceDB.

    credible_level=0.90 → région contenant 90% de la probabilité de localisation.

    Args:
        params (SkymapInput): credible_level (obligatoire), event_name, n_day_before, n_day_after.

    Returns:
        str: JSON avec alertes LSST dans la région de probabilité GW.

    """
    try:
        data = await _post(
            "skymap",
            {
                "event_name": params.event_name,
                "credible_level": params.credible_level,
                "n_day_before": params.n_day_before,
                "n_day_after": params.n_day_after,
                "output-format": params.output_format,
            },
        )
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="fink_list_classes",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def fink_list_classes() -> str:
    """
    Liste tous les tags/classes de classification disponibles dans Fink/LSST.

    Retourne la liste complète des tags produits par les modules scientifiques Fink.
    Ces tags sont utilisés avec fink_get_by_tag pour filtrer les alertes.

    Returns:
        str: JSON avec liste des classes disponibles et leur description.

    """
    try:
        data = await _get("classes")
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="fink_get_blocks",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def fink_get_blocks() -> str:
    """
    Récupère la définition des blocs de données Fink/LSST.

    Les blocs définissent les groupes de colonnes disponibles dans la base.
    Utile pour comprendre la structure des données et identifier les colonnes
    d'intérêt par thème.

    Returns:
        str: JSON avec définition des blocs de données.

    """
    try:
        data = await _get("blocks")
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


# ─────────────────────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
