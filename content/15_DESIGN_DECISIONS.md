# 15 — Design Decisions

This is a standalone record of the pivotal design choices that shape the platform. Each entry is the *what* and *why* of a decision, plus the major alternatives that were considered, the conditions under which the decision should be revisited, and — where relevant — the **prior iteration** that taught the lesson. Several of these decisions were arrived at after an earlier shape was tried and failed; those scars are recorded because they are the most defensible part of the rationale.

The decisions are grouped by the area they primarily affect.

## Lessons from earlier iterations (read first)

Five major shifts during the prototype's life shape the rest of the decisions:

1. **Aurora PostgreSQL + pgSTAC was deployed, then removed.** The original design used Aurora Serverless v2 PostgreSQL with PostGIS and pgSTAC. Maintaining an always-on database for what turned out to be a serving workload was an order of magnitude more expensive than necessary, and the database became the single point of failure for scale-to-zero. The whole spatial-data layer was moved to S3-native formats (PMTiles, GeoParquet, COGs) and the database was deleted entirely. This is the headline lesson; D1 below codifies it.
2. **Vector tiles ran on Martin (Rust, PostgreSQL-backed), then on go-pmtiles.** Martin's PostgreSQL dependency conflicted with lesson 1; its PMTiles support required service restarts on file change. Replaced with go-pmtiles, which reads S3 directly and refreshes on ETag change. D5 codifies it.
3. **STAC ran on Fargate with pgSTAC, then as a Lambda over DynamoDB.** Once the rest of the platform was off the database, pgSTAC was the last hold-out. Replaced with a small Lambda reading the DynamoDB datasets table. The registry *is* the catalogue.
4. **OGC Features API ran on Fargate with its own DuckDB engine, then as a Lambda façade over GraphQL.** When the GraphQL query layer arrived, the Fargate Features service was refactored into a thin Lambda calling GraphQL so the spatial engine wasn't duplicated. The standalone-Fargate version was then deleted. D26 codifies both shapes as valid; the Lambda-standalone shape (over GeoParquet directly, without GraphQL) is the *recommended* starting point for OGC-only deployments.
5. **The ALB was internet-facing, then moved to private subnets behind VPC Link.** The original design relied on convention ("traffic should go through API Gateway") rather than network controls. Closing this required moving the ALB to private subnets and connecting API Gateway via VPC Link. Anyone implementing this design should make the ALB internal-only from day one. D16 codifies it.
6. **The editing pipeline had no sessions, no queueing, no review, then got all three.** The first pipeline accepted any upload and ran it immediately. Concurrent uploads to the same dataset produced corrupted partition writes. Edit sessions, per-dataset concurrency limits with queueing, and the reviewed-editing variant with delta/diff PMTiles were added as a single body of work. D18, D19, and D20 codify them.

These are the lessons that informed the decisions below. Where a decision exists *because* of a prior misfire, the misfire is noted.

---

## Data and storage

### D1. Serve all spatial data directly from S3; no spatial database in the read path

**Decision.** Vector features are queried as GeoParquet by DuckDB; vector tiles are served as PMTiles archives over S3 byte-range reads; raster is served as Cloud-Optimized GeoTIFFs and MosaicJSON descriptors in S3. No relational or document database holds spatial data in the read path.

**Why.** Eliminates the largest fixed cost of a traditional geospatial platform (an always-on database with patching, backups, connection pooling, failover). Enables scale-to-zero. Makes durability a property of S3 (eleven nines), not the application. Aligns with a maturing ecosystem of tools that read these formats directly.

> *In plain terms:* an idle deployment pays for storage and almost nothing else. The cost shape follows traffic, not the calendar.

**Prior iteration.** The platform originally ran on **Aurora PostgreSQL Serverless v2 with PostGIS and pgSTAC**, deployed as an RDS stack with RDS Proxy. The minimum capacity floor (0.5 ACU ≈ \$43/month) and the operational weight of patching, backup, and Data API integration made scale-to-zero impossible. The whole database stack was deleted in favour of S3-native formats. The platform has not needed a database for spatial data since.

**Trade-off.** No live SQL queries against spatial data. Updates are batch-oriented through the editing pipeline, not transactional INSERTs.

**Alternatives.** A managed PostGIS instance (mature, but always-on cost and operational burden). Athena (per-query cost, higher latency). Aurora Serverless v2 (still has minimum capacity).

