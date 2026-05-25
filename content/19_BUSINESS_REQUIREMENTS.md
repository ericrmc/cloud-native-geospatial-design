# 19 — Business Requirements

This document lists the business and technical requirements the platform fulfils, expressed as evaluation criteria rather than acceptance tests. It is intended for teams considering whether the platform is a good fit for a project, programme, or replacement candidate — letting them check the platform's coverage of their needs before commissioning new bespoke systems.

It is not a roadmap, a contract, or a guarantee. It is a frank reading of what is in the design, what is in adjacent reach, and what is deliberately not the platform's role.

## How to read the status column

| Status | Meaning |
|---|---|
| **Met** | Explicitly designed and exercised through the prototype. Section references point to where the design is specified. |
| **Partial** | Some aspects are met; others are not. Notes describe what is and what is not. |
| **Planned** | Documented in [17 Further Directions](17_FURTHER_DIRECTIONS.md) as a sketched extension. Not built; the platform's substrate fits the requirement and a design has been outlined. |
| **Adjacent** | Not explicitly designed, but the platform's architecture could absorb it without architectural change. Likely the smallest delta for a future team to add. |
| **Out of scope** | Deliberately not in the platform's role. The architecture is shaped against this, and pursuing it would mean a different platform. Notes explain why and what alternative pattern fits better. |

The platform is positioned as a **state-of-the-art serverless spatial platform** for hosting, securing, serving, and editing spatial data. Anything outside that framing — heavy analytics, transactional spatial writes, federated proxying, bespoke field tools — sits in *Adjacent*, *Planned*, or *Out of scope*.

---

## Functional requirements

### 1. Data ingestion

| Requirement | Status | Notes |
|---|---|---|
| Bulk vector upload (GeoParquet) | Met | Presigned S3 URL → validate → partition → tile → promote, fully automated. See [11 Editing Pipeline](11_EDITING_PIPELINE.md). |
| Bulk vector upload (GeoJSON) | Met | Same pipeline as GeoParquet; converted on ingest. Practical size ceiling around 1–2 GiB before GeoParquet is recommended. |
| Bulk vector upload (Shapefile, GeoPackage, KML) | Adjacent | Not natively supported. A small Lambda shim using GDAL/OGR converts to GeoParquet before the pipeline. Recommended pattern for legacy datasets. |
| Feature-level edits (GeoJSON via Features API) | Met | Authenticated, attribute-aware, validated. See [11 Editing Pipeline](11_EDITING_PIPELINE.md). |
| Raster ingest (Cloud-Optimised GeoTIFFs) | Met | COGs placed on S3 and registered via MosaicJSON; no in-platform reprocessing. See [08 Raster Services](08_RASTER_SERVICES.md). |
| Raster ingest (non-COG TIFFs) | Adjacent | The platform expects COGs. A pre-conversion step (GDAL `gdal_translate -of COG`) is the recommended pattern. A managed conversion Lambda is sketched but not built. |
| Reference-data ingest (no copy) | Met | Datasets can be registered against external S3 paths without copying. Useful for shared imagery archives. |
| Format validation | Met | Schema, geometry validity, projection, attribute types checked before promotion. |
| Schema enforcement | Met | Dataset-level schemas declared on registration; rejects on schema drift. |
| Automatic conversion to optimised formats | Met | Vector → GeoParquet + PMTiles; raster expected as COG. |
| Automatic spatial partitioning | Met | Hive-style `z=/x=/y=` partitioning on GeoParquet; tunable per dataset. See [04 Data Layout](04_DATA_LAYOUT.md). |
| Delta-only ingest | Partial | Append-only writes with `DISTINCT ON (id)` dedup are supported. True change-set ingest (only new/changed rows from a remote system) is a client responsibility. |
| Idempotent re-ingest | Met | Identical uploads produce no new rows; ingest pipeline keys on content + dataset version. |
| Large file handling (multi-GiB) | Met | Fargate validation/generation tasks have ~200 GiB ephemeral storage; multi-part upload supported. |
| Failed-upload recovery | Met | Step Functions retains failure context; partial artefacts cleaned up; resumption is by re-upload. |
| Streaming ingest (Kafka, Kinesis) | Out of scope | The platform is a published-artefact serving platform, not a streaming sink. Live ingestion belongs in a streaming layer that lands batches into S3 for the platform to consume. |
| Live transactional writes | Out of scope | No always-on database in the read path. Transactional spatial writes belong in PostGIS or a lakehouse-managed table; the platform's editing pipeline is reviewed-batch, not live-transactional. |

