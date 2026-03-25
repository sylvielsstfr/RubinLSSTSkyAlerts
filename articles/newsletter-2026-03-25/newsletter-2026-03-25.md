# Coding with an AI to Explore the Fink Broker for Rubin/LSST — One Month In

**Fink Newsletter · March 25, 2026**

*Sylvie Dagoret-Campagne — IJCLab / IN2P3*

---

## A Telescope Turns On, and a Different Kind of Collaboration Begins

Around February 24, 2026, the first public alert stream from the Rubin Observatory
Vera C. Rubin Science Verification began flowing through the Fink broker. Tens of
thousands of transient detections — each one encoded as a `diaSource` packet with
six photometric bands, image cutouts, and crossmatch metadata — started accumulating
every night at `https://api.lsst.fink-portal.org`.

At roughly the same moment, I started using Claude, the AI assistant developed by
Anthropic, in its free version — no dedicated coding environment, no special
integration. Just a browser window open next to a terminal, and a month's worth of
increasingly ambitious conversations.

This article is an attempt to reflect honestly on what happened: what I asked, what
came back, how it worked technically, and why this kind of human-AI pair programming
turned out to be genuinely useful for exploring a new scientific data portal.

---

## The Context: A New API, an Unfamiliar Schema

The Fink LSST API is not the same as the older ZTF version of the portal. The
differences are subtle but consequential, and discovering them the hard way —
through 500 errors, unexpected empty DataFrames, or light curves plotted in the
wrong band — is exactly the kind of friction that slows down exploration.

A few examples of things that tripped me up initially, and that the AI helped me
decode:

| Aspect | ZTF portal | LSST portal |
|--------|------------|-------------|
| HTTP method | `POST` with JSON body | `GET` with query-string params |
| Tag endpoint | `/latests?class=` | `/tags?tag=` |
| Light curve endpoint | `/objects?objectId=` | `/sources?diaObjectId=` |
| Column prefix `r:` | spectral band r | diaSource table name (NOT the band) |
| Flux units | magnitudes | nJy (nanojansky) |
| Spectral band | value of `i:fid` | value of `r:band` |

The `r:` prefix confusion deserves special mention. In the LSST alert schema,
`r:` means "field from the `diaSource` relational table" — it is a database table
identifier, not the photometric band r. The actual band is encoded in the *value*
of the column `r:band`. This naming convention, while logical once you understand
the Fink HBase block family structure, was a source of persistent confusion early
on. Figuring it out required careful reading of the `/api/v1/blocks` endpoint
response, and the AI was invaluable in walking through that JSON structure
systematically.

---

## How Does Claude Actually Decode the Fink API?

This is the question I keep getting asked, and it deserves a careful answer
because the mechanism is less mysterious than it sounds — but also more interesting.

### No real-time access, no internal test cloud

Claude does not make live HTTP requests to `api.lsst.fink-portal.org` during a
conversation. It has no "internal cloud" where it runs test queries in the
background. It does not browse the Fink Swagger UI at runtime.

What it does have is a large-scale language model trained on a broad corpus that
includes REST API documentation, Python code using `requests`, pandas, numpy,
astropy, and many examples of scientific data pipelines. When I paste a JSON snippet
from the `/api/v1/blocks` endpoint or a fragment of a 500-error traceback into
the conversation, Claude reasons from that context — not from some live connection
to the outside world.

### The conversation as a living specification

In practice, what made the collaboration productive was that I treated the
conversation as an incremental specification document. Each exchange added
context:

1. I paste the raw JSON response from `/api/v1/blocks` and ask: *"What structure
   is this? How many block families are there?"*
2. Claude identifies the `i:`, `r:`, `d:`, `f:`, `b:` prefix convention and
   explains its meaning in terms of Fink's HBase schema.
3. I ask: *"Write a Python function that normalises this into a tidy DataFrame
   regardless of whether the response is a flat list, a dict of lists, or a
   nested dict."*
4. Claude produces adaptive code with three fallback strategies. I run it,
   it works, I move on.
5. Next session: *"Now I want to cross-reference the block-defined columns against
   what `/api/v1/statistics` actually returns. Write a comparison notebook section."*

At no point did the AI need to "test" the API. It reasoned from the schema I
provided and from its prior knowledge of REST conventions and pandas idioms.

### What about the Swagger?

