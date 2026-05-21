# 01 — Principles

The platform exists to make geospatial data — vector and raster — available to users and machines, under controlled access, with a way to edit it that protects authoritative data from accidental change. Every other property of the system follows from a small set of design principles.

## 1. S3 is the source of truth

All spatial data lives in **Amazon S3** as **cloud-native files** — formats designed to be read efficiently over HTTP byte-range reads without a database server. There is no spatial database in the read path. Serving compute is stateless and ephemeral; data is in the bucket.

This choice eliminates the largest fixed cost of a traditional geospatial platform (an always-on database with patching, backups, connection pooling, failover) and turns durability into a property of S3 (eleven nines), not the application. The platform's prior incarnation used Aurora PostgreSQL with PostGIS and pgSTAC; removing it was the single most consequential architectural decision in the platform's history.

The cloud-native formats used:

- **GeoParquet** for vector features. Columnar, predicate-pushdown-aware, queryable in place by analytical engines such as DuckDB, BigQuery, and Athena.
- **PMTiles** for vector tiles. A single-file archive of MVT tiles, served by HTTP range requests against an object-storage URL.
- **Cloud-Optimized GeoTIFF (COG)** for raster. Internally tiled, with overviews; readable by GDAL-class clients via HTTP range requests.
- **MosaicJSON** for raster mosaics across many COGs.

## 2. Scale-to-zero is a first-class concern

The platform is expected to sit idle for extended periods between demos, dev cycles, and partner work. Every serving component must be able to run at zero capacity and start on demand. A platform with a \$400/month minimum is not the same product as a platform with a \$5/month minimum, even if their warm performance is identical.

This implies:
- No always-on databases for spatial data.
- **Fargate services** that can run at desired-count 0 and scale up on demand via ECS Service Auto Scaling.
- **AWS Lambda** for lightweight handlers (auth, discovery, write coordination) where pay-per-invocation matches usage shape.
- **CloudFront** edge caching that absorbs steady-state traffic so back-end services can stay cold.
- **No NAT Gateways** where avoidable — VPC endpoints to S3 and DynamoDB instead, eliminating ~\$130/month per environment of always-on cost.

Three explicit scaling modes are offered — *off*, *minimal*, *performance* — and the entire infrastructure is parameterised by them via AWS CDK context. See [12 Deployment](12_DEPLOYMENT.md).

## 3. Standards at the edge, pragmatism inside

External interfaces speak the standards consumers expect:
- **OGC API - Features** for vector features (cataloguing, query, single-feature retrieval).
- **OGC API - Coverages** for raster data access.
- **OGC WMTS 1.0.0** and **OGC WMS 1.3.0** for desktop-GIS interoperability.
- **STAC 1.0.0** for spatial data discovery.
- **TileJSON** and **MVT** for web mapping clients.

Internal capabilities are exposed through a richer, non-standard interface — **GraphQL** — that supports composable spatial operations, network routing, and cross-dataset queries. The OGC standards are stable contracts; the internal interface is free to evolve. See [07 Query Layer](07_QUERY_LAYER.md).

This separation matters: a vendor or partner who only needs OGC compliance does not have to learn the internal interface, and the standards-compliant surface does not need to bend to accommodate every internal feature.

## 4. Modular, replaceable components behind stable URL contracts

Every public capability is reached by a service-agnostic URL path: `/tiles/vector/*`, `/tiles/raster/*`, `/features/*`, `/coverages/*`, `/wmts/*`, `/stac/*`, `/routing/*`, `/rest/*`. The implementation behind each path can be swapped — a different tile server, a different feature engine, a different identity provider — without changing the URL contract that clients depend on. ALB listener rules with `CfnListenerRule` priorities make this concrete: each path prefix is one rule pointing at one target group.

