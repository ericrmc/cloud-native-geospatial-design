# 02 — Architecture

This document describes the overall shape of the platform: the layers, the components within each layer, and the path a request takes through them. It is the map you keep open while reading the other documents.

## Platform at a glance

This is a C4 *container* view: the people who use the platform, the deployable containers that make it up, the technology each runs on (in `[brackets]`), and — importantly — what each container reads from. Solid arrows are request and data flow; dashed arrows are token validation and catalogue links.

Three kinds of user reach the platform through a single public entry. Every request passes through the **security layer** — CloudFront and the API Gateway, the Lambda authoriser, and the internal ALB — before any backend is touched; nothing else is publicly reachable. The authoriser resolves identity once against the identity provider and DynamoDB, and the ALB routes the request to the container that serves it. Serving APIs read cloud-native files directly from S3 — vector tiles from PMTiles, raster from COGs, features and spatial queries from GeoParquet via DuckDB. The query layer is the one serving component that fans out further: it calls the routing engine for route, isochrone, and map-match operations, reads the dataset registry and row-level-security policies from DynamoDB, and can register new datasets there. The STAC catalogue is **discovery only** — it is *not* in the data path; clients read tiles, features, and coverages straight from the serving APIs. The editing pipeline is the write path; the Policy API is the admin control plane alongside.

```mermaid
flowchart TB
    consumer(["Data Consumer<br/>Web map · QGIS · ArcGIS · app"])
    editor(["Data Editor<br/>Contributes &amp; reviews edits"])
    admin(["Administrator<br/>Manages access &amp; datasets"])

    subgraph platform["Cloud-Native Spatial Platform"]
        direction TB

        subgraph security["Security Layer — every request passes through"]
            direction LR
            CF["CloudFront + API Gateway<br/>[managed]"]
            AZ["Lambda Authoriser<br/>[Lambda]"]
            ALB["Internal ALB<br/>[private]"]
            IDP[("Cognito / OIDC IdP")]
        end

        subgraph control["Discovery &amp; Admin"]
            direction LR
            STAC["STAC Catalogue API<br/>[Lambda] · discovery"]
            POLICY["Policy API<br/>[Lambda] · admin"]
        end

        subgraph write["Editing Pipeline — write path"]
            direction LR
            EDIT["Editing API · Upload Gate<br/>[Lambda]"]
            SFN["Step Functions<br/>Validate → Generate → Promote"]
        end

        subgraph serve["Serving APIs — read path"]
            direction TB
            VT["Vector Tile Server<br/>[Fargate · go-pmtiles]"]
            RT["Raster Tile Server<br/>[Fargate · TiTiler]"]
            WMTS["WMTS / WMS Proxy<br/>[Fargate]"]
            FEAT["OGC Features API<br/>[Lambda]"]
            QUERY["Query Layer / GraphQL<br/>[Fargate · DuckDB]"]
            COV["Coverages API<br/>[Fargate]"]
            ROUTE["Routing Engine<br/>[Fargate · Valhalla]"]
        end

        DDB[("DynamoDB · registry · policies · jobs")]
        S3[("S3 — object store<br/>PMTiles · COGs · GeoParquet · history")]
    end

    consumer -->|API key / JWT| CF
    editor -->|JWT| CF
    admin -->|JWT| CF

    CF -->|invoke| AZ
    CF -->|VPC Link| ALB
    AZ -.->|validate token| IDP
    AZ -.-> DDB

    ALB --> serve
    ALB --> control
    ALB --> write

    VT -->|PMTiles| S3
    RT -->|COGs| S3
    COV -->|COGs| S3
    QUERY -->|GeoParquet| S3
    QUERY --> ROUTE
    QUERY -.-> DDB
    FEAT -->|façade| QUERY
    WMTS -->|proxies| RT
    STAC -.-> DDB
    POLICY -.-> DDB

    EDIT -->|landing| S3
    EDIT -.-> DDB
    EDIT --> SFN
    SFN -->|artefacts| S3

    classDef person fill:#08427b,color:#ffffff,stroke:#052e56;
    classDef store fill:#eef3f8,color:#222,stroke:#9bb;
    classDef muted fill:#fafafa,color:#999,stroke:#d5d5d5,stroke-dasharray:3 3;
    class consumer,editor,admin person;
    class S3,IDP store;
    class DDB muted;
```