**Revisit if.** Live transactional spatial writes become a requirement, or analytical workloads on highly normalised data exceed what DuckDB can handle.

### D2. Single object-storage bucket with prefixes, not multiple buckets

**Decision.** One bucket holds COGs, PMTiles, GeoParquet sources, drafts, landing uploads, history, and metadata. Organisation is by prefix.

**Why.** Simpler IAM (one resource), one lifecycle policy, fewer resources to manage, no cross-bucket coordination during atomic operations. Object storage has no per-bucket charge.

**Trade-off.** Per-prefix cost reporting requires storage analytics rather than per-bucket billing.

### D3. Hive-style spatial partitioning for GeoParquet

**Decision.** GeoParquet sources are organised as `{dataset}/z={z}/x={x}/y={y}/data.parquet`. Features that straddle partition tiles are written to every tile they intersect, full geometry (not clipped). Reads deduplicate by feature identifier.

**Why.** Predicate pushdown on partition keys lets bbox queries read only the relevant files. Incremental edits only rewrite affected partitions (a one-feature edit on an 800k-feature dataset rewrites a handful of files). Hive layout is understood by every modern analytical engine. Writing full geometries means queries never need to reassemble clipped pieces.

**Trade-off.** Features that span partitions appear multiple times in raw scans; deduplication on read is mandatory. Every dataset must declare an identifier column.

**Alternatives.** Flat layout with a single file per dataset (no spatial pushdown). Attribute-based partitioning (does not align with bbox queries). Geometry clipping at partition boundaries (writes are simpler, reads must reassemble — chose the opposite trade-off).

### D4. Use `DISTINCT ON` (or equivalent) for cross-partition deduplication

**Decision.** Every spatial query is written with explicit deduplication by feature identifier. For distance-ordered queries where `DISTINCT ON` can't express the ordering, a window function ranking by identifier and distance is used.

**Why.** The smallest change that handles the cross-partition writes (D3) correctly. The analytical engine handles deduplication efficiently when the identifier is high-cardinality.

**Alternatives.** Clipping at write time (rejected — see D3). Post-query deduplication in the application layer (defeats LIMIT/OFFSET; requires over-fetch).

### D5. PMTiles + go-pmtiles for vector tile delivery

**Decision.** Vector tiles are stored as PMTiles archives in S3 and served by **go-pmtiles** (an off-the-shelf PMTiles HTTP server) running as a Fargate service. The server uses S3 byte-range reads to fetch the PMTiles directory and individual tiles; it caches the directory keyed on the S3 ETag and refreshes when the ETag changes.

**Why.** Single-file archive (one S3 object per dataset), no database, supports millions of features, automatic refresh on atomic CopyObject swap. The format and tooling are mature.

**Prior iteration.** The platform originally ran **Martin** (Rust, PostgreSQL-backed) for vector tiles. Martin's PostgreSQL dependency conflicted with D1; Martin's PMTiles support did exist but only re-read the file index at process startup, so any update to a PMTiles file required a service restart. go-pmtiles refreshes automatically on ETag change, which composes cleanly with the atomic-swap promotion pattern (D5 in [11 Editing Pipeline](11_EDITING_PIPELINE.md)).

**Alternatives.** A database-backed tile generator (introduces a database; not aligned with D1). Pre-rendered tile pyramids in S3 as individual objects (massive object count, harder lifecycle, no atomic-swap pattern).

### D6. Tippecanoe for PMTiles generation

**Decision.** PMTiles archives are produced by Tippecanoe (the open-source vector tile generator originated at Mapbox, currently maintained by Felt).

**Why.** Produces high-quality vector tiles with intelligent feature simplification and dropping. Geometry-aware parameter sets handle points, lines, and polygons differently. Active maintenance.

**Trade-off.** A C++ build is required in the generation task's container image. Tippecanoe makes opinionated decisions about tile content at low zoom levels (drops features for legibility) that may not match every use case.

**Alternatives.** GDAL `ogr2ogr` to MVT (lower quality, no intelligent simplification). Python-native PMTiles builders (less mature for production volume).

### D7. Cloud-Optimized GeoTIFFs for raster

**Decision.** All raster data uses COGs with overviews and internal tiling.

**Why.** The de facto standard for HTTP-readable raster. GDAL ecosystem support is universal. Mosaicking via MosaicJSON composes COGs without a database.

**Alternatives.** Zarr (excellent for multidimensional rasters, less standard for 2D imagery served as tiles). Tile pyramids (precomputed, less flexible).