This is the most important property for long-term maintenance. Software dates faster than data. The platform has used this property in earnest: Martin replaced by go-pmtiles for vector tiles, Aurora pgSTAC replaced by a DynamoDB-backed Lambda for STAC, Fargate Features API replaced by a Lambda over GraphQL — all without changing client URLs. Treating implementations as substitutable, and contracts as durable, lets the platform absorb upstream change.

## 5. The platform serves and edits, but does not transform or analyse

This is a serving and editing system, not an analytics or ETL system. It does not:

- Run scheduled transformations to produce derived datasets.
- Provide a user-facing SQL surface for ad-hoc analytical queries.
- Compose multi-stage analytical workflows.
- Hold a data warehouse.

It does:

- Store authoritative datasets and serve them through standards-compliant APIs.
- Accept edits to those datasets through a reviewed pipeline, validate them, regenerate serving artefacts, and atomically promote them to live.
- Maintain a row-level history for auditing.
- Offer admin-level bulk-correction tools for fixing data that has become inconsistent with a schema (this is data repair, not transformation).

Where analytical or ETL workloads are needed, they belong in a separate system that reads the platform's GeoParquet from object storage directly. The GeoParquet layout is designed to make that read-only consumption easy.

## 6. Async editing over synchronous writes

User-initiated edits do not run inline with the HTTP request. Uploads land in object storage; a workflow engine orchestrates validation, tile generation, and promotion as discrete steps. The user gets a job identifier and watches it move through states.

This decoupling is what makes scale-to-zero compatible with real edit work: the request layer can be cold and the pipeline can spin up containers only when there is work to do. It also makes reviewed editing natural — once an edit is decoupled from a request, inserting an approval step between validation and promotion is a state transition, not a re-architecture.

See [11 Editing Pipeline](11_EDITING_PIPELINE.md).

## 7. One authorisation layer, many backends

Every request entering the platform passes through a single **API Gateway HTTP API custom Lambda authoriser** that resolves identity (from an OIDC JWT or an API key) into a permission context. API Gateway's parameter-mapping then forwards the request to the relevant backend over **VPC Link** to an **internal ALB**, with the context attached as trusted `X-Auth-*` headers. Backends do not validate tokens themselves; they read the headers.

This concentrates the security-critical code in one place, makes adding a new backend a matter of writing an ALB listener rule, and lets the authorisation model evolve without touching every service.

See [03 Authorisation](03_AUTHORISATION.md).

## 8. Partitioning for size, deduplication on read

Vector datasets can grow to millions of features. The platform partitions GeoParquet sources spatially (a Hive-style layout by tile coordinates: `source/{dataset}/z={z}/x={x}/y={y}/data.parquet`) so that bounding-box queries only read the files they need. Features that straddle partition boundaries are written to every tile they intersect, with full geometry; reads deduplicate on feature identifier using DuckDB's `DISTINCT ON`.

This is the inverse of the typical "partition by attribute, clip at boundaries" approach. It makes editing efficient (one feature's edit rewrites a handful of small files, not the whole dataset) and makes bbox reads cheap (predicate pushdown on partition keys, then row-group statistics pushdown inside Parquet). See [04 Data Layout](04_DATA_LAYOUT.md).

## 9. A garden, not a cathedral

The platform is a collection of small services connected by stable contracts. New capabilities are added by writing new components against the same contracts, not by extending a monolith. Some pieces will be experiments. Some will be temporary. Some will outgrow their current form. The architecture is designed to accommodate this without rework.

## Non-goals, restated

The platform does **not**:

- Serve as a general-purpose database.
- Run analytical or BI queries on behalf of users.
- Provide a generic data-transformation pipeline.
- Federate or proxy external geospatial services.
- Manage identities itself (it consumes them from a chosen identity provider).
- Provide collaborative real-time editing (edits are session-grouped, not concurrent).
- Guarantee instantaneous permission revocation (revocation is eventual, on the order of seconds to minutes).

Holding these non-goals firmly is what keeps the system small enough to operate at scale-to-zero cost while still doing its core job well.