The rest of this document decomposes the same platform into technical layers and request flows.

## Five layers

The container view above shows relationships and reads; this view shows the same platform as the five-layer skeleton the rest of this document is organised around — edge, read, write, admin, and data — and the control flow between them.

```mermaid
flowchart TB
    subgraph Edge["Edge Layer"]
        CF["CloudFront<br/>cache policies per route class"]
        APIGW["API Gateway HTTP API<br/>wildcard {proxy+} route"]
        AUTH["Lambda Authoriser<br/>custom authoriser"]
    end

    subgraph Read["Read Layer"]
        TILES["Vector tile server (Fargate)"]
        FEAT["OGC Features API (Lambda)"]
        QUERY["Query layer / GraphQL (Fargate)"]
        RAS["Raster tile server (Fargate)"]
        WMTS["WMTS/WMS proxy (Fargate)"]
        COV["Coverages API (Fargate)"]
        ROUTE["Routing engine (Fargate)"]
        STAC["STAC API (Lambda)"]
    end

    subgraph Write["Write Layer"]
        EDIT["Editing API (Lambda)"]
        UPLOAD["Upload gate (Lambda)"]
        SFN["Step Functions"]
        VAL["Validation task (Fargate task)"]
        GEN["Generation task (Fargate task)"]
        PROMOTE["Promotion function (Lambda)"]
    end

    subgraph Admin["Admin Layer"]
        POLICY["Policy API (Lambda)"]
        SYNC["Dataset sync (Lambda, scheduled)"]
        VACUUM["History vacuum (Lambda, scheduled)"]
    end

    subgraph Data["Data Layer"]
        S3[("S3 — single bucket, prefix-organised")]
        DDB[("DynamoDB — policies, datasets,<br/>jobs, sessions, api-keys")]
        COG[("Cognito User Pool<br/>(or external OIDC IdP)")]
    end

    CF --> APIGW --> AUTH
    AUTH -. reads policies/RLS .-> DDB
    APIGW -- VPC Link --> ALB[Internal ALB]
    ALB --> Read & Write & Admin
    AUTH -. validates JWT .-> COG
    Read -->|"tiles, features, coverages"| S3
    Read -->|"registry, RLS lookups"| DDB
    Write --> SFN --> VAL --> GEN --> PROMOTE
    Write -->|"landing, generated artefacts"| S3
    Write -->|"jobs, sessions, history"| DDB
    Admin -->|"policies, keys, registry"| DDB
    Admin -->|"history vacuum, event log"| S3
```

### Edge layer

The edge layer handles TLS termination, edge caching, and authorisation. Every request entering the platform passes through it. No backend service is reachable from the public internet; the only public endpoint is the API Gateway HTTP API, and it is fronted by CloudFront.

Components:

- **CloudFront** — terminates TLS, caches responses according to per-route cache policies (see below), and forwards cache misses to the API Gateway origin. Tile and metadata cache keys include both the `Authorization` and `X-Api-Key` request headers so each credential gets its own edge entry. Permission-sensitive APIs use a near-zero-TTL policy whose cache key includes `Authorization` only (CloudFront requires TTL > 0 to header-key, so `X-Api-Key` is forwarded but is not in the cache key for this policy class — see below).
- **API Gateway HTTP API** — a single wildcard `{proxy+}` route attached to a Lambda custom authoriser, with a VPC Link integration to the internal ALB. Provides request throttling, structured CloudWatch access logging, CORS handling, and route-level configuration.
- **Lambda authoriser** — a small Lambda function that resolves identity (Cognito or external-OIDC JWT, or platform-issued API key) into a permission context. The API Gateway HTTP API parameter-mapping feature turns the authoriser's response context into trusted `X-Auth-*` headers attached to the forwarded request. Backends never see the original token.