### 2. Data formats and storage

| Requirement | Status | Notes |
|---|---|---|
| Cloud-native formats throughout | Met | PMTiles, GeoParquet, COG, MosaicJSON. All readable directly from S3 via byte-range reads. |
| Object storage as primary store | Met | S3 single bucket, prefix-organised. No primary database for spatial data. |
| No always-on warm engines in read path | Met | The authoriser is on the path (single-digit ms, scale-to-zero compatible); after that, services read object storage directly. See [02 Architecture](02_ARCHITECTURE.md). |
| Per-row history (SCD2) | Met | Append-only Parquet with valid-from/valid-to; vacuum compacts. See [11 Editing Pipeline](11_EDITING_PIPELINE.md). |
| Soft-delete with audit trail | Met | Deletes write tombstone rows; original row remains queryable for history. |
| Cross-dataset spatial joins at rest | Partial | DuckDB in the query layer joins across datasets, scoped to caller permissions. Joins across hundreds of millions of rows are CPU-bound and slow; bulk analytical joins belong in a lakehouse. See [18 Lakehouse Integration](18_LAKEHOUSE_INTEGRATION.md). |
| External-table federation | Out of scope | The platform owns its data. Federated query against external warehouses is a lakehouse pattern; the integration page describes how the two co-exist. |

### 3. Vector data serving

| Requirement | Status | Notes |
|---|---|---|
| Vector tiles (MVT via PMTiles) | Met | Served by go-pmtiles on Fargate, byte-range reads from S3, ETag-aware. See [05 Vector Tiles](05_VECTOR_TILES.md). |
| OGC API Features | Met | GeoJSON responses, bbox + attribute filtering, pagination, conformance classes documented. See [06 OGC Features API](06_OGC_FEATURES_API.md). |
| Filter by bounding box | Met | Pushed into Parquet predicate pushdown; chunks outside bbox skipped at read time. |
| Filter by attribute | Met | Parquet column predicates pushed down where the column is partitioned or has min/max statistics. |
| Pagination of feature responses | Met | Cursor-based, stable across requests. |
| TileJSON / capabilities documents | Met | Per dataset; published for both PMTiles and OGC Features. |
| Vector style hints | Partial | Tile metadata carries layer schema; style suggestions are documented per dataset but not auto-generated. Recommended layer styles can be hand-published per dataset. |
| Multi-zoom support | Met | PMTiles archives carry the full zoom pyramid; tile generation tunes min/maxzoom per dataset. |
| Server-side label generation | Out of scope | Labels are a client-side rendering concern. The platform serves geometry + attributes; clients (MapLibre, ArcGIS, QGIS) apply label rules. |

### 4. Raster data serving

| Requirement | Status | Notes |
|---|---|---|
| Raster tiles (PNG/WebP) | Met | titiler-style Fargate service reads COGs via MosaicJSON, returns tile bytes. See [08 Raster Services](08_RASTER_SERVICES.md). |
| WMTS interface | Met | Standards-compliant; usable from QGIS and ArcGIS directly. |
| WMS interface | Met | Provided for legacy clients. |
| Time-enabled raster (mosaic-of-time) | Met | MosaicJSON manifests scoped by acquisition date; clients pass time dimension. |
| OGC API Coverages | Met | Elevation and continuous-field rasters exposed as coverages. |
| Multi-band raster (3+ bands) | Met | Band combination expressions evaluated at tile-render time; common indices (NDVI etc.) presetable per dataset. |
| Reprojection on the fly | Partial | Limited; the platform serves in the tile-pyramid CRS (typically Web Mercator). Other CRSes are reprojected at the WMS layer with quality caveats. Heavy reprojection workloads belong upstream of ingest. |
| Server-side rendering with styling | Partial | Default colour ramps and stretches provided per dataset; custom render styles per request supported via render parameters. Complex cartography is a client responsibility. |
| Vector overlays burnt into rasters | Out of scope | Composite render is a client capability. The platform serves raster and vector independently; the client composes. |