### D8. Row-level history as append-only SCD2 Parquet, not a separate transactional log

**Decision.** Per-row history is written to `history/{dataset}/` as Parquet files with SCD2 columns. Initial snapshots are excluded from compaction. Read queries use predicate pushdown on validity timestamps. A vacuum job compacts deltas monthly.

**Why.** Reuses the platform's existing read engine (analytical SQL on Parquet) for history queries. Storage grows with edit frequency, not dataset size. No additional infrastructure.

**Trade-off.** Spatial queries against history are limited by the unpartitioned layout; the design is for time-based audit queries, not for spatial-temporal analytics.

**Alternatives.** A separate audit-log database (extra infrastructure, different query language). Spatial partitioning of history (more complex, premature optimisation for use cases not yet observed).

---

## Authorisation

### D9. Lambda-equivalent authoriser in front of every backend

**Decision.** An HTTP API gateway runs a function-runtime authoriser on every request. The authoriser resolves identity to a permission context and returns headers that the gateway attaches to the forwarded request. Backends do not validate tokens; they read the headers.

**Why.** Concentrates security-critical logic in one small body of code. Backends become simpler. Adding a backend is a path-routing rule; no auth code is duplicated.

> *In plain terms:* every backend is downstream of a single small Lambda that decides whether the caller is allowed and who they are. Backends just read the headers they're handed.

**Trade-off.** Adds an authoriser hop per request (typically ~50–100ms cold-call, sub-millisecond warm-cached). Header trust depends on the internal load balancer being unreachable from the internet.

**Alternatives.** Per-backend auth libraries (duplication, drift, harder to update). Sidecar auth (more components per service). Network-level allow-listing without identity (insufficient).

### D10. Three-tier permission model: IdP ceiling, platform groups, effective permission

**Decision.** Identity providers map users to IdP groups; each IdP group maps to a (role, scope) ceiling. The platform manages its own groups, memberships, dataset grants, and group claims. Effective permission is the most permissive grant capped by the ceiling.

**Why.** Separates "what the organisation says about this person" (IdP) from "what this platform has granted" (platform groups). Platform admins cannot accidentally exceed organisational role boundaries. IdP-side group changes flow through without re-grant work.

**Trade-off.** Two layers to administer.

**Alternatives.** Permissions purely from IdP (loses platform-specific grants). Permissions purely platform-managed (loses ceiling enforcement; admins have to maintain whatever the IdP knows).

### D11. Key-value store for authorisation, not a relational database

**Decision.** Authorisation policies, ceilings, group memberships, dataset grants, API keys, and RLS configuration all live in a key-value store with single-table designs where appropriate.

**Why.** Single-digit-millisecond reads for every authorisation lookup. Function-runtime authoriser runs outside a VPC (no cold-start penalty). Pay-per-request billing matches request volume.

**Trade-off.** Queries are partition-key oriented; ad-hoc relational queries are not supported. Some authorisation analyses require scanning, which is acceptable because such analyses are rare.

**Alternatives.** Relational database (richer query but adds VPC-bound cold starts or data-API latency). In-memory store (would still need a persistent store of record).

### D12. API keys hashed at rest; raw key returned only once

**Decision.** API keys are random opaque tokens. The platform stores only a SHA-256 hash of the key with its metadata; the raw key is returned at issuance and never retrievable thereafter.

**Why.** Stolen-database scenarios do not yield usable keys. The hash-first pattern is standard for password handling and applies cleanly to API keys.

**Trade-off.** Lost keys must be reissued, not recovered.

### D13. Group-level claims merged with JWT claims for RLS

**Decision.** Row-level security is configured per dataset as `(column, claim, operator)`. The effective claim set is the JWT claims merged with claims attached to the user's platform groups, with group claims taking precedence.

**Why.** Avoids requiring per-user attributes in the IdP. A whole council's worth of staff get the right RLS scoping by being added to one group with `{council_id: "..."}` claims.

**Alternatives.** Per-user attributes in the IdP (requires IdP-side admin work and IdP integration for every claim). RLS via SQL views (premature, the dataset registry is the right place for this config).

---

## Compute split

### D14. Container runtime for heavy data engines; function runtime for lightweight handlers

**Decision.** Container runtime hosts: raster tile server, vector tile server, query layer, OGC Coverages, WMTS proxy, routing engine, validation tasks, generation tasks. Function runtime hosts: authoriser, OGC Features (when standalone), STAC API, editing API, upload gate, job API, promotion function, scheduled maintenance.