### Read layer

Serves data to clients. Every component in this layer is read-only and stateless; persistent state lives in the data layer.

Components are grouped by *capability domain*, not by transport. The compute substrate (Fargate or Lambda) is chosen per component based on workload — see [12 Deployment](12_DEPLOYMENT.md) for the compute-split rationale.

- **Vector tile server (Fargate)** — serves MVT tiles from PMTiles archives in S3 via byte-range reads. See [05 Vector Tiles](05_VECTOR_TILES.md).
- **OGC Features API (Lambda)** — standards-compliant feature access. May be implemented as a standalone Lambda over GeoParquet, or as a façade over the query layer. See [06 OGC Features API](06_OGC_FEATURES_API.md).
- **Query layer (Fargate)** — GraphQL endpoint offering spatial operations, network routing, and cross-dataset queries. Optional; not deployed in environments that only need OGC compliance. See [07 Query Layer](07_QUERY_LAYER.md).
- **Raster tile server (Fargate)** — dynamic tile rendering from COGs in S3. See [08 Raster Services](08_RASTER_SERVICES.md).
- **WMTS/WMS proxy (Fargate)** — protocol translation to OGC WMTS 1.0.0 and WMS 1.3.0, plus an adapter for ArcGIS-compatible vector tile services.
- **Coverages API (Fargate)** — OGC API - Coverages over COGs.
- **Routing engine (Fargate)** — network routing, isochrones, map-matching, and road snapping. See [09 Routing](09_ROUTING.md).
- **STAC API (Lambda)** — catalogue and discovery over the DynamoDB dataset registry. See [10 Discovery](10_DISCOVERY.md).

### Write layer

Coordinates user-initiated edits to authoritative datasets. Edits are decoupled from the request that initiates them: the request layer accepts an intent and a payload; Step Functions performs the work asynchronously and reports status through a job record.

Components:

- **Editing API (Lambda)** — manages edit sessions, presigned S3 upload URLs, finalisation, review approvals, and validation-check configuration.
- **Upload gate (Lambda)** — accepts standalone bulk-upload requests (non-session edits), authorises the caller against dataset and role, and returns presigned S3 upload URLs.
- **Step Functions state machine** — orchestrates validation, generation, and promotion. Retry policies with exponential backoff cover transient failures; catch blocks route uncaught errors to a failure handler. Execution history is visible in the AWS console.
- **Validation task (Fargate task, transient)** — an ECS task launched per job that runs schema, geometry, and user-defined SQL checks against an uploaded dataset. Uses DuckDB with the spatial extension.
- **Generation task (Fargate task, transient)** — an ECS task launched per job that produces serving artefacts (PMTiles via Tippecanoe, with optional delta and difference variants for review). Up to 200 GiB ephemeral storage per task.
- **Promotion function (Lambda)** — performs the S3 `CopyObject` atomic swap, issues the CloudFront invalidation, writes SCD2 history rows, emits an event-log entry, and dequeues the next queued job for the dataset.

See [11 Editing Pipeline](11_EDITING_PIPELINE.md) for the full state machine.

### Admin layer

Long-running concerns that are not in the request path of any user.

- **Policy API (Lambda)** — administrative REST surface for managing identity ceilings, platform groups, projects, group claims, dataset registration, row-level security configuration, API keys, and user invitations. See [03 Authorisation](03_AUTHORISATION.md).
- **Dataset sync (Lambda, EventBridge-scheduled)** — scanner that **validates** existing dataset registry entries against actual S3 contents, flagging registry rows whose referenced S3 paths no longer exist. The scanner does not create new registry rows for unknown S3 contents — dataset registration is always an explicit Policy-API or pipeline action. The original design intent was auto-creation of `needs_review` skeleton entries for surfaced new content; the prototype landed on validation-only as the safer default.
- **History vacuum (Lambda, EventBridge-scheduled)** — compactor that merges per-edit SCD2 history files into monthly archives.
- **Event-log compactor (Lambda, EventBridge-scheduled)** — same pattern for the per-dataset event log under `metadata/dataset_events/`.