### 5. Network routing

| Requirement | Status | Notes |
|---|---|---|
| Point-to-point routing | Met | Valhalla, exposed via GraphQL on the query layer. See [09 Routing](09_ROUTING.md). |
| Drive-time isochrones | Met | Valhalla isochrone endpoint wrapped as GraphQL. |
| Map matching (GPS traces to roads) | Met | Valhalla `trace_attributes` wrapped as GraphQL. |
| Snap-to-road | Met | Valhalla `locate` wrapped as GraphQL. |
| Multi-mode travel costs (car, bike, pedestrian) | Met | Valhalla profiles selectable per request. |
| Public transport routing | Adjacent | OpenTripPlanner is the recommended substitute for transit; the routing slot in the platform is profile-based and could host OTP alongside or instead of Valhalla. Not currently built. |
| Time-dependent routing (traffic, closures) | Adjacent | Valhalla supports time-of-day costing on historical traffic tiles; the platform's graph build does not currently include traffic. A traffic-ingest pipeline would be additive. |
| Multi-modal routing (drive + walk + transit) | Adjacent | Engine choice and graph composition required; out of the box not provided. |
| Custom routing profiles (heavy vehicles, hazmat) | Partial | Valhalla supports truck profiles natively; the platform exposes them via GraphQL. Custom-cost profiles (height/weight/hazmat overlays) are configurable but require graph rebuild. |
| Geocoding | Planned | Sketched in [17 Further Directions](17_FURTHER_DIRECTIONS.md). Pelias is the recommended substrate. |
| Reverse geocoding | Planned | Same sketch as geocoding. |

### 6. Spatial query and analysis

| Requirement | Status | Notes |
|---|---|---|
| Spatial predicates (intersects, contains, within, disjoint) | Met | DuckDB Spatial executes these against GeoParquet. Exposed via GraphQL. See [07 Query Layer](07_QUERY_LAYER.md). |
| Distance and nearest-neighbour | Met | DuckDB Spatial; results stream as GeoJSON. |
| Buffer and other geometry construction | Met | DuckDB Spatial geometry functions; exposed as GraphQL fields. |
| Aggregation queries (count by region, sum within polygon) | Met | DuckDB SQL aggregation against GeoParquet. |
| Cross-dataset joins | Partial | Supported up to mid-millions of rows; bulk warehouse-scale joins belong in a lakehouse. |
| Programmatic SQL access | Adjacent | The query layer is GraphQL, deliberately. Direct SQL access is not exposed externally to keep the contract stable and the surface area small. A read-only DuckDB-over-HTTP shim would be the smallest add. |
| BI dashboard back-end (Tableau, Power BI, Superset) | Out of scope | These tools want JDBC/ODBC or warehouse SQL. The platform is a serving platform, not a BI back-end. See [18 Lakehouse Integration](18_LAKEHOUSE_INTEGRATION.md) for the right pattern. |
| Ad-hoc end-user SQL surface | Out of scope | Same as above; query layer is GraphQL by design. |

### 7. Discovery and catalogue

| Requirement | Status | Notes |
|---|---|---|
| STAC API | Met | Lambda-backed, reads from the DynamoDB datasets registry. See [10 Discovery](10_DISCOVERY.md). |
| Catalogue API (richer admin metadata) | Met | Policy API `/rest/datasets/*` routes; per-caller filtering. |
| Per-user catalogue filtering | Met | The catalogue is always scoped to what the caller is allowed to see. Anonymous callers see public datasets only. |
| Dataset metadata (provenance, schema, extents, lineage) | Met | Schema, spatial extents, temporal extents, owner, contact, licence captured at registration. |
| Asset linking to serving endpoints | Met | Each dataset record carries links to its tile, feature, raster, or coverage endpoints. |
| Full-text dataset search | Partial | Substring matching on titles and descriptions is supported. Semantic search (embeddings, natural language) is planned. |
| Faceted browse (by tag, owner, theme) | Partial | Tag and owner facets supported; advanced faceting (e.g. by lineage, by upstream system) requires schema extension. |
| Natural-language dataset discovery | Planned | Sketched in [17 Further Directions](17_FURTHER_DIRECTIONS.md) — embeddings + a small LLM over catalogue records. |
| External catalogue harvesting (CSW, ISO 19115) | Adjacent | The platform does not federate external catalogues. A harvester Lambda writing into the registry is the recommended pattern. |
| Lineage graph visualisation | Adjacent | Lineage fields are captured; a graph-rendering surface is not built. |

