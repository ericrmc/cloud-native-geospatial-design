# Document index and reading paths

This page is the navigational entry point to the design corpus. For the purpose and framing of the work itself, start at the [introduction](index.md).

A complete, implementation-independent description of a serverless geospatial platform for hosting and serving vector data, raster data, and reviewed dataset editing, behind a single authorisation layer.

## What this document set is

A vendor-ready design artefact. It describes *what* the platform is, *why* each design choice was made, and *how* the components fit together. It is not a code guide, a tutorial, or a record of any specific implementation. A team reading this set should be able to construct an equivalent platform — in their preferred cloud, languages, and frameworks — and arrive at substantively the same behaviour.

The platform is positioned as **state-of-the-art serverless spatial computing**: cloud-native data formats served directly from object storage, scale-to-zero by default, with a coherent authorisation model and a reviewed editing pipeline. The audience is technical decision-makers, architects, and implementers.

## What the platform does and does not do

**Does:**
- Serves vector tiles, vector features, raster tiles, and raster coverages from object-storage-native formats
- Provides standards-compliant external interfaces (OGC API Features, OGC API Coverages, OGC WMTS/WMS, STAC, TileJSON, MVT)
- Offers an optional rich query layer for spatial operations and network routing
- Supports authenticated read and edit access, with row-level filtering driven by group claims
- Manages reviewed edit sessions with delta and difference visualisation against authoritative datasets
- Keeps per-row history for auditing
- Issues and manages API keys for desktop GIS and programmatic clients

**Does not:**
- Run analytical workloads (no BI, no ad-hoc SQL surfaces for end users)
- Transform or derive datasets through pipelines (no ETL framework, no scheduled transformations beyond data sync)
- Provide live transactional spatial writes (no database-backed feature collections)
- Federate or proxy external spatial services (it owns its data)

## Reading order

| If you are… | Start with | Then |
|---|---|---|
| An executive needing the shape | [01 Principles](01_PRINCIPLES.md), [02 Architecture](02_ARCHITECTURE.md) | [16 Design Decisions](16_DESIGN_DECISIONS.md) |
| An architect planning a build | [01 Principles](01_PRINCIPLES.md) → [02 Architecture](02_ARCHITECTURE.md) → [04 Data Layout](04_DATA_LAYOUT.md) → [03 Authorisation](03_AUTHORISATION.md) | [16 Design Decisions](16_DESIGN_DECISIONS.md), [12 Deployment](12_DEPLOYMENT.md) |
| An implementer of the read path | [04 Data Layout](04_DATA_LAYOUT.md), [05 Vector Tiles](05_VECTOR_TILES.md), [06 OGC Features API](06_OGC_FEATURES_API.md) | [08 Raster](08_RASTER_SERVICES.md), [09 Routing](09_ROUTING.md), [10 Discovery](10_DISCOVERY.md) |
| An implementer of the query layer | [07 Query Layer](07_QUERY_LAYER.md) | [04 Data Layout](04_DATA_LAYOUT.md), [09 Routing](09_ROUTING.md) |
| An implementer of editing | [11 Editing Pipeline](11_EDITING_PIPELINE.md) | [04 Data Layout](04_DATA_LAYOUT.md), [03 Authorisation](03_AUTHORISATION.md) |
| An operator | [13 Operations](13_OPERATIONS.md), [12 Deployment](12_DEPLOYMENT.md) | [11 Editing Pipeline](11_EDITING_PIPELINE.md) |
| A client integrator | [14 Client Integration](14_CLIENT_INTEGRATION.md) | [03 Authorisation](03_AUTHORISATION.md) |
| A front-end developer of the map client | [15 Map Client](15_MAP_CLIENT.md) | [03 Authorisation](03_AUTHORISATION.md), [11 Editing Pipeline](11_EDITING_PIPELINE.md) |

## Document catalogue

| # | Document | Subject |
|---|---|---|
| — | [Introduction](index.md) | Purpose, framing, the original brief, and how to read the corpus |
| 01 | [Principles](01_PRINCIPLES.md) | Design philosophy and non-goals |
| 02 | [Architecture](02_ARCHITECTURE.md) | System shape, components, request flow |
| 03 | [Authorisation](03_AUTHORISATION.md) | Identity, roles, ceilings, groups, claims, RLS, API keys |
| 04 | [Data Layout](04_DATA_LAYOUT.md) | Object-storage layout, partitioning, metadata stores |
| 05 | [Vector Tiles](05_VECTOR_TILES.md) | PMTiles serving |
| 06 | [OGC Features API](06_OGC_FEATURES_API.md) | Standards-compliant feature access, with and without the query layer |
| 07 | [Query Layer](07_QUERY_LAYER.md) | Rich spatial query and routing interface |
| 08 | [Raster Services](08_RASTER_SERVICES.md) | Raster tiles, WMTS/WMS, OGC Coverages |
| 09 | [Routing](09_ROUTING.md) | Network routing, isochrones, map matching |
| 10 | [Discovery](10_DISCOVERY.md) | STAC catalogue and dataset registry |
| 11 | [Editing Pipeline](11_EDITING_PIPELINE.md) | Upload, validation, generation, review, promotion, history |
| 12 | [Deployment](12_DEPLOYMENT.md) | Environments, service groups, scaling modes |
| 13 | [Operations](13_OPERATIONS.md) | Monitoring, alarms, troubleshooting, DR |
| 14 | [Client Integration](14_CLIENT_INTEGRATION.md) | QGIS, ArcGIS, web maps, programmatic clients |
| 15 | [Map Client](15_MAP_CLIENT.md) | First-party React + MapLibre web app: catalogue, editing, review, GraphiQL, live pipeline link |
| 16 | [Design Decisions](16_DESIGN_DECISIONS.md) | Standalone record of pivotal choices and trade-offs |
| 17 | [Further Directions](17_FURTHER_DIRECTIONS.md) | Eleven sketched extensions — semantic discovery, geocoding, point clouds, 3D, computer vision, multi-agent orchestration, field capture, reports, subscriptions, change detection, live data |
| 18 | [Glossary and References](18_GLOSSARY_AND_REFERENCES.md) | Reference index — every term, format, service, standard, library, and peer OGC stack named in the corpus, with canonical URLs |