### Data layer

Three durable substrates, each with a clear purpose:

- **S3 (single bucket)** — all spatial data, edit uploads, serving artefacts, SCD2 history, and event logs. Prefix-organised; lifecycle rules per prefix. See [04 Data Layout](04_DATA_LAYOUT.md).
- **DynamoDB** — auth policies, dataset registry, edit sessions, jobs, API keys, row-level-security configuration. Single-table designs for related data with GSIs for inverse-direction lookups; separate tables only where access patterns or TTL requirements diverge. On-demand billing, PITR enabled.
- **Identity provider** — Cognito User Pool by default, or any OIDC-compliant external IdP listed in the trusted-issuers configuration. The platform consumes signed JWTs; no identity management within the platform itself.

## Request flow

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant CF as CloudFront
    participant GW as API Gateway HTTP API
    participant AZ as Lambda Authoriser
    participant DDB as DynamoDB
    participant ALB as Internal ALB
    participant Backend
    participant S3

    Client->>CF: Request with credential header
    alt cached
        CF-->>Client: Cached response
    else miss
        CF->>GW: Forward request (HTTPS origin)
        GW->>AZ: Invoke custom authoriser
        AZ->>DDB: Look up identity, ceiling, groups, datasets, RLS
        DDB-->>AZ: Resolved context
        AZ-->>GW: isAuthorized + context
        GW->>ALB: HTTPS via VPC Link, with parameter-mapped X-Auth-* headers
        ALB->>Backend: Path-based listener rule → target group (Fargate IP or Lambda)
        Backend->>S3: Byte-range read (PMTiles / COG) or partition read (GeoParquet)
        S3-->>Backend: Bytes
        Backend-->>ALB: Response
        ALB-->>GW: Response
        GW-->>CF: Response
        CF-->>Client: Response (cached per policy)
    end