### 8. Authorisation and identity

| Requirement | Status | Notes |
|---|---|---|
| Centralised authorisation across all services | Met | Single Lambda authoriser in front of every backend. See [03 Authorisation](03_AUTHORISATION.md). |
| OIDC / JWT support | Met | Trusted-issuers list; signature, expiry, issuer, audience all validated. |
| Cognito as default IdP | Met | First-sign-in trigger converts invitations into memberships. |
| External IdP federation (Entra ID, Auth0, Okta, Google) | Met | Configured via trusted-issuers list. |
| API keys | Met | SHA-256 hashed, owner-scoped, revocable. |
| Role hierarchy (admin → editor → viewer) | Met | Documented in [03 Authorisation](03_AUTHORISATION.md). |
| Group-based permissions | Met | Group memberships from the IdP or from platform-managed groups. |
| Row-level security (RLS) | Met | Filter expressions per group, evaluated server-side against trusted headers. |
| Dataset-level grants | Met | Read, write, admin grants per dataset, per group or per user. |
| Anonymous / public access | Met | Explicit public-access opt-in per dataset. |
| Audit logging of access decisions | Partial | Authoriser writes structured logs; a queryable audit surface is not built. Logs land in CloudWatch and can be exported to S3 + Athena. |
| Per-credential rate limiting | Adjacent | API Gateway throttling is global; per-credential quotas are configurable but not exposed as a self-service surface. |
| Multi-factor authentication | Adjacent | Cognito supports MFA; configuration is at the IdP, not the platform. |
| Just-in-time access elevation | Adjacent | Not built. The model is static grants; temporary elevation is a procedural process. |

### 9. User and group management

| Requirement | Status | Notes |
|---|---|---|
| Self-service group creation | Met | Admins create groups, assign members, define grants. |
| Email invitations | Met | First-sign-in trigger converts invitation tokens into memberships. |
| API key lifecycle (issue, revoke, rotate) | Met | Self-service for owners; admin override available. |
| Permission propagation latency guarantees | Met | Documented; authoriser cache TTL is the dominant factor (single-digit minutes). |
| SCIM provisioning | Adjacent | Not implemented. For enterprise IdPs, group sync via SCIM would replace the invitation flow. |
| Delegated administration | Partial | Dataset owners can grant access to their own datasets without platform-admin involvement. Sub-tenant administration (group admins) is not built. |
| Service accounts | Met | API keys serve this role; no separate service-account abstraction. |

### 10. Editing workflows

| Requirement | Status | Notes |
|---|---|---|
| Edit sessions | Met | Per-dataset, per-user; isolated working copies. See [11 Editing Pipeline](11_EDITING_PIPELINE.md). |
| Per-dataset concurrency control | Met | Optimistic locking via DynamoDB conditional writes. |
| Feature-level edits (web client, API) | Met | GeoJSON via Features API. |
| Bulk SQL-based editing | Met | DuckDB-backed; supports `UPDATE`, `INSERT`, `DELETE` against the working copy. |
| Validation before promotion | Met | Same validation as ingest; reviewer must clear all errors before promotion. |
| Reviewer approval workflow | Met | Edit sessions submitted for review; reviewer sees delta + diff PMTiles. |
| Delta and diff visualisation | Met | Pre-rendered tiles showing additions, modifications, deletions against the current authoritative dataset. |
| Promote to authoritative | Met | Atomic; serving artefacts swapped server-side; clients see new tiles on next request via ETag refresh. |
| Rollback / revert | Met | Cherry-pick revert from history; producing the inverse delta as an edit session. |
| Concurrent edit conflict handling | Met | Conflicts surface at promotion; reviewer resolves before merge. |
| Schema migration support | Partial | Adding columns is supported; renaming or restructuring requires a new dataset version. |
| Offline editing | Planned | Field-capture sketch in [17 Further Directions](17_FURTHER_DIRECTIONS.md). |