## AWS as the reference platform

This design is **AWS-native**. It was first implemented on AWS, and several of the architectural choices depend on specific AWS service features that do not have like-for-like equivalents elsewhere. The most consequential of these:

- **Application Load Balancer (ALB) v2** for internal path-based routing, with per-rule URL rewrite via listener-rule transforms, listener-rule priorities, and IP-target groups that accept Fargate task ENIs and Lambda function ARNs as targets.
- **S3** with byte-range reads (the substrate that PMTiles, COGs, and GeoParquet predicate pushdown all depend on), atomic `CopyObject` within a bucket for promotion, prefix-scoped event notifications, prefix-scoped lifecycle rules, and Intelligent-Tiering.
- **API Gateway HTTP API** with a wildcard `{proxy+}` route, a custom Lambda authoriser, and parameter-mapping that turns authoriser context fields into trusted request headers.
- **Lambda** for the authoriser, for thin façades over data, and as ALB or API Gateway integration targets — with the IAM/VPC-Link/private-integration semantics that make this possible.
- **DynamoDB** with single-table designs, GSIs, conditional writes (for optimistic locking and concurrency control), on-demand billing, per-item TTL, and PITR.
- **Step Functions** for the editing pipeline: visual execution history, integrated ECS task invocation, typed retry policies with exponential backoff, and catch-block error routing to a failure handler.
- **Fargate** with the task-versus-service distinction (transient ECS tasks for batch validation/generation steps; long-running ECS services for HTTP backends) and per-task ephemeral storage up to ~200 GiB.
- **CloudFront** with cache policies that key on credential headers (`Authorization`, `X-Api-Key`), per-behaviour cache-policy assignment, and path-scoped invalidation.
- **Cognito User Pool** as the default identity provider with a post-authentication Lambda trigger that converts pending platform invitations into memberships on first sign-in.
- **VPC Link** as the private connectivity layer between API Gateway HTTP API and the internal ALB; the ALB sits in private subnets and is not reachable from the public internet.
- **OIDC identity provider** — the platform consumes signed JWTs from any OIDC-compliant IdP. Cognito is the default; an enterprise IdP (Entra ID, Auth0, Okta) can be configured via the trusted-issuers list.

Where a concept is genuinely portable (the OGC standards, the cloud-native file formats, the design principles, the editing-pipeline state machine), the documentation describes it abstractly. Where an AWS service is doing specific work that another cloud does not directly replicate, the AWS service is named.

A brief survey of the closest equivalents on Google Cloud and Azure is given in [12 Deployment](12_DEPLOYMENT.md), but it is intended as orientation only: porting this platform to another cloud is a redesign at the networking and edge layers, not a substitution exercise.

## Status of this design

This is a *direction* document, not a record of a proven implementation. The original prototype was not production-reviewed and is not being handed over. Anyone implementing against this set should treat it as a well-considered starting point: the decisions in [16 Design Decisions](16_DESIGN_DECISIONS.md) are the load-bearing ones, but every component admits substitution as long as the contracts in [02 Architecture](02_ARCHITECTURE.md), [03 Authorisation](03_AUTHORISATION.md), and [04 Data Layout](04_DATA_LAYOUT.md) are preserved.

Several decisions documented here are informed by **prior iterations** that were tried and replaced during the prototype's life. Where a previous shape failed or proved over-engineered, the relevant document explains the lesson learned. These are not abstract preferences; they are scars.

## Timeline and currency

This design is a snapshot of considered work, not eternal truth. The research and prototype work spanned roughly seven months:

- **November–December 2025** — exploratory phase. Evaluation of [GeoServer Cloud](16_DESIGN_DECISIONS.md) as a possible foundation; first attempts at PMTiles serving; the initial Aurora PostgreSQL + pgSTAC shape that would later be removed.
- **February 2026** — the platform's public git history begins. First working PMTiles and raster stack lands; Martin → go-pmtiles switch follows; database stack deleted in favour of S3-native formats; DynamoDB-backed authoriser introduced.
- **March 2026** — the most active month. GraphQL query layer added; OGC Features API refactored from Fargate-with-DuckDB into a Lambda façade; edit sessions, per-dataset concurrency, reviewed editing with delta/diff PMTiles, SCD2 history, and SQL-based bulk editing all land. Internal-only ALB and VPC Link migration completed.
- **April 2026** — final tweaks and consolidation.
- **May 2026** — this design corpus assembled.

Seven months is enough time for the AWS, OGC, and open-source landscape to move. Several technology claims here may already have been overtaken — Aurora Serverless v2 added true scale-to-zero late in this window (see the callout under [D1 in 16 Design Decisions](16_DESIGN_DECISIONS.md)); Bedrock AgentCore matured rapidly; OpenSearch Serverless pricing shifted; mermaid macro names in Confluence Cloud changed providers. Where the corpus has caught up, it says so. Where it has not, treat every concrete tech claim as **true when written, not true forever**. Re-check the canonical sources in [18 Glossary and References](18_GLOSSARY_AND_REFERENCES.md) before committing to a build path. The [closing note in 17 Further Directions](17_FURTHER_DIRECTIONS.md#a-note-on-dates) bookends this point.