**Why.** Heavy engines benefit from persistent in-process caches (Parquet metadata, routing graphs, GDAL state); function runtime cold starts and per-invocation isolation defeat those benefits. Lightweight handlers cold-start in hundreds of milliseconds and amortise the runtime overhead well across many small invocations.

**Trade-off.** Two operational substrates instead of one. Resource scaling models differ.

### D15. Three scaling modes — off, minimal, performance

**Decision.** Each service is parameterised by a scaling mode that controls task count and resource allocation. Mode `off` runs zero tasks; `minimal` runs one or two; `performance` runs many pre-warmed tasks with larger allocations.

**Why.** A single deployment template supports demo-scale, development, and production workloads without code change. Scale-to-zero is the default for development; production picks the performance mode.

**Trade-off.** `off` mode incurs cold-start latency on first request. `performance` mode costs significantly more steady-state.

---

## Network and edge

### D16. Internal ALB, API Gateway as sole ingress

**Decision.** The Application Load Balancer (ALB v2) sits in private subnets with a security group that allows ingress only from the VPC Link security group. API Gateway HTTP API is the only path to it. The ALB is not reachable from the public internet.

**Why.** Authorisation cannot be bypassed. Header trust (D9) is grounded in the network topology — clients cannot forge `X-Auth-*` headers because they cannot reach the ALB at all.

**Prior iteration.** The ALB was once **internet-facing**, in public subnets. The design relied on convention — "all traffic should go through API Gateway" — rather than network controls. The ALB was technically reachable directly, which meant a misconfigured client or an attacker could bypass the Lambda authoriser entirely. Closing this took two steps: first restricting the ALB security group to CloudFront IP ranges, then moving the ALB to private subnets and adding the VPC Link as the only path from API Gateway. Anyone implementing this design should make the ALB internal-only from day one; the migration from internet-facing was disruptive (required destroying and recreating dependent stacks).

**Trade-off.** Direct debugging requires going through the gateway or using **ECS Exec** to shell into a task. There is no convenient bypass for ad-hoc curl-against-backend testing.

### D17. CDN with three cache policy classes

**Decision.** The CDN applies three cache policies:
- *Auth no-cache* (1-second TTL) for routes whose responses depend on current permissions.
- *Per-key tiles* (7-day TTL, keyed on credential) for tile and capabilities responses.
- *Per-key metadata* (1-hour TTL, keyed on credential) for capability documents.

**Why.** Tiles are the dominant traffic class and are highly cacheable; aggressive edge caching is the platform's most cost-effective performance lever. Per-key keying ensures every credential is verified at least once.

**Trade-off.** Per-credential caching means N credentials = N cache entries for the same tile. Acceptable; tile cost is small.

---

## Editing

### D18. Asynchronous editing pipeline via AWS Step Functions

**Decision.** Edits are decoupled from the request that initiates them. The request layer accepts an intent and payload, writes a job record to DynamoDB, and invokes **Step Functions** which orchestrates validation (Fargate task), generation (Fargate task), and promotion (Lambda) as discrete states. Retry policies with exponential backoff cover transient `EcsAmazonECSException` and `States.Timeout` errors; catch blocks route to the failure handler.

**Why.** Pipeline runtimes can be tens of seconds to minutes; synchronous handling would require long-lived request handlers and tight coupling. Step Functions provides visual execution history (auditable in the AWS console), built-in retry, and clean failure routing.

**Alternatives.** EventBridge with separate Lambdas chained by events (more flexible for non-linear flows but loses the visual execution audit trail). Building a custom orchestrator (rebuilds what Step Functions provides).

**Trade-off.** Clients must poll the Job API to observe progress. Step Functions has its own pricing model based on state transitions.

### D19. Per-dataset concurrency limit with queueing

**Decision.** One pipeline job at a time per dataset. New jobs submitted while another is active are accepted with `queued` status (HTTP 202) and dequeued when the prior job completes. Enforced via a DynamoDB GSI on `(dataset_id, status)`.

**Why.** Overlapping pipeline runs on the same dataset corrupt GeoParquet partition writes and produce incorrect delta computations for reviewed datasets. Queueing rather than rejection is the better user experience: editors do not have to poll-and-retry; the platform serialises automatically.