### 11. Audit and history

| Requirement | Status | Notes |
|---|---|---|
| Per-row history (SCD2) | Met | Append-only Parquet; valid-from / valid-to ranges. |
| Versioned datasets viewable side-by-side | Met | Any historical version queryable as a dataset. |
| Time-travel queries | Met | Query the dataset as of any past timestamp. |
| Edit attribution (who, when, what) | Met | Per-row, retained for the lifetime of the dataset history. |
| Cherry-pick revert | Met | Single edits or whole sessions can be inverted as a new edit. |
| Vacuum / compaction | Met | Scheduled Lambda compacts the append-only history to balance query speed and storage cost. |
| Cryptographic provenance (signed assertions) | Out of scope | Not the platform's role. If required, the assertion layer sits above the catalogue. |
| Per-attribute change log | Partial | History is per-row, not per-attribute. Per-attribute diff is computed at query time from row versions. |

### 12. Client integration

| Requirement | Status | Notes |
|---|---|---|
| QGIS (WMTS, WMS, OGC API Features) | Met | API key passes via header; tested. See [14 Client Integration](14_CLIENT_INTEGRATION.md). |
| ArcGIS (Esri WMTS/WMS adapter) | Met | Standards-compliant interfaces consumed natively. |
| Any XYZ/MVT tile client (MapLibre, Mapbox GL JS, Leaflet) | Met | URL templates published in TileJSON. |
| Programmatic Python access | Met | API key + standard HTTP libraries. DuckDB can read GeoParquet directly via signed URLs. |
| Programmatic R access | Met | Via `sf`, `terra`, and standard HTTP libraries. |
| Programmatic JavaScript / TypeScript access | Met | Via `fetch` + standard parsers. |
| First-party React + MapLibre web client | Met | Catalogue browse, editing, review, GraphiQL exploration. See [15 Map Client](15_MAP_CLIENT.md). |
| GraphiQL exploration surface | Met | Authenticated, scoped to caller permissions. |
| OpenAPI specification | Partial | OGC endpoints publish OpenAPI 3.0 documents; the GraphQL surface has its own schema introspection. A consolidated cross-surface API document is not built. |
| Mobile SDK (iOS, Android) | Adjacent | Standard HTTP clients work; no first-party SDK is provided. |
| Desktop bulk export tool | Adjacent | GDAL/OGR with the platform's URLs works today; a dedicated export tool is not built. |

### 13. Reporting and outputs

| Requirement | Status | Notes |
|---|---|---|
| Static map image export (PNG/JPEG) | Adjacent | Achievable by composing tiles client-side; no server-side export endpoint. |
| Print-quality cartographic layouts | Out of scope | Cartographic composition belongs in QGIS or a layout-engine product. The platform supplies the data; the layout tool composes. |
| PDF reports with embedded maps | Planned | Sketched in [17 Further Directions](17_FURTHER_DIRECTIONS.md). |
| Scheduled report generation | Planned | Same sketch — Step Functions + headless renderer. |
| Data export as Shapefile / GeoPackage / KML | Adjacent | Achievable by client-side GDAL conversion from GeoParquet or GeoJSON. Server-side export shim is a small add. |

### 14. Notifications and subscriptions

| Requirement | Status | Notes |
|---|---|---|
| Dataset change subscriptions | Planned | Sketched in [17 Further Directions](17_FURTHER_DIRECTIONS.md). EventBridge + per-subscription filter. |
| Webhook notifications | Planned | Same sketch. |
| Email alerts | Planned | Same sketch; SES integration. |
| SMS or push notifications | Out of scope | Notification fan-out is a generic infrastructure concern; the platform should emit events, not deliver every channel. |
| Server-Sent Events / WebSocket push | Out of scope | The architecture is request/response and CDN-cached. Long-lived push connections would require a stateful component the platform does not have. Polling against ETags is the recommended pattern. |

### 15. Field capture

| Requirement | Status | Notes |
|---|---|---|
| Mobile data collection | Planned | Sketched in [17 Further Directions](17_FURTHER_DIRECTIONS.md). |
| Offline editing with sync | Planned | Same sketch. |
| Photo capture against features | Planned | Same sketch; S3 attachments addressable by feature ID. |
| Form-based data entry | Adjacent | Schema is captured per dataset; rendering a form is a client concern. Standard form-builder integrations are achievable. |

