# 17 — Further Directions

This document collects ideas that have been thought through but not built into the core design. The rest of the corpus is the load-bearing material; this page is direction, not commitment. Each section sketches what the capability is, where it would fit, the concrete technology choices that seem appropriate, and what would need to be designed before a build.

> *In plain terms:* a vendor or future team picking up the platform will eventually ask "what's next?" These are the sketches that answer that question, ordered so the most natural extensions come first.

Ordered roughly by ease-of-fit with the existing platform — early entries plug into existing patterns with minimal change; later entries introduce new substrates, new cost shapes, or new operational concerns.

## 1. Semantic dataset discovery — OpenSearch + Bedrock Knowledge Base

The STAC catalogue handles structured discovery: spatial extent, temporal extent, declared keywords. It does not handle *meaning*. A user asking "what data do we have on coastal erosion" wants a result they would not find by keyword match alone — the relevant dataset might be called "Shoreline Recession Polygons 2024" and never use the word "erosion".

Augmenting the catalogue with a semantic search layer closes that gap. **Amazon OpenSearch Serverless** holds an index of every dataset's description, lineage, attribution, and schema fields. **Amazon Bedrock Knowledge Base** manages embeddings and the retrieval contract over that index, exposing semantic search as a single API the discovery agent (or any client) can call. The STAC API stays as it is; semantic discovery is a sidecar over the same dataset registry.

> *In plain terms:* a sidecar to STAC that lets users (and agents) find datasets by what they *mean*, not just what they're labelled.

**Concrete tech to consider.** OpenSearch Serverless, Bedrock Knowledge Base, Bedrock embedding models. Index refresh tied to the editing pipeline's promotion step so new and updated datasets are searchable within minutes.

**What needs designing.** The indexing pipeline (which fields contribute to the embedding, how schema descriptions are summarised). Permission-aware retrieval — KB results must filter by the user's `X-Auth-User-Datasets` (see [03 Authorisation](03_AUTHORISATION.md) for the header contract), not just return everything. Handling of dataset deprecation and retirement so the index stays in sync with the catalogue's lifecycle states. The cost shape: OpenSearch Serverless has a minimum capacity floor, so this adds always-on cost the rest of the platform avoids.

## 2. Geocoding and address search

Forward geocoding ("14 Smith St" → coordinates), reverse geocoding (nearest address to a point), and proximity queries ("features within 200m of this location"). The platform currently has no first-party geocoder; users either consume external services or go without.

OpenSearch's `geo_point` and `geo_shape` field types make this a one-index problem. With an authoritative address dataset ingested, all three operations are standard OpenSearch queries.

**Why it fits.** The auth gate (see [03 Authorisation](03_AUTHORISATION.md)) fronts every backend; OpenSearch sits behind it like any other service. No external geocoder calls — useful for jurisdictions where queries against third-party services would leak data location.

**Concrete tech to consider.** OpenSearch Serverless (shared with the semantic-discovery index above), `geo_point` for address points, `geo_shape` for polygon overlays (council areas, suburbs, flood zones — anything you want to combine with text+spatial queries).

**What needs designing.** The address-normalisation pipeline is the real work: canonical address fabric → indexable documents with consistent CRS, deduplication, alias handling. The serving side is well-trodden in the industry but has not been exercised in this platform. Versioning of the address dataset (point-in-time queries against historical addresses) is a deeper concern that may or may not be in scope.

## 3. Point cloud serving — COPC + auth proxy

LiDAR datasets are typically too large to serve as one file and too detailed to render naively. **Cloud Optimised Point Clouds (COPC)** solve this: a LAZ file reorganised as a clustered octree with a header-resident spatial index. Clients (CesiumJS) request only the octree nodes relevant to their viewport and zoom via HTTP byte ranges — coarse overview first, finer detail as the user dwells.

The platform's role is the same as for PMTiles: store the file in S3, gate access via the auth Lambda, let the client drive the streaming. A thin proxy validates the token, checks dataset permissions in DynamoDB, and forwards byte ranges to S3.

> *In plain terms:* the same byte-range + auth-proxy pattern that already works for PMTiles, applied to LiDAR. The proxy does not need to understand the format — only gate access to it.

**Concrete tech to consider.** PDAL + Entwine (one-time batch per dataset) to convert raw LAZ to COPC, AWS Batch (or a one-off Fargate task following the operator-driven pattern in [08 Raster Services](08_RASTER_SERVICES.md) — choose based on whether builds are recurring or one-shot), STAC's `pointcloud` extension for catalogue entries linked through [10 Discovery](10_DISCOVERY.md), CesiumJS as the client renderer (also see §4).