The `swagger.json` file that you can find at the root of the notebooks directory
was something I downloaded manually early on and used as reference documentation.
I never fed it directly to the AI in full (it's large), but I pasted relevant
excerpts when I had specific questions about endpoint parameters. Claude could
read those excerpts and infer the correct `requests.get()` call parameters without
needing to "browse" anything.

---

## A Month of Notebooks: What We Built Together

Looking back at the notebooks directory, the progression is clear. Here is a
condensed map of what emerged from those exchanges, roughly in chronological order.

### Phase 1 — First contact with the alert stream (late February 2026)

The first scripts downloaded a batch of recent alerts using the `/api/v1/tags`
endpoint, saved their light curves as Parquet files, and produced the first
cutout visualisations. The key discovery was the `GET`-based query model of
the LSST API (as opposed to the `POST`-based ZTF model), and the correct way
to request forced-photometry data via `/api/v1/fp`.

A Python library began to take shape: `rubinlsstskyalerts.fink_tools`, which
encapsulated all API calls behind clean functions (`download_dataset`,
`fetch_latest_alerts`, `fetch_light_curve`, `fetch_cutouts`).

### Phase 2 — Sky maps and spatial exploration (early March 2026)

The `02_fink_api_exploration` notebooks addressed questions like: where in the
sky are alerts appearing? How do the different Fink classification tags
(`extragalactic_new_candidate`, `sn_near_galaxy_candidate`, `hostless_candidate`,
`in_tns`, `extragalactic_lt20mag_candidate`) distribute across the celestial sphere?

This required HEALPix pixelisation via `healpy`, Mollweide and rectangular
projections, annotation of Deep Drilling Fields and the Galactic plane, and a
temporal animation showing a rolling 3-day window over 30 days. The AI helped
translate astronomical coordinate reasoning (Galactic ↔ equatorial conversion
for `healpy` projections) into working code.

The statistics endpoint (`/api/v1/statistics`) was also explored in depth,
yielding nightly alert counts per tag, cumulative stream curves, and a day-of-week
heatmap of alert activity.

### Phase 3 — Schema archaeology: the `/api/v1/blocks` endpoint (mid-March 2026)

The `05_fink_api_blocks.ipynb` notebook is perhaps the most technically intricate.
The `/api/v1/blocks` endpoint returns the complete HBase column schema — hundreds
of field definitions organised into the five block families. The notebook:

- Detects the response structure automatically (flat list, dict of lists, or
  nested dict) and normalises it into a tidy DataFrame
- Produces bar charts of column counts per block prefix
- Performs keyword analysis via CamelCase/snake_case tokenisation
- Cross-references block-defined columns against those actually returned by
  live endpoints (`/statistics`, `/tags`)

None of this required running live queries during development. The AI reasoned
from the pasted JSON responses I provided.

### Phase 4 — Light curve classification for calibration (mid-to-late March 2026)

The `03_fink_api_blockselections` notebooks tackled a specific scientific question:
which sources in the Rubin alert stream are photometrically stable enough to
serve as atmospheric transparency calibrators?

This required cone searches of Deep Drilling Fields, crossmatch-based classification
(Gaia DR3 stable stars, SIMBAD galaxies, Legacy Survey sources, Mangrove galaxies,
VSX variables, TNS transients), flatness metrics (σ/⟨f⟩ per band per object),
colour-colour diagrams (G−R vs R−I in AB magnitude), and visit-level matching
for Butler integration.

The nJy → AB magnitude conversion (`m = −2.5 log₁₀(f_nJy) + 31.4`) and its
propagated uncertainty became routine after the AI explained it once, clearly,
with the correct formula.

---

## The Less-Known Capability: Writing Files Directly to Your Machine

There is a feature of the local Claude interface that is not widely advertised
and that turned out to be extraordinarily useful in this work.

When Claude is connected to your local filesystem via the MCP (Model Context
Protocol) filesystem server — which can be set up once and then runs silently
in the background — it can write files directly to your computer in response to
a chat request.

This means the workflow for generating a new notebook or a Python script looks
like this:

> *"Write a Python script that downloads the 50 most recent `sn_near_galaxy_candidate`
> alerts from the Fink LSST API, saves the light curves as Parquet files under
> `fink_dataset/sn_near_galaxy_candidate/`, and produces a 5×4 grid of light
> curve plots in both flux and magnitude."*

Claude writes the complete, ready-to-run script directly into the appropriate
directory on disk. No copy-paste, no intermediate step.

The same applies to README files. After completing a set of notebooks, I would
ask:

> *"Write a README.md for this directory that describes each notebook, its inputs
> and outputs, the API endpoints it uses, and the execution order."*

The three README files that now accompany the notebook directories in this
repository were generated in exactly this way — then reviewed and adjusted to
reflect my own experience and phrasing.

This is not automation replacing judgment. The AI cannot know whether a scientific
choice is right. But it dramatically compresses the time between "I want to
understand X" and "I have running code and documentation for X."

---

## What Made This Pedagogically Valuable

For users who are not already fluent with REST APIs, the dialogue model has a
specific educational advantage: you can ask *why*, not just *what*.

A typical exchange:

> *Me: Why did my request to `/api/v1/sources` return an empty DataFrame even
> though the diaObjectId is valid?*
>
> *Claude: The most likely cause is that `/api/v1/sources` expects a `diaSourceId`,
> not a `diaObjectId`. These are different identifiers in the LSST schema. A
> `diaObject` aggregates multiple `diaSource` detections. You need to first
> fetch the object record to get the list of associated `diaSourceId` values,
> then query each source individually — or use the `objectId` parameter of
> `/api/v1/objects` to get the aggregate view.*

This kind of explanation — immediate, specific to the actual error, embedded in
the correct conceptual frame — is what distinguishes interactive AI assistance
from searching documentation. The documentation exists, but navigating it
correctly presupposes knowing what question to ask.

---

## Limitations and Honest Caveats

The collaboration was not frictionless. A few things to be aware of:

**The AI can be confidently wrong about specifics.** When I asked about the
exact parameter names for a rarely-documented endpoint, I sometimes received
plausible-sounding but incorrect suggestions. The fix was always to verify
against the actual API response — which is why pasting real output into the
conversation is essential.

**It does not remember previous sessions.** Each conversation starts fresh.
Over a month of work, I developed the habit of opening new sessions with a
brief context-setting paragraph: the base URL, the key column conventions,
what I had built so far. The filesystem connection means it can read existing
code and README files directly, which partially compensates for the lack of
persistent memory.

**Scientific judgment remains yours.** The AI does not know whether
`extragalactic_new_candidate` is the right tag to use for your science case,
or whether 50 detections is a reasonable minimum for a calibration study.
It executes the reasoning you frame. The framing is your responsibility.

---

## An Invitation

If you use the Fink portal for Rubin/LSST data and you have not yet tried
working with an AI assistant, I encourage you to try it for the specific task
of understanding the API schema. Start with the `/api/v1/blocks` endpoint:
download its JSON response, paste it into a Claude conversation, and ask the
AI to explain the block family structure to you. Then ask it to write a
normalisation function. See what happens.

The notebooks and library produced over this month are available in the
`RubinLSSTSkyAlerts` repository. The README files document the API nuances
that took the longest to work out. They are the best starting point if you
want to avoid the most common pitfalls.

The Fink broker is a remarkable piece of infrastructure. Rubin/LSST is generating
data at a scale that requires new tools for exploration. AI-assisted coding is
one of those tools — not a replacement for scientific expertise, but a
genuine accelerant for the part of the work that is about turning data into
understanding.

---

## Key API Reference (Fink LSST, March 2026)

```
Base URL: https://api.lsst.fink-portal.org/api/v1

Endpoints:
  GET  /tags?tag=<tag>&n=<n>             → latest alerts by classification tag
  GET  /latests?class=<class>            → latest alerts by class (incl. Solar System)
  POST /sources?diaObjectId=<id>         → per-detection light curve (diaSource table)
  POST /fp?diaObjectId=<id>              → forced-photometry light curve
  POST /objects?objectId=<id>            → object-level aggregate statistics
  POST /conesearch                       → spatial cone search (use r: column prefix)
  GET  /statistics?date=<YYYYMMDD>       → per-night alert stream statistics
  GET  /blocks                           → full HBase column schema
  GET  /schema                           → column schema per endpoint

Available classification tags (March 2026):
  extragalactic_lt20mag_candidate
  extragalactic_new_candidate
  hostless_candidate
  in_tns
  sn_near_galaxy_candidate

Flux → AB magnitude:
  m    = -2.5 * log10(f_nJy) + 31.4
  σ_m  = (2.5 / ln 10) * (σ_f / f)
```

---

*This article reflects one researcher's experience using Claude (Anthropic) as a
coding companion for scientific data exploration. All code and notebooks described
here are available in the `RubinLSSTSkyAlerts` repository. Feedback and corrections
are welcome.*

*→ Fink LSST portal: [https://lsst.fink-portal.org](https://lsst.fink-portal.org)*
*→ Fink LSST API: [https://api.lsst.fink-portal.org](https://api.lsst.fink-portal.org)*