### 16. Change detection and intelligence

| Requirement | Status | Notes |
|---|---|---|
| Imagery change detection | Planned | Sketched in [17 Further Directions](17_FURTHER_DIRECTIONS.md). |
| Feature-level change alerts (someone edited a road I care about) | Adjacent | Subscriptions plus per-row history would deliver this; not built. |
| Computer-vision-derived features (extracted from imagery) | Planned | Sketched; substantial pipeline work. |
| Agentic data assistant | Planned | Postscript in [10 Discovery](10_DISCOVERY.md); intentionally aspirational. |

### 17. Live data

| Requirement | Status | Notes |
|---|---|---|
| Live vehicle / sensor feeds | Planned | Sketched in [17 Further Directions](17_FURTHER_DIRECTIONS.md). Polling pattern over ETag'd tile or feature endpoints; backed by frequent batch refresh. |
| Sub-second latency live data | Out of scope | The architecture is CDN-cached and batch-refreshed. Sub-second feeds need a streaming layer alongside, not inside, this platform. |

---

## Non-functional requirements

### 18. Performance

| Requirement | Status | Notes |
|---|---|---|
| Tile p50 latency under CDN warm | Met | Single-digit ms from CDN edge; no backend touch. |
| Tile p99 latency on cold path | Met | Sub-second target on cold path; PMTiles + go-pmtiles + Fargate cold start. |
| Feature query p50 latency | Met | Sub-second for bbox + attribute predicates against partitioned GeoParquet. |
| Feature query p99 on large datasets | Partial | Tens of millions of rows: sub-second. Hundreds of millions: depends on selectivity; the architecture biases towards good selectivity via partitioning. Bulk analytical workloads belong elsewhere. |
| Authoriser latency | Met | Single-digit ms with DynamoDB lookup; cached at API Gateway per request. |
| CDN edge cache hit rate | Met | Tile classes are designed for high hit rate; per-credential cache keys keep auth correct. |
| Routing query latency | Met | Tens to low hundreds of ms for typical metro-area routes. |

### 19. Scalability

| Requirement | Status | Notes |
|---|---|---|
| Concurrent users | Met | No fixed ceiling; the read path is stateless and CDN-fronted. |
| Concurrent tile request rate | Met | CDN absorbs the bulk; origin Fargate scales by ALB target. |
| Dataset size (vector, rows) | Met | Hundreds of millions of rows demonstrated. Billion-row datasets need partition tuning; documented. |
| Dataset size (raster, TB-scale) | Met | COG + MosaicJSON is the standard pattern; no platform-level ceiling. |
| Number of datasets | Met | DynamoDB datasets table; tens of thousands of datasets handled. |
| Geographic scaling (multi-region) | Adjacent | Single-region by default. Multi-region requires CloudFront + replicated S3 + DynamoDB Global Tables. Documented but not built. |
| Scale to zero when idle | Met | Tile servers, query layer, raster servers all scale to zero on configurable idle timeouts. Lambda services have no warm pool. |

### 20. Cost

| Requirement | Status | Notes |
|---|---|---|
| Pay-per-request model | Met | Lambda, API Gateway, CloudFront, S3 — all consumption-priced. |
| No always-on warm pools (default) | Met | Configurable per environment; production may keep minimum capacity for cold-start mitigation. |
| Predictable cost at wide adoption | Met | Cost scales with traffic; no per-user licence model. |
| CDN egress optimised | Met | Tile cache classes designed for high hit rate; per-credential keys on dynamic responses only. |
| Storage cost optimisation (Intelligent-Tiering) | Met | S3 Intelligent-Tiering recommended; lifecycle rules for working areas. |
| Per-tenant cost attribution | Partial | Tags + access logs allow cost allocation; a per-tenant cost dashboard is not built. |
| Cost ceiling enforcement | Adjacent | AWS Budgets + alarms is the recommended pattern; not in-platform. |

### 21. Reliability and availability