**Prior iteration.** The first version of the pipeline accepted any upload and ran it immediately. Two near-simultaneous edits to the same dataset overlapped their partition writes, producing source GeoParquet that contained duplicate features in some partitions and missing features in others, with no way to tell which write was correct. The queueing model was introduced to make this impossible by construction. The first attempt at the fix used **DynamoDB conditional writes** to reject concurrent jobs with HTTP 409; the UX was poor (editors had to retry manually), so the implementation was changed to queue rather than reject.

> *In plain terms:* the platform now serialises same-dataset edits automatically. The editor doesn't have to retry; they just wait a little longer behind whoever submitted first.

**Trade-off.** A backlog on a hot dataset can grow. There is no per-feature locking — conflicts within a single edit are caught at validation, not prevented at submission.

### D20. Reviewed editing through state-machine sessions with delta and difference visualisation

**Decision.** Datasets opt in to a review workflow via a registry flag. Edits to opted-in datasets pass through a session state machine (draft → uploading → submitted → validating → reviewing → approved → promoting → promoted). The generation task produces a small delta PMTiles (only edited features) and a difference PMTiles (geometric ST_Difference) so reviewers can render what is changing.

**Why.** Authoritative datasets (cadastral boundaries, planning zones) need approval gates. Regenerating full datasets for review is wasteful; deltas and differences are small and fast.

**Trade-off.** A dedicated editing API, a state machine, and additional generation work. Acceptable for the value provided.

### D21. SQL-defined validation checks composed into sequences

**Decision.** Validation rules are parameterised analytical-SQL templates stored per check. Datasets reference ordered sequences of checks. Severity (error vs warning) determines whether a check failure blocks promotion.

**Why.** SQL is the natural language for tabular data validation. Spatial extensions cover geometry validity, conflict detection, attribute constraints in the same dialect. New checks do not require deployment.

**Alternatives.** Python plugin checks (more flexible, but requires deployment per check). JSON Schema validation only (cannot express spatial or cross-dataset rules).

### D22. SQL-based bulk data editing for admin data repair

**Decision.** Administrators can submit SQL UPDATE / ALTER statements against a dataset's GeoParquet source. The statement is parsed against a whitelist, run against a draft copy, validated by the standard pipeline, and promoted through the standard flow.

**Why.** When a schema change invalidates existing data, re-uploading is impractical for large datasets. SQL-based repair operates in place, scoped to admin roles, with the same validation gates as any other edit.

**Trade-off.** A new code path that must be carefully sandboxed. The whitelist parser is critical.

### D23. Breaking-change detection on schema mutations

**Decision.** Schema mutations are compared against the current schema for six categories of breaking change (field made required, field deleted, type changed, enum reduced, constraints tightened, additionalProperties restricted). Breaking changes are rejected unless the caller passes `force: true`.

**Why.** Schema and data drift apart silently in distributed systems. The check is cheap and the rejection is informational; admins force through after confirming the data complies.

---

## Standards and interfaces

### D24. OGC standards externally; richer non-standard interface internally

**Decision.** External clients see OGC API Features, OGC API Coverages, OGC WMTS, OGC WMS, STAC, TileJSON, and MVT. Internal richer operations (spatial computation, routing, joins) are exposed through GraphQL, separate from the OGC surface.

**Why.** Standards are durable; the internal interface is free to evolve. Standards consumers do not need to learn GraphQL; rich-application consumers benefit from a typed, composable interface.

### D25. Service-agnostic URL paths

**Decision.** Public URLs reflect *capability*, not *implementation*: `/tiles/vector/*`, `/tiles/raster/*`, `/features/*`, `/coverages/*`, `/wmts/*`. Implementation-specific URL components are kept inside the platform.

**Why.** Implementations can be swapped without breaking client URLs. The contract is the URL pattern, not the software behind it.

### D26. The OGC Features API can be a standalone Lambda or a façade over the query layer

**Decision.** Deployments that need only standards-compliant feature access build the OGC Features API as a **standalone AWS Lambda** that queries GeoParquet on S3 with DuckDB directly. Deployments that include the query layer build the OGC Features API as a thin **Lambda façade** that calls GraphQL.

**Why.** The query layer's complexity is unjustified for deployments that do not need rich spatial operations. The OGC contract is independent of how it is satisfied internally.