**What needs designing.** None of this has been built end-to-end. The ingestion pipeline: raw LAS/LAZ on S3 → PDAL normalise (consistent CRS, classification schema, LAS version) → Entwine build → COPC output → STAC item. Existing LiDAR holdings should be audited before the pipeline is written — inconsistent CRS and mixed classification schemes are common and require explicit normalisation steps. Permission gating: byte-range proxy versus presigned URLs with embedded auth scope (presigned URLs are simpler but cannot be revoked once issued). Retention and lifecycle for raw versus COPC files.

## 4. 3D rendering with Cesium / TerriaJS

A 3D companion to the 2D MapLibre map client described in [15 Map Client](15_MAP_CLIENT.md). **TerriaJS**, running on **CesiumJS**, renders point clouds (COPC natively), **OGC 3D Tiles** for textured meshes and photogrammetry, COGs draped over terrain, time-dynamic data, and routing geometry on actual terrain. Shares the dataset catalogue and auth gate with the rest of the platform. 3D Tiles is the natural sibling streaming format to PMTiles and COG for the 3D-asset class — anything produced through the pipeline sketched in §12 will be consumed here without format conversion.

A 3D view is the natural primary surface for some tasks — flythrough of LiDAR, terrain-aware route inspection, infrastructure planning against elevation. The 2D MapLibre client and the 3D Cesium/TerriaJS shell coexist; users choose based on the task.

**Why it fits.** Every data format the platform produces (COG, COPC, MVT, GeoJSON, MosaicJSON) is consumable by CesiumJS in principle. The STAC catalogue is the entry point. The auth gate is unchanged. None of this has been wired up in this platform — the *principle* of fit is sound; the integration work is undone.

**Concrete tech to consider.** TerriaJS as the catalogue/visualisation shell, CesiumJS as the render engine. TerriaJS catalogue items support polling GeoJSON endpoints with a `refreshInterval` for semi-live data; WebSocket CZML for genuinely live operational feeds.

**What needs designing.** Shared session and auth between the 2D and 3D clients so users do not sign in twice. Feature parity for editing — drawing and attribute editing in 3D is a UX problem this design has not approached. Layer-state synchronisation if the user toggles between 2D and 3D views.

## 5. Computer vision inference proxy

A thin FastAPI proxy that fetches an imagery tile from the raster tile server, runs inference (building detection, vehicle detection, vegetation classification), converts pixel-space detections back to geographic coordinates via standard XYZ tile math, and returns a GeoJSON FeatureCollection. MapLibre renders the detections as an overlay layer.

The proxy pattern is the same as the WMTS proxy and the Coverages API described in [08 Raster Services](08_RASTER_SERVICES.md): gate the request, do the work, return geospatial data. Detection output is GeoJSON, which composes with everything else on the platform — including the query layer's spatial operations and the `saveQueryResult` mutation in [07 Query Layer](07_QUERY_LAYER.md), and the editing pipeline in [11 Editing Pipeline](11_EDITING_PIPELINE.md) so a user could promote detection output into a managed dataset.

**Concrete tech to consider.** Samgeo (SAM fine-tuned for geospatial output) handles georeferencing internally and returns GeoJSON natively. Small SAM (`vit_b`) runs acceptably on CPU; for interactive response times, either ECS on EC2 with GPU instances or SageMaker async inference — Fargate does not currently expose GPU. ElastiCache keyed on `(tile_coordinates, detection_type, parameters)` so the same tile does not pay inference twice. The auth gate decides who may call detection at all — it is a permission-gated capability, not an open one.

**What needs designing.** A minimum-zoom guard (small SAM needs zoom 17–19 for building-level detail from typical aerial imagery; allowing detection at lower zoom wastes compute and returns garbage). A parameter API — the raw thresholds (`pred_iou_thresh`, `points_per_side`, `min_mask_region_area`, `stability_score_thresh`) are exposed for advanced users; an agent maps natural-language intent ("only large buildings") to those parameters. The cost trade-off between CPU and GPU instances. Output schema: confidence score in each feature's properties for client-side filtering.

## 6. Multi-agent orchestration — Bedrock AgentCore

The agentic postscript at the end of [10 Discovery](10_DISCOVERY.md) describes the simple shape — one agent over the GraphQL surface, with STAC providing catalogue context. This section describes the elaborate shape: a **supervisor agent** that orchestrates specialist sub-agents, each owning a domain.