| Requirement | Status | Notes |
|---|---|---|
| Multi-AZ where supported | Met | All AWS services default to multi-AZ within the deployed region. |
| Stateless backends | Met | Tile servers, query layer, OGC Features API, raster servers — all stateless. |
| Graceful degradation under load | Met | API Gateway throttling, CloudFront shielding; documented in [13 Operations](13_OPERATIONS.md). |
| Disaster recovery plan | Met | Documented in [13 Operations](13_OPERATIONS.md). RTO/RPO targets vary by component. |
| RTO (recovery time objective) | Partial | Stateless services: minutes. Stateful (DynamoDB, S3): determined by region. Cross-region DR is adjacent. |
| RPO (recovery point objective) | Met | S3 versioning + DynamoDB PITR give RPO measured in minutes. |
| Health checks and self-healing | Met | ALB health checks; ECS service recovery; CloudWatch alarms wired to PagerDuty integration points. |

### 22. Security

| Requirement | Status | Notes |
|---|---|---|
| TLS in transit | Met | Public endpoints via CloudFront; internal traffic over VPC. |
| Encryption at rest | Met | S3 SSE, DynamoDB encryption, KMS-managed keys recommended. |
| VPC-only internal traffic | Met | ALB is internal; backends not reachable from the public internet. |
| API Gateway as sole public entry | Met | VPC Link to internal ALB. |
| IAM least-privilege | Met | Per-service IAM roles documented in [12 Deployment](12_DEPLOYMENT.md). |
| API key hashing | Met | SHA-256; raw key returned only at issuance. |
| Audit logging | Partial | Structured logs land in CloudWatch; queryable audit surface is not built. |
| Secret management | Met | Secrets Manager for issuer keys, signing keys; no secrets in code or environment. |
| Dependency scanning | Adjacent | Standard ECR scanning; in-platform SBOM publication is not built. |
| Penetration testing posture | Out of scope | A platform-level requirement that the deploying team operationalises. The platform's architecture is shaped for it (small attack surface, single ingress, authoriser in front of everything). |

### 23. Compliance and data governance

| Requirement | Status | Notes |
|---|---|---|
| Single-region data residency (default) | Met | Deployed in one region; data does not cross region boundaries. |
| Configurable region | Met | Region is a deployment parameter. |
| Audit trail for sensitive datasets | Met | Per-row history + access logs combine into an audit story. |
| GDPR-style data subject access requests | Adjacent | The platform supports per-user data extraction by querying the datasets; a self-service DSAR surface is not built. |
| Right-to-be-forgotten | Adjacent | Hard delete (vs soft delete) is supported per-row; an automated DSAR-driven purge is not built. |
| Data classification tagging | Adjacent | Dataset metadata supports tags; a structured classification taxonomy is the deploying team's choice. |
| Logging retention configuration | Met | CloudWatch retention configurable per log group. |
| Regulated-industry deployment (HIPAA, PCI) | Out of scope | The architecture admits regulated deployment, but the platform itself does not ship with certification. The deploying team operates within their accreditation. |

### 24. Operability

| Requirement | Status | Notes |
|---|---|---|
| Centralised monitoring | Met | CloudWatch dashboards per service group; documented in [13 Operations](13_OPERATIONS.md). |
| Alarm definitions | Met | Standard alarms documented; PagerDuty integration is a deployment detail. |
| Runbooks for common incidents | Met | Documented in [13 Operations](13_OPERATIONS.md). |
| DR playbook | Met | Documented in [13 Operations](13_OPERATIONS.md). |
| Cost dashboards | Partial | Cost Explorer recommended; per-service cost dashboards are not pre-built. |
| Capacity planning guidance | Met | Documented in [12 Deployment](12_DEPLOYMENT.md). |
| Blue/green deployment | Met | Fargate service deployment with rolling update; Lambda alias-based traffic shifting. |
| Configuration as code | Met | Recommended pattern is CDK or Terraform; the corpus is implementation-independent. |

### 25. Standards compliance