**Prior iteration.** Both shapes have actually existed in this platform's history. The platform's *original* OGC Features API was a **Fargate service running DuckDB** directly — a third shape, which is now deprecated in favour of one of the two above. When the GraphQL query layer was introduced for richer queries, the Fargate Features service was refactored into a thin Lambda façade (current shape B) so the spatial engine wasn't duplicated. The Fargate version's code was then deleted. The Lambda-standalone shape (A) is what the platform *would* deploy if it didn't include the query layer; it has not been the production shape historically but is the recommended starting point for new OGC-only deployments. The deletion of the Fargate version (and the move to Lambda for the façade) reduced cold-start latency from 5–8 seconds (VPC-bound Fargate) to about 200 milliseconds.

**Revisit if.** Cross-deployment standardisation becomes important (e.g. a single implementation has to serve both use cases).

---

## Workflow and deployment

### D27. Single-branch deployment with environment profiles and tag-based promotion

**Decision.** A single source branch targets all environments. Environment profiles (in code, parameterised by context variables) determine which service groups are deployed where. Promotion to test and prod is gated by version tags.

**Why.** Eliminates branch drift, cherry-pick complexity, and infrastructure-code merge conflicts. Tags are immutable release artefacts that permanently record what was deployed.

**Trade-off.** Requires discipline in environment-aware code paths.

### D28. Stable workflow engine, not custom orchestration

**Decision.** Editing pipeline orchestration uses a cloud-native workflow engine with built-in state, retry, and execution-history visibility.

**Why.** Visual execution history is valuable for operators and audit. Built-in retry policies handle transient failures. Cheaper than building these capabilities.

**Alternatives.** Event-driven orchestration via a message bus (more flexible for non-linear flows but loses the workflow's audit trail). Custom orchestrator (rebuilds what the cloud provides).

---

## Identity provider

### D29. Identity provider is external; the platform consumes signed tokens

**Decision.** The platform does not manage identities. It consumes signed JWTs from any OIDC-compliant identity provider. A trusted-issuers list (a deployment parameter) governs which providers are accepted.

**Why.** Identity management is its own domain with its own products. The platform is best served by integrating cleanly with whatever the deploying organisation uses (Cognito, Entra ID, Auth0, Okta, Google Identity, etc.).

**Trade-off.** Federation (e.g. linking SAML or social identity providers) is configured on the IdP side, not in the platform.

### D30. Group-based invitations, resolved on first sign-in

**Decision.** Administrators create invitations (email, group, role) ahead of the user being known to the IdP. A post-authentication hook on the IdP converts invitations into platform memberships on first sign-in.

**Why.** Administrators can provision access before a user exists. The pattern survives IdP-side identity churn (a re-created user retains memberships).

---

## What is deliberately not in the platform

The decisions above describe what was built. Equally important are the decisions about what is *not* in scope.

| Not included | Reason |
|---|---|
| User-facing analytics or BI surfaces | Out of scope (Principle 5). Analytical workloads belong in a separate system reading the platform's GeoParquet directly. |
| Generic data-transformation pipelines | Out of scope. The editing pipeline accepts user-submitted changes; it does not run ETL or derive datasets. |
| Live transactional spatial writes | Out of scope. Aligns with D1; reintroducing this would conflict with the database-less design. |
| Real-time collaborative editing | Out of scope. Sessions are coarse-grained; concurrent editing of the same dataset is not supported. |
| Federation or proxying of external geospatial services | Out of scope. The platform owns its data. |
| Identity provider | External; the platform consumes one. |
| Multi-region active-active deployment | Single-region deployment is the design baseline. Multi-region is achievable through standard cloud patterns but is not designed in. |
| Per-feature locking | The conflict-detection check at validation time is the agreed mechanism for handling overlapping edits. |
| Server-side WMS GetFeatureInfo, SLD styling | OGC WMS is implemented in a deliberately limited form. Styling is client-side. |
| Real-time traffic in routing | The routing engine uses statically-built graphs. |

These exclusions are part of the design, not gaps to be filled. Including any of them would change the platform's character — its cost shape, its operational complexity, or its scope.

---

## Revisiting decisions

The decisions here are deliberate, but they are not permanent. The platform's principle of stable contracts (Principle 4) is what lets decisions be revisited safely:

- A decision about *implementation* (which database engine, which tile server, which routing engine) can change without altering the contracts that clients depend on.
- A decision about *contract* (URL patterns, header formats, OGC compliance) requires versioning to change without breaking clients.

When a decision is revisited, the right unit of work is to update this document, then implement the change. The implementation will then drift from the prior state in a deliberate, recorded way.

This is a living set. Treat it as the canonical record of *why* the platform looks the way it does, and update it when *why* changes.