```
Supervisor (Bedrock AgentCore)
  ├── Discovery Agent       — Bedrock KB + STAC + catalogue queries
  ├── Cartography Agent     — assembles MapLibre styles, calls tile/feature APIs
  ├── Spatial Query Agent   — OpenSearch, Valhalla, the GraphQL query layer
  └── CV Agent              — calls the CV inference proxy, interprets results
```

**Bedrock AgentCore** provides session memory across conversation turns (so a user can refine — "now add flood zones to that map"), tool-execution lifecycle management, KB integration, **user-token passthrough so the agent never has more permission than the user it serves** (see [03 Authorisation](03_AUTHORISATION.md) for the token-to-headers contract), and an audit trail of agent actions. The audit trail is non-optional for regulated deployments.

**Why it fits.** Every sub-agent is just another authenticated client of an existing platform API. The supervisor coordinates; the sub-agents have narrow tool schemas; the platform does what it already does. Same auth gate, same data, same cost shape per query.

**Concrete tech to consider.** Amazon Bedrock AgentCore for the orchestration runtime, Bedrock Knowledge Base for catalogue retrieval, the OpenSearch + KB combination from §1, the existing platform APIs as tools.

**What needs designing.** Prompts and tool schemas for each specialist agent. KB indexing schema (what fields contribute to the embedding for "find me a dataset like…"). Permission-aware response shaping — the discovery agent must not describe datasets the user cannot access. Fan-out guardrails (an agent that wants to compose fifty isochrones should be bounded; the GraphQL query layer's batch limit from [07 Query Layer](07_QUERY_LAYER.md) provides a server-side floor, but the agent should reason about its own budget). Evaluation — how do you regression-test an agent? Conversational UX patterns for refinement and back-tracking.

## 7. Field data capture

A field-staff app for capturing GPS points, photographs, and form data — the role currently filled by tools like Esri Survey123. Offline-capable (field staff work where connectivity is unreliable), GPS-aware (uses device location), schema-driven (the same dataset JSON Schemas drive the form rendering).

The platform's existing editing pipeline absorbs the submissions: each field outing is an edit session (or a batch of sessions, one per submission), routed through the standard validation → generation → promotion path described in [11 Editing Pipeline](11_EDITING_PIPELINE.md).

**Why it fits.** Schema-driven editing is already a pattern in [15 Map Client](15_MAP_CLIENT.md) via RJSF. Per-dataset permissions, validation rules, and review workflow all apply unchanged. A field app is a new front-end against existing back-end APIs.

**Concrete tech to consider.** Form.io offers an offline-capable form runtime with a familiar form-builder UX — note this is the one explicitly non-AWS substrate suggested in this document; alternatives include a custom React Native app or a Capacitor wrapper around the existing map client. Server-side spatial enrichment on submit: reverse-geocode the captured point against the address dataset (§2), point-in-polygon for council lookup, automatic attachment of the nearest road network feature.

**What needs designing.** Offline reconciliation (last-write-wins, conflict review on sync, or queue-and-prompt). Trip-based session model — does each field outing become one edit session, or one session per submission? Spatial enrichment hooks (which datasets get queried at submit time; how the result attaches to the feature). Photograph handling (S3 upload via presigned URL, EXIF orientation, thumbnails). Form versioning when a dataset's schema changes mid-trip.

## 8. Automated report generation

An agent assembles a written assessment — site context, recent imagery, historical change, surrounding land use, flood and bushfire risk — into a formatted document. The inputs are platform API calls; the work is composition.

**Why it fits.** Every input is already a platform API. The CV proxy (§5) adds detection-derived context. The history queries in [11 Editing Pipeline](11_EDITING_PIPELINE.md) provide change-over-time. The query layer composes spatial operations. An agent is the natural orchestrator. None of this has been built, however; the path described below is unproven.

**Concrete tech to consider.** The multi-agent setup from §6 as the orchestration layer, an ODF or DOCX layout template (ODF is open-format; DOCX has broader installed-base support), headless map rendering for the figures (a small Fargate service that takes a bbox, style, and dimensions and returns a PNG), Bedrock for the prose generation.

**What needs designing.** Report templates — the layout, section structure, which data sources feed which sections per assessment type. The agent's planning prompt — how it decides which datasets to include for a given query. Human-in-the-loop checkpoint — does the draft go to a reviewer before delivery, or directly to the requester? Output format choice (ODF for editability, PDF for finality, both?). Audit trail — every figure and claim should be traceable to the source dataset and version.

## 9. Spatial subscriptions

A user defines an area of interest — polygon, bbox, or point-and-radius — and a dataset they care about. When new features are added or existing features change within that area, they receive a notification.

**Why it fits.** Edits flow through the editing pipeline, which already writes an event log to `metadata/dataset_events/` (see [11 Editing Pipeline](11_EDITING_PIPELINE.md)). A subscription manager listens on those events, filters them against registered AOIs, and dispatches notifications.

**Concrete tech to consider.** DynamoDB for subscriptions (partition key `USER#user_id`, sort key `SUB#sub_id`, AOI stored as GeoJSON in the item). Event-driven Lambda that filters new feature events against AOIs (point-in-polygon for the simple case; a pre-indexed AOI set for scale). Amazon SES or SNS for email and SMS channels; an in-app inbox in the map client (§15) for users who prefer not to receive external messages.

**What needs designing.** AOI matching at scale — per-event point-in-polygon against all subscriptions is fine for hundreds of subscriptions; not for hundreds of thousands. A pre-built AOI spatial index becomes necessary. Notification batching so a bulk update of 1,000 features does not fire 1,000 emails. Client surface for managing subscriptions, snoozing, channel selection. Permissioning — a subscription should not surface features the user cannot otherwise see (see [03 Authorisation](03_AUTHORISATION.md) for the dataset-access contract).

## 10. Change detection

Scheduled comparison of new versus previous aerial captures. The CV inference proxy (§5) runs on both, the differences are computed (features present in the new capture and not the previous, or vice versa), and the result is written as a `change_detection_alerts/` GeoJSON layer. Users with a spatial subscription (§9) covering the affected area are notified.

**Why it fits.** Captures already arrive on a schedule — the operator-driven COG ingest tooling in [08 Raster Services](08_RASTER_SERVICES.md) covers the input side. The CV proxy already produces GeoJSON. The subscription mechanism filters by AOI. Compose them.

**Concrete tech to consider.** EventBridge-scheduled Lambda that triggers per-tile inference on both captures, the existing CV pipeline, the same notification channel as subscriptions.

**What needs designing.** False-positive handling — CV produces noise, especially around tree canopy, shadow movement, vehicle parking. What threshold filters output before users see alerts? The comparison logic itself — true geometric diff via spatial ST_Difference, or detection-presence diff (a building was detected here last year, not this year)? Feedback loop where reviewers mark false positives and the system learns its thresholds.

## 11. Live data — GTFS Realtime and sensor integration

The platform is batch-oriented today: edits land, the pipeline runs, tiles update on a cadence of minutes. A live data surface — vehicle positions, environmental sensor readings, flood gauge levels — would extend it with cadence in the order of seconds, suiting use cases the batch model does not (real-time traffic overlays, live emergency dashboards).

**Why it fits.** OpenSearch's `geo_point` indexing supports high-cadence updates. The map client (15) already supports GeoJSON sources with a polling `refreshInterval`, so a polled OpenSearch endpoint surfaces live data through the existing client without front-end changes.

**Concrete tech to consider.** EventBridge-scheduled Lambda polling external feeds (GTFS Realtime, IoT sensor APIs, hydrology services) and writing to OpenSearch with timestamp and source attribution. Map client polls the OpenSearch endpoint at the desired cadence. For genuinely sub-second data (rare in this domain), a WebSocket fan-out becomes appropriate — but note this introduces a *different* gateway (API Gateway WebSocket APIs or AppSync) and a different auth flow than the rest of the platform's HTTP-API gate; the auth model would need a parallel design.

**What needs designing.** A different cost shape than the rest of the platform — live ingest implies always-on compute, even if low-volume. Retention policy: keep all historical readings (large, expensive), or only the most recent per source (cheap, no replay)? Time-window queries ("last 5 minutes of bus positions") in OpenSearch. UX for live overlays — animation versus snapshot, opacity for older readings, separate styling from authoritative data. Authentication: many external live feeds need credentials of their own that the platform must rotate and protect.

## 12. 3D and visual asset management — VAMS-style extension

3D models, point clouds, CAD, and media don't yet fit anywhere in the platform's serving model — vector and raster handle most of the spatial corpus but not the visual-asset class. AWS Labs' [Visual Asset Management System (VAMS)](https://awslabs.github.io/visual-asset-management-system/) has trodden this path on the same substrate this platform uses: S3 as source of truth, DynamoDB for metadata and policy, Lambda and serverless pipelines for asset transforms, a browser viewer with seventeen-plus built-in plugins for 3D, point cloud, CAD, media, and document formats, and ABAC/RBAC at both the API and data-entity levels. The platform can be extended to absorb the same workloads, or VAMS can sit alongside it behind the existing auth gate.

VAMS is also part of this platform's lineage. Its API-and-data-level access control was one of the inputs that shaped the auth design in [03 Authorisation](03_AUTHORISATION.md); the platform landed on a simpler version of the same idea (one Lambda authoriser, group ceilings, dataset grants, RLS) because the broader complexity VAMS carries was not needed for vector-and-raster serving. The thinking carries over the other direction — if 3D and CAD become first-class here, VAMS's processing-pipeline and asset-versioning model is the closest reference for how the editing pipeline would extend.

> *In plain terms:* the platform already does for vector and raster what VAMS does for 3D and CAD. Either bolt VAMS into the auth gate as a sibling backend, or extend the platform's pipeline and viewer to cover visual assets directly — whichever is closer to the workloads in scope.

**Why it fits.** S3 + DynamoDB + Lambda + serverless pipelines is shared substrate. The editing pipeline (see [11 Editing Pipeline](11_EDITING_PIPELINE.md)) is structurally close to VAMS's asset-version-and-process model. The auth gate is the natural integration point for either path; the 3D rendering surface sketched in §4 is the natural client.

**Concrete tech to consider.** Deploy VAMS behind the existing auth gate via a new ALB listener rule (one new path prefix, no per-VAMS-route auth code), or extend the editing pipeline to accept 3D and CAD inputs and register them with a new `data_type` (`asset`) — reusing VAMS-equivalent viewer plugins on the client side. For asset transforms (CAD → glTF, point cloud → COPC, mesh decimation), AWS Batch is likely a better substrate than transient Fargate tasks because asset pipelines run longer and want more ephemeral storage than the current 200 GiB ceiling.

**What needs designing.** The integrate-vs-extend choice — different consequences for who owns the asset registry, who manages access, and whether visual assets share the dataset lifecycle (review, versioning, history) with vector and raster. Identity-passthrough between this platform's auth and VAMS's ABAC/RBAC if integrating. Storage of large binaries and their derivatives (cost shape diverges from Parquet-and-tile economics). Viewer surface — whether the existing map client (see [15 Map Client](15_MAP_CLIENT.md)) gains 3D plugins or a separate viewer ships alongside it.

## What is solid, what needs work

To borrow the framing from [10 Discovery](10_DISCOVERY.md):

**Solid.** None of it. Treat every section as a starting point.

**Designed but not built.** All twelve. Each section is well enough thought through to brief an architect; none has had code written against it as part of this platform's prototype.

**Where the work is heaviest.** The first three (semantic discovery, geocoding, point clouds) extend patterns and substrates the platform already uses — moderate effort, fits naturally. The middle three (3D, computer vision, agents) introduce new substrates with their own operational shapes. The last five (field capture, reports, subscriptions, change detection, live data) introduce new workflows with substantial product design work alongside the engineering. The twelfth (3D and visual asset management) shares this platform's substrate but introduces a different file ecosystem and the option of integrating a peer system (VAMS) rather than building from scratch — appended out of strict ease-of-fit order so the existing section numbering is preserved.

These are doors, not roads. A future team reading this set should treat each section as a starting point — enough to spark a design conversation, not enough to commit to a build without one.

## A note on dates

The ideas in this chapter were sketched alongside the rest of the corpus — see [Currency](00_INDEX.md#currency) on the document index. Several of them depend on AWS services and open-source projects that were themselves new at the time of writing: Bedrock AgentCore had only recently reached general availability; OpenSearch Serverless's geospatial story was still maturing; Aurora Serverless v2's scale-to-zero arrived mid-window; mermaid macro vendors in Confluence Cloud were in flux.

Cloud-service landscapes move on the order of months. By the time anyone picks up this set, several of the technology callouts here will have shifted — service names may change, pricing models may evolve, new substrates may emerge, and the gaps these sketches address may have closed (or new gaps opened in their place). **The shape of each sketch is more durable than the specific tech named within it.** Re-check the canonical sources in [20 Glossary and References](20_GLOSSARY_AND_REFERENCES.md) before committing to a build path, and treat the dating in each section as one factor among several when judging fit.

If you are reading this set well after it was compiled, the right next step is to look at what has changed in the underlying services since, rather than take any single technology recommendation at face value. The design choices in [16 Design Decisions](16_DESIGN_DECISIONS.md) — the *why* of each call — age more slowly than the *what*.