| Requirement | Status | Notes |
|---|---|---|
| OGC API Features | Met | Conformance classes documented. |
| OGC API Coverages | Met | |
| OGC WMTS | Met | |
| OGC WMS | Met | |
| OGC 3D Tiles (consumption) | Met | Compatible with Cesium / TerriaJS clients out of the box. |
| STAC | Met | Items, collections, conformance. |
| TileJSON | Met | Per dataset; per service surface. |
| MVT | Met | The vector tile wire format. |
| PMTiles | Met | The storage format for tile archives. |
| COG / COPC | Met | Raster (COG) is standard; point cloud (COPC) is planned. |
| GeoParquet | Met | Primary vector storage format. |

### 26. Vendor independence and portability

| Requirement | Status | Notes |
|---|---|---|
| Open formats throughout | Met | PMTiles, GeoParquet, COG, MosaicJSON, STAC — all open. |
| Standard interfaces | Met | OGC, STAC, TileJSON. |
| Open-source engines | Met | DuckDB, go-pmtiles, Valhalla, GDAL, PDAL, Tippecanoe. |
| Portable to other clouds | Partial | Substrate is portable; the AWS-specific layer (ALB rules, API Gateway authorisers, VPC Link, Cognito) is a redesign in another cloud. Documented in [12 Deployment](12_DEPLOYMENT.md). |
| No proprietary lock-in for data | Met | Datasets can be exported via standard APIs at any time. |
| Substitutable engines | Met | Each component is replaceable behind its contract: Valhalla ↔ OSRM, DuckDB ↔ Sedona, go-pmtiles ↔ Martin. |

### 27. Maintainability

| Requirement | Status | Notes |
|---|---|---|
| Modular components | Met | Each component has a small, contracted surface area. |
| Documented design decisions | Met | [16 Design Decisions](16_DESIGN_DECISIONS.md). |
| Documented prior iterations | Met | Each decision page records what was tried and why it changed. |
| Clear contracts at component boundaries | Met | [02 Architecture](02_ARCHITECTURE.md), [03 Authorisation](03_AUTHORISATION.md), [04 Data Layout](04_DATA_LAYOUT.md). |
| Low-skill operational footprint | Met | Most services are managed; no database admin role required. |
| Documented upgrade paths for major engines | Partial | Engine substitution is documented; major version upgrades within a single engine are a standard release process. |

### 28. Observability

| Requirement | Status | Notes |
|---|---|---|
| Structured logging | Met | JSON logs across all components. |
| Metrics per component | Met | CloudWatch standard metrics + custom per-service metrics. |
| Distributed tracing | Partial | X-Ray supported on Lambda and ALB; full request-trace stitching across all components is not turn-key. |
| Per-request audit | Partial | Logs carry caller + decision + dataset; an audit-query surface is not built. |
| Cost-per-request attribution | Adjacent | Tagging supports it; a per-request cost view is not standard. |

---

## Reading by intent

If you are evaluating against a specific need:

- **"Do we still need GeoServer?"** — Read §3 Vector serving, §4 Raster serving, §25 Standards compliance. Most GeoServer use cases are *Met*.
- **"Can we run our editing workflow on this?"** — Read §10 Editing workflows, §11 Audit and history.
- **"Can we replace our access-control mess?"** — Read §8 Authorisation, §9 User and group management.
- **"Will this work for a BI / analytics workload?"** — Read §6 Spatial query, then read [18 Lakehouse Integration](18_LAKEHOUSE_INTEGRATION.md). The answer is "use a lakehouse alongside, not instead."
- **"Will this scale to our user base?"** — Read §18 Performance, §19 Scalability, §20 Cost.
- **"Is this compliant with our security posture?"** — Read §22 Security, §23 Compliance.
- **"Can we run this in [non-AWS cloud]?"** — Read §26 Vendor independence and the deployment chapter's cross-cloud notes.

## When this document is wrong

This is a snapshot. If you find a requirement here that the platform claims to meet but the implementation cannot, that is a documentation bug — log it, and the right page in the corpus should be amended. If you find a requirement marked *Adjacent* or *Planned* that you actually need, that is useful evaluation signal: either the platform needs that work commissioned, or another platform is a better fit for your project.

The point of this document is to make the *fit conversation* short and concrete, not to dress the platform in capabilities it does not have.

---

**Read next:** [20 Glossary and References](20_GLOSSARY_AND_REFERENCES.md) — every term, format, service, standard, library, and peer geospatial stack named across the documentation, with canonical URLs.