```

The flow is identical for every backend in the read layer. The only thing that varies is the path the gateway matches and the backend it forwards to.

For edits, the early stages of the flow are the same; the backend (the editing API) writes to the key-value store and object storage, optionally invokes the workflow engine, and returns a job identifier. The actual work happens asynchronously and the client polls the job API.

## CloudFront cache policy classes

CloudFront is configured with three cache policies, each applied to a class of behaviours on the distribution:

| Policy class | TTL | Cache key includes | Applies to |
|---|---|---|---|
| Auth near-zero | 1 second (min/default/max) | `Authorization` header | Feature reads, admin APIs, edit APIs, job APIs, STAC, uploads — anything that must reflect current permissions |
| API-key tiles | 7 days | `Authorization` and `X-Api-Key` headers | Vector tiles, raster tiles, WMTS, mosaics, capabilities documents |
| API-key metadata | 1 hour | `Authorization` and `X-Api-Key` headers | TileJSON, STAC collections, dataset listings |

> *In plain terms:* "every request is authorised" is true on cache miss. On a cache hit inside a one-second window, the credential header in the cache key is the only thing distinguishing one caller from another. For tiles and metadata, that key includes both `Authorization` and `X-Api-Key`, so JWT and API-key callers each get their own edge entry. For the near-zero auth policy, CloudFront requires `TTL > 0` to header-key the cache, and only `Authorization` is in the key — `X-Api-Key` is forwarded as a request header but not part of the cache key for that policy class. Two API-key callers hitting the same permission-sensitive URL within a one-second window can therefore share a cache entry. The trade-off was accepted because the alternative — a fully disabled cache policy on those paths — gives up CloudFront-level burst protection without buying meaningful isolation given a 1s TTL.

Per-credential keying for the tile and metadata policies means a tile cached for one API key is not served to another, even if both have access to the same dataset. Every distinct credential is verified at least once, and there is no cross-credential cache reuse for those paths.

> *In plain terms:* for tiles and metadata, the same artefact is stored at the edge once per credential. Tile bytes are cheap, but the guarantee that nobody ever reads a tile cached against someone else's permissions is valuable. For permission-sensitive APIs, the one-second TTL bounds the staleness window — a stricter contract would need a disabled cache policy *and* explicit `X-Api-Key` keying.

CloudFront path-pattern invalidation (`/tiles/vector/{dataset}/*`) is issued by the promotion function on every successful pipeline run so edge caches re-fetch the new tiles.

## Backend addressing — internal ALB

Inside the platform, a single internal Application Load Balancer (ALB v2) sits in private subnets and is the only ingress to all backends. API Gateway HTTP API reaches it through a **VPC Link** private integration; the ALB is **not reachable from the public internet**.

> *In plain terms:* every backend trusts the `X-Auth-*` headers because the only way those headers can reach a backend is through the gateway's parameter mapping. A client cannot forge them because a client cannot reach the ALB at all.

The ALB routes by path pattern via listener rules (each rule is a `CfnListenerRule` with a unique priority and a `PathPatternConfigProperty`). Several rules use the ALB v2 URL-rewrite transform (`RewriteConfigObjectProperty`) to strip the public path prefix before forwarding to the backend's native path:

| Path prefix | Backend |
|---|---|
| `/stac/*` | STAC API |
| `/rest/auth/*`, `/rest/datasets/*` | Policy API |
| `/tiles/vector/*` | Vector tile server (with URL rewrite) |
| `/graphql/*` | Query layer |
| `/features/*` | OGC Features API |
| `/routing/*` | Routing engine |
| `/coverages/*` | Coverages API |
| `/tiles/raster/*`, `/mosaics/*` | Raster tile server |
| `/wmts/*`, `/wms/*` | WMTS/WMS proxy |
| `/edit-sessions/*`, `/editing/*`, `/validation-checks/*`, `/validation-sequences/*` | Editing API |
| `/uploads/*` | Upload gate |
| `/jobs/*` | Job API |

Each rule is independent. A new backend is added by writing a new `CfnListenerRule` with a non-conflicting priority and pointing it at a new target group. Target groups accept Fargate task IPs (target-type `ip`) or Lambda function ARNs (target-type `lambda`); the ALB transparently selects between them based on the rule's target group.

## Component substitutability

A summary of which components are off-the-shelf and which are custom (in the sense of being purpose-built for this platform, regardless of who builds them):

| Component | AWS substrate | Build vs buy |
|---|---|---|
| CloudFront | Managed CDN | Configuration only |
| API Gateway HTTP API | Managed gateway | Configuration only |
| Lambda authoriser | Lambda + DynamoDB | Custom (small, focused) |
| Vector tile server | Fargate service running an off-the-shelf PMTiles HTTP server (e.g. go-pmtiles) | Container only |
| OGC Features API | Lambda | Custom (small) — see [06 OGC Features API](06_OGC_FEATURES_API.md) for the two valid shapes |
| Query layer | Fargate service | Custom (substantial) — only build if rich query capability is required |
| Raster tile server | Fargate service running an off-the-shelf COG-aware tile server (e.g. TiTiler) | Container only |
| WMTS/WMS proxy | Fargate service | Custom (moderate) |
| Coverages API | Fargate service | Custom (small) |
| Routing engine | Fargate service running an off-the-shelf routing engine (e.g. Valhalla) with regional OSM data baked into the image | Container with embedded data |
| STAC API | Lambda over DynamoDB | Custom (small) |
| Editing API | Lambda | Custom (moderate) |
| Validation / generation tasks | Fargate transient ECS tasks | Custom (moderate) — use DuckDB and Tippecanoe |
| Promotion function | Lambda | Custom (small) |
| Policy API | Lambda | Custom (moderate) |

Custom components are deliberately small because the design principle of stable contracts (Principle 4) confines complexity to single components. There is no monolith.

## Where to read next

- The data layer is the most consequential design choice — go to [04 Data Layout](04_DATA_LAYOUT.md) next.
- The authorisation model determines every request's behaviour — [03 Authorisation](03_AUTHORISATION.md).
- The rationale for each technology pick is in [16 Design Decisions](16_DESIGN_DECISIONS.md).
