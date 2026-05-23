# Cloud-Native Geospatial Reference Architecture

Vendor-ready design corpus for an AWS-native serverless geospatial platform: vector data, raster data, network routing, and reviewed editing, behind a single authorisation layer. Sixteen documents, ~4,900 lines, code-independent.

Hosted as a [Quartz](https://quartz.jzhao.xyz/) site so the cross-references between principles, components, decisions, and journeys are navigable — graph view, backlinks, hover previews, full-text search.

## Reading the site

Start at the [Introduction](content/index.md) for the framing and purpose of the work, then continue to the [Document index and reading paths](content/00_INDEX.md) for chapter-by-chapter navigation by audience (executive, architect, implementer, operator).

The substance lives in `content/`:

- `index.md` — introduction: the brief, the approach, the economic case, three ways to use the work
- `00_INDEX.md` — document index, reading paths, AWS-as-reference framing, and currency notes
- `01_PRINCIPLES.md` — design philosophy and non-goals
- `02_ARCHITECTURE.md` — system shape, request flow, cache classes
- `03_AUTHORISATION.md` — identity, permission model, RLS
- `04_DATA_LAYOUT.md` — S3 layout, GeoParquet partitioning, DynamoDB tables
- `05_VECTOR_TILES.md` through `10_DISCOVERY.md` — component designs
- `11_EDITING_PIPELINE.md` — reviewed editing pipeline end to end
- `12_DEPLOYMENT.md` — environments, scaling modes, AWS specifics
- `13_OPERATIONS.md` — monitoring, runbooks, DR
- `14_CLIENT_INTEGRATION.md` — QGIS, ArcGIS, web, programmatic
- `15_MAP_CLIENT.md` — first-party React + MapLibre web client: catalogue, editing, review, GraphiQL, live pipeline link
- `16_DESIGN_DECISIONS.md` — 30+ decisions with rationale and prior-iteration lessons
- `17_FURTHER_DIRECTIONS.md` — sketched extensions worth exploring (semantic discovery, geocoding, point clouds, 3D, CV, multi-agent, field capture, reports, subscriptions, change detection, live data)
- `18_LAKEHOUSE_INTEGRATION.md` — reconciling the platform with a modern lakehouse (Delta, Iceberg, Databricks): where the boundary sits, what each side does well, and how they compose
- `19_GLOSSARY_AND_REFERENCES.md` — every term, format, service, standard, library, and peer OGC stack named in the corpus, with canonical URLs

## Running locally

```sh
npm install
npx quartz build --serve
```

Then open <http://localhost:8080>.

The first build takes a minute; subsequent builds are incremental.

## Deploying to GitHub Pages

A workflow at `.github/workflows/deploy.yml` builds the site and publishes it on every push to `main`. To enable:

1. Push this repo to GitHub.
2. In repo settings → Pages, set **Source: GitHub Actions**.
3. Push to `main`. The site appears at `https://<user>.github.io/<repo>/`.

If you point a custom domain at the site, set the `baseUrl` field in `quartz.config.ts` accordingly.

## Editing

Files are plain markdown. Mermaid diagrams render natively (fenced code blocks with `mermaid` language).

Internal cross-document references can be either:
- Standard markdown: `[03 Authorisation](03_AUTHORISATION.md)` — used throughout the corpus.
- Wikilinks: `[[03_AUTHORISATION|03 Authorisation]]` — also supported by Quartz.

Backlinks, hover previews of linked pages, the per-page graph, and the whole-corpus graph are all enabled by default in the site layout.

## Status

The original prototype is not being handed over. This documentation is the artefact. See `15_DESIGN_DECISIONS.md` for the lessons-learned spine that shaped the design, and the honest "what's solid vs what's undertested" framing inside `10_DISCOVERY.md`. The agentic-access postscript at the end of `10_DISCOVERY.md` is intentionally aspirational.

---

## Site generator

Built with [Quartz v4](https://quartz.jzhao.xyz/) by Jacky Zhao. Quartz's `docs/` and license remain in this repo for reference; everything in `content/` is original design documentation.
