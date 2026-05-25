# 19 — Business Requirements

This document lists what the platform does, expressed as outcomes a project or programme might be looking for. It is intended for teams considering whether the platform is a good fit for a project, programme, or replacement candidate — letting them check coverage of their needs before commissioning a new bespoke system.

It is not a roadmap, a contract, or a guarantee. It is a frank reading of what the platform delivers today, what is in adjacent reach, and what is deliberately not the platform's role.

## How to read the status column

| Status | Meaning |
|---|---|
| **Met** | The platform delivers this today, designed and exercised through the prototype. Each row points to where the design is specified. |
| **Partial** | Some of what's described is in place; some is not. Notes explain which is which. |
| **Planned** | Sketched as a future direction in [17 Further Directions](17_FURTHER_DIRECTIONS.md). Not built; the platform's foundations fit it and an approach has been outlined. |
| **Adjacent** | Not explicitly designed, but the platform can be extended to cover it without changing its overall shape. Usually the smallest delta for a future team to add. |
| **Out of scope** | Deliberately not part of the platform's role. The architecture is shaped against doing this, and pursuing it would mean a different platform. Notes explain why and what a better fit looks like. |

The platform's role is to **host, secure, serve, and edit spatial data** at organisation scale. Anything outside that — heavy analytics, transactional spatial writes, document management, bespoke field-collection apps — sits in *Adjacent*, *Planned*, or *Out of scope*.

---

## Functional requirements

### 1. Discovering data

| What you can do | Status | Notes |
|---|---|---|
| Browse every dataset the organisation has registered, in one place | Met | Single catalogue across vector, raster, routing, and reference data. See [10 Discovery](10_DISCOVERY.md). |
| See only the datasets you're allowed to see | Met | The catalogue filters per user; you never see metadata for data you can't access. |
| Read each dataset's description, owner, contact, extent, and last-updated date before requesting access | Met | Standard metadata captured at registration and visible on every dataset record. |
| See a dataset's field structure (which fields exist, what types) before opening it | Met | Field metadata is exposed alongside the dataset record; this is what desktop GIS tools and the built-in editor use to render forms. |
| Filter the catalogue by area, time, or known dataset identifier | Met | Standard catalogue search supports spatial extent, temporal extent, and collection or dataset id. |
| Find datasets using natural-language questions ("show me road networks near the western corridor") | Planned | Sketched in [17 Further Directions](17_FURTHER_DIRECTIONS.md) using embeddings and a small language model over catalogue records. |
| Discover datasets from outside catalogues (other agencies, partners) | Adjacent | The platform doesn't pull in remote catalogues today; a connector that harvests external catalogues into the local registry is a feasible extension. |
| See the lineage of a dataset (where it came from, what it depends on) | Partial | Lineage fields are captured per dataset; a graphical lineage view is not built. |
| See a preview of a dataset before opening it in a GIS tool | Met | The built-in web map client renders any registered dataset. See [15 Map Client](15_MAP_CLIENT.md). |
| See deprecation notices and migrate to the named successor before a dataset is retired | Met | Datasets carry an explicit lifecycle (active → deprecated → retired → archived); deprecation notices and successor links appear in catalogue listings. See [10 Discovery](10_DISCOVERY.md). |
| Get a clear "gone, here's the replacement" response when calling a retired dataset, instead of a generic error | Met | Retired datasets return an HTTP "Gone" response with the successor identifier, so client code can migrate deliberately rather than guess. |

### 2. Controlling who can see and change data

| What you can do | Status | Notes |
|---|---|---|
| Sign in with the organisation's existing identity provider (Entra ID, Okta, Google Workspace, etc.) | Met | The platform accepts logins from any standard corporate identity provider; users don't need a separate account. See [03 Authorisation](03_AUTHORISATION.md). |
| Issue long-lived access credentials for desktop GIS tools and scripts | Met | Each person (or shared service account) can hold one or more keys, scoped to their own access. |
| Grant access to a specific dataset to a specific person or team | Met | Per-dataset grants managed by dataset owners. |
| Restrict what each person sees *within* a dataset based on their group, region, or project | Met | Common patterns: regional teams see only their region; projects see only their records; contractors see only what they've been engaged on. |
| Let external partners or agencies each see only their own records in a single shared dataset | Met | A multi-tenant pattern — one shared dataset, many tenants, each tenant sees only their rows. The canonical example is a single asset register shared across regional councils. |
| Cap any contractor's or partner's permissions to what HR or the identity provider has agreed, regardless of internal grants | Met | The identity provider's group membership sets a ceiling that platform grants cannot exceed. |
| Issue a credential to a desktop GIS team that is read-only against a defined set of layers | Met | Group-scoped credentials inherit only the group's datasets at viewer access; useful for shared service accounts on shared workstations. |
| Make a dataset publicly available without sign-in | Met | Per-dataset opt-in; everything else stays behind authentication. |
| Let dataset owners manage their own access without involving a platform administrator | Met | Owners create groups, add members, and grant permissions on the datasets they own. |
| Invite a new user by email and have their account set itself up on first sign-in | Met | The invitation carries the group memberships; they're active the moment the user signs in. |
| Revoke a user's access | Met | Group removal or credential revocation takes effect within a few minutes everywhere. |
| See an audit trail of who accessed what and when | Partial | Every access decision is recorded centrally; reviewing it today uses standard log-query tooling — a dedicated audit-search screen isn't built. |
| Require multi-factor authentication for sensitive datasets | Adjacent | Configured at the identity provider, which already supports MFA; the platform inherits whatever the IdP enforces. |
| Provision and de-provision users automatically from the HR or central identity system | Adjacent | Today the workflow is invitation-based. Automatic provisioning would replace that and is a feasible extension. |
| Grant temporary elevated access ("break-glass") that expires automatically | Adjacent | Not built; today temporary access is a procedural process (grant, then revoke). |
| Limit how many requests a single user or credential can make per minute | Adjacent | Platform-wide protection is in place; per-user quotas are configurable but not exposed as a self-service feature. |

### 3. Loading and managing data

| What you can do | Status | Notes |
|---|---|---|
| Upload a new dataset from a file | Met | The platform validates, organises, prepares maps, and publishes — without manual intervention. See [11 Editing Pipeline](11_EDITING_PIPELINE.md). |
| Onboard datasets from common spatial file formats (GeoParquet, GeoJSON) | Met | Standard upload pathway; no conversion required first. |
| Onboard datasets from legacy spatial formats (Shapefile, GeoPackage, KML) | Adjacent | A small conversion step using standard tools turns these into a supported format. A managed conversion service is a feasible extension. |
| Register an existing imagery archive without copying it into the platform | Met | Reference-only datasets point at the existing storage location; no duplication. |
| Onboard aerial or satellite imagery as map layers | Met | The platform serves cloud-optimised imagery directly from storage; ingestion is registration only. See [08 Raster Services](08_RASTER_SERVICES.md). |
| Add new monthly or annual imagery captures incrementally to an existing archive | Met | Time-keyed mosaic descriptors let new captures land alongside older ones; older captures remain addressable by date. |
| Onboard elevation data | Met | Same path as imagery; elevation is served as a coverage. |
| Have the platform check uploads for format errors, missing fields, or invalid geometry | Met | Validation runs before any data is published; errors are reported back. |
| Have the platform enforce a dataset's schema (rejecting uploads that drift from it) | Met | Schema declared at registration; ingest enforces it. |
| Re-upload the same dataset without duplicating rows | Met | Idempotent ingestion; identical uploads produce no new rows. |
| Upload large datasets (multiple gigabytes) | Met | Multi-part upload supported; ingestion has ample working storage. |
| Recover gracefully from a failed upload | Met | Failure context is retained; partial artefacts are cleaned up; re-uploading resumes safely. |
| Ingest data from a live stream (Kafka, Kinesis) | Out of scope | The platform is built around published datasets and reviewed change, not live streams. A streaming layer that batches into the platform is the recommended pattern. |
| Make changes to data and have them go live instantly without review | Out of scope | The platform's value is in reviewed, auditable change. Live transactional writes belong in a different kind of system. |

### 4. Editing and reviewing changes

| What you can do | Status | Notes |
|---|---|---|
| Make changes to a dataset and submit them for review before they go live | Met | Edit sessions hold changes; nothing is published until reviewed. See [11 Editing Pipeline](11_EDITING_PIPELINE.md). |
| Edit features one at a time through a map interface | Met | Built-in web client supports feature-level edits. See [15 Map Client](15_MAP_CLIENT.md). |
| Make bulk changes (update many records at once) | Met | A bulk editing surface supports adding, modifying, or removing many records in a single session. |
| Let data managers fix data at scale (e.g. backfill a new mandatory field across millions of rows) through the same reviewed pipeline as any other edit | Met | Bulk operations are routed through validation and review, not run as out-of-band scripts. |
| Have the platform queue same-dataset edits so two editors don't corrupt each other's work | Met | Submissions to the same dataset are queued and run cleanly in order; genuine record-level conflicts are flagged at submission. |
| Define organisation-specific data quality rules and apply them automatically on every edit | Met | Per-dataset validation rules run on every edit; some block submission, others issue warnings to the reviewer. |
| See what's changed before approving (additions, modifications, deletions visualised on the map) | Met | Reviewers see a colour-coded delta against the current authoritative dataset. |
| Preview an editor's draft overlay on the live map before approving | Met | Draft tiles render alongside live tiles so reviewers can see the proposed change in context. |
| Be warned before applying a schema change that would invalidate existing rows | Met | The platform detects breaking schema changes and refuses to apply them unless explicitly forced, with guidance on the data fix needed first. |
| Approve and publish changes in a single action | Met | Once approved, changes go live; consumers see the new version on their next request. |
| Detect when two editors have changed the same record, and surface the conflict at submission rather than silently overwriting | Met | The second submission sees the conflict, the editor resubmits with the conflict resolved. No automatic merge tool. |
| Add new columns to an existing dataset | Met | Schema additions are supported. |
| Restructure a dataset's schema (rename columns, change data types) | Met | Supported via schema edits with breaking-change detection; the platform refuses dangerous changes unless the data is brought into line first. |
| Roll back to a previous version of a dataset | Met | Whole-dataset revert is supported as a reviewed edit. |
| Capture and edit data offline in the field, syncing later | Planned | Field-capture workflow is sketched in [17 Further Directions](17_FURTHER_DIRECTIONS.md). |

### 5. Tracking history and audit

| What you can do | Status | Notes |
|---|---|---|
| See who changed which record, when, and what the value was before and after | Met | Per-record history with attribution, retained for the life of the dataset. See [11 Editing Pipeline](11_EDITING_PIPELINE.md). |
| Get a clear record of every edit session: who submitted it, who reviewed it, when it went live | Met | Submitter, reviewer, timestamps, and a payload summary are recorded per session; the dataset event log holds the durable record. |
| Require that the person approving a change is not the person who made it (four-eyes) | Met | Submitter and reviewer are recorded distinctly and constrained to be different. |
| View a dataset as it was on any past date | Met | Time-travel queries return the dataset as of any historical timestamp. |
| Compare two versions of a dataset side by side | Partial | The reviewer flow compares an in-progress edit against the live version using the same overlay rendering; one-click comparison of any two arbitrary historical versions is not exposed as a feature. |
| Revert an individual change without reverting everything since | Adjacent | The history primitives support this — a cherry-pick is a small edit submitted against an earlier row version — but it is not exposed as a one-click revert in the built-in client. |
| Get a cryptographic guarantee that a historical record hasn't been altered | Out of scope | Not the platform's role. If required, the assertion layer sits above the catalogue (e.g. a separate notarisation service). |

### 6. Serving data to users and applications

| What you can do | Status | Notes |
|---|---|---|
| Show data on interactive web maps to many users at once | Met | Map tiles served from a global edge network; fast and predictable under any load. See [05 Vector Tiles](05_VECTOR_TILES.md). |
| Show satellite or aerial imagery on the same maps | Met | Raster tiles served the same way. See [08 Raster Services](08_RASTER_SERVICES.md). |
| Show how a layer has changed over time (time slider) | Met | Time-enabled raster services support this directly. |
| Make individual records available to applications (one at a time, or in filtered queries) | Met | Standard feature-query interface; filter by area, attribute, or both. See [06 OGC Features API](06_OGC_FEATURES_API.md). |
| Make elevation, sea-surface, or other continuous data available to scientific applications | Met | Standard coverages interface; clients pull the data they need for the region and time of interest. |
| Get the same fast response anywhere in the world (global edge caching is part of standard delivery) | Met | The edge layer absorbs repeat requests close to the user. |
| Embed maps in third-party applications and dashboards | Met | Standard interfaces work in any web framework or BI tool that accepts a standard map tile URL. |
| Push notifications to clients when data changes (server-sent) | Out of scope | The architecture is request/response. Clients poll a cheap "last-changed" check; long-lived push connections aren't supported by design. |

### 7. Spatial analysis and routing

| What you can do | Status | Notes |
|---|---|---|
| Find features in an area (e.g. all assets within a polygon) | Met | Spatial query interface returns matching features. See [07 Query Layer](07_QUERY_LAYER.md). |
| Find features near a point, with distance ranking | Met | Nearest-neighbour queries supported. |
| Count or summarise features within an area | Met | Aggregation queries supported. |
| Combine data from two or more datasets in a single query | Partial | Joins across moderate-sized datasets are supported. Very large analytical joins belong in a lakehouse alongside the platform. See [18 Lakehouse Integration](18_LAKEHOUSE_INTEGRATION.md). |
| Calculate driving, cycling, or walking routes between points | Met | Routing service with multiple travel modes. See [09 Routing](09_ROUTING.md). |
| Calculate drive-time catchment areas (isochrones) | Met | Standard isochrone outputs. |
| Calculate travel time / distance matrices between many origins and destinations in a single call | Met | Matrix operation exposed via the routing service. |
| Match recorded GPS traces back to the road network | Met | Map-matching service. |
| Chain several spatial operations in one request (e.g. drive-time → intersect with parcels → save the result) | Partial | Composition primitives exist in the design; the prototype is honest that this is "designed but under-tested" at this stage. |
| Save the output of a spatial analysis as a new layer that colleagues can render | Partial | A save primitive exists in the prototype; hardening it to go through the standard review pipeline is on the to-do list. |
| Route public transport trips | Adjacent | The routing service is profile-based; the public-transport engine (OpenTripPlanner) can be added alongside or instead of the driving engine. |
| Route with live traffic | Adjacent | The traffic data feed would be the addition; the engine supports time-of-day costing. |
| Convert an address to a coordinate (geocoding) | Planned | Sketched in [17 Further Directions](17_FURTHER_DIRECTIONS.md). |
| Power a BI dashboard with ad-hoc SQL queries against spatial data | Out of scope | The platform is built for serving, not for analytics workloads. A lakehouse is the right tool; [18 Lakehouse Integration](18_LAKEHOUSE_INTEGRATION.md) describes how they coexist. |

### 8. Connecting to existing tools

| What you can do | Status | Notes |
|---|---|---|
| Open datasets in QGIS | Met | Standard map and feature interfaces; QGIS connects with an access credential. See [14 Client Integration](14_CLIENT_INTEGRATION.md). |
| Open datasets in ArcGIS Pro and ArcGIS Online | Met | Same standard interfaces; ArcGIS connects via its built-in adapters. |
| Connect to ArcGIS Enterprise Portal as a registered vector tile service | Met | A dedicated adapter exposes the platform's vector layers in the shape ArcGIS Enterprise expects. |
| Use the data from any standards-compliant mapping or GIS tool | Met | The platform speaks the standard interfaces those tools expect. |
| Query the data from Python, R, or JavaScript scripts | Met | Standard HTTP access with a credential; widely-used spatial libraries work directly. |
| Read the data directly from object storage with analytics tools (DuckDB, BigQuery, Athena, Spark) | Met | The on-disk layout is designed for direct read by any modern analytical engine, with permissions enforced at the storage layer. |
| Use the built-in web map client to browse, edit, and review | Met | First-party React + MapLibre client. See [15 Map Client](15_MAP_CLIENT.md). |
| Explore the data programmatically with an interactive query tool | Met | Built-in GraphiQL surface, scoped to the user's permissions. |
| Use the data on mobile devices | Adjacent | Standard HTTP clients work; no platform-supplied mobile SDK or app. |
| Export data to common file formats (Shapefile, GeoPackage, KML) | Adjacent | Achievable today using standard conversion tools on the client side; a server-side export is a small addition. |

### 9. Reporting and exports

| What you can do | Status | Notes |
|---|---|---|
| Export a dataset as a file for downstream use | Partial | Downloads of the platform's native formats work today; conversions to other formats are a client-side step. |
| Take a snapshot of a map as a static image | Adjacent | Achievable by composing tiles client-side; no server-side image export. |
| Generate a PDF report with maps and tables embedded | Planned | Sketched in [17 Further Directions](17_FURTHER_DIRECTIONS.md). |
| Schedule report generation on a recurring basis | Planned | Same sketch. |
| Produce print-quality cartographic layouts | Out of scope | Cartographic layout belongs in QGIS or a layout-product. The platform supplies the data; the layout tool composes the page. |

### 10. Notifications and live updates

| What you can do | Status | Notes |
|---|---|---|
| Get notified when a dataset you care about changes | Planned | Sketched in [17 Further Directions](17_FURTHER_DIRECTIONS.md). |
| Send change events to other systems (webhooks) | Planned | Same sketch. |
| Receive email alerts for dataset events | Planned | Same sketch. |
| Power a real-time vehicle or sensor display | Planned | Polling pattern over fast-refreshing map tiles is the recommended approach; live feeds are sketched in [17 Further Directions](17_FURTHER_DIRECTIONS.md). |
| Push updates to clients with sub-second latency | Out of scope | The platform is cache-friendly and request/response. Sub-second live data needs a streaming layer alongside, not inside, this platform. |
| Send SMS or push notifications | Out of scope | Notification delivery channels are a generic concern; the platform should emit events, not own every delivery channel. |

### 11. Field and mobile work

| What you can do | Status | Notes |
|---|---|---|
| Collect data on a mobile device in the field | Planned | Sketched in [17 Further Directions](17_FURTHER_DIRECTIONS.md). |
| Continue working offline and sync when connectivity returns | Planned | Same sketch. |
| Attach photos to features captured in the field | Planned | Same sketch; attachments addressable by feature. |
| Generate a form for data entry based on a dataset's schema | Adjacent | The schema is available; rendering a form is a client concern. Standard form-builder integrations are achievable. |

### 12. Detecting change and using intelligence

| What you can do | Status | Notes |
|---|---|---|
| Detect changes between two dates of imagery | Planned | Sketched in [17 Further Directions](17_FURTHER_DIRECTIONS.md). |
| Get alerted when a specific feature changes (e.g. a road I'm responsible for) | Adjacent | A combination of change subscriptions and the history system would deliver this; not built end to end. |
| Extract features from imagery using computer vision | Planned | Substantial pipeline; sketched in [17 Further Directions](17_FURTHER_DIRECTIONS.md). |
| Ask an AI assistant questions about the data ("which datasets cover this area?") | Planned | Aspirational postscript in [10 Discovery](10_DISCOVERY.md). |

### 13. Working with 3D and visual assets

| What you can do | Status | Notes |
|---|---|---|
| Serve 3D city or terrain models to standard 3D viewers (Cesium, TerriaJS) | Adjacent | The platform's storage and authorisation pattern accept standard 3D tile formats; a first-party serving and viewer integration is not built. The integration is sketched in [17 Further Directions](17_FURTHER_DIRECTIONS.md). |
| Manage and serve large visual assets (photos, models, scans) alongside spatial data | Planned | Sketched in [17 Further Directions](17_FURTHER_DIRECTIONS.md), drawing on the AWS Visual Asset Management System pattern. |
| Serve point cloud data (LiDAR) to 3D viewers | Planned | The platform's substrate supports point-cloud-on-storage; the serving and viewer integration is sketched in [17 Further Directions](17_FURTHER_DIRECTIONS.md). |

---

## Non-functional requirements

### 14. Cost

| What you get | Status | Notes |
|---|---|---|
| Pay for what you use, not for idle capacity | Met | Costs scale with traffic. Lambda-backed services charge per invocation and cost nothing when idle; container-backed services in `minimal` mode keep one warm task at a few dollars per month each. See [12 Deployment](12_DEPLOYMENT.md). |
| Predictable cost as adoption grows | Met | Per-request pricing; no per-seat licensing. |
| Low cost when traffic is low (out-of-hours, weekends, project gaps) | Met | Idle deployments pay for storage and registry minimums plus a small per-service warm-task allowance — typically single-digit dollars per month for a development environment. |
| Lower ongoing cost than a heavy database-backed GIS stack | Met | The platform's design specifically targets this; the cost case is summarised in [content/index.md](index.md#the-economic-case) and supported by the comparisons in [18 Lakehouse Integration](18_LAKEHOUSE_INTEGRATION.md). |
| Avoid paying for fixed cloud-network bridges that idle most of the day | Met | The platform routes internal traffic via private endpoints rather than paid network gateways; this avoids a real per-zone monthly line item. |
| Cost transparency per project, team, or tenant | Partial | Cost can be tagged and attributed using standard cloud cost tooling; a built-in per-tenant cost view is not provided. |
| Budget ceilings with automatic alerts | Adjacent | Standard cloud budget tooling provides this outside the platform. |

### 15. Scale and performance

| What you get | Status | Notes |
|---|---|---|
| Map tiles served quickly to users anywhere in the world | Met | Edge-cached globally; typical responses in the tens of milliseconds. |
| Fast feature queries against datasets up to hundreds of millions of records for typical area-bounded workloads | Met | Spatial filtering is pushed down to storage; queries return in sub-second time for typical workloads. |
| Absorb unpredictable traffic spikes without pre-provisioning capacity | Met | Stateless services plus an edge cache absorb sudden load; this is one of the platform's defensible advantages over warm-pool architectures. |
| Concurrent users limited only by what you choose to pay for | Met | The serving layer has no fixed user ceiling; it scales with traffic. |
| Wake services on demand after idle periods | Partial | Scale-to-zero is supported; the first request to a fully-idle interactive service may wait 60–120 seconds for warm-up. Production deployments typically keep a minimum capacity rather than fully idle for interactive services. |
| Many thousands of datasets per platform deployment | Met | Registry sized for organisation scale. |
| Single platform deployment supports an entire organisation | Met | Multi-team, multi-tenant by design. |
| Geographic redundancy across regions | Adjacent | Single-region by default. Multi-region is achievable but requires deliberate configuration. |

### 16. Reliability and recovery

| What you get | Status | Notes |
|---|---|---|
| Services stay available through normal infrastructure failures | Met | Multi-zone deployment within a region; stateless services recover automatically. |
| Documented recovery plan for major incidents | Met | See [13 Operations](13_OPERATIONS.md). |
| Data recovery to within minutes of any failure | Met | Storage versioning and point-in-time recovery on registry data. |
| Recover from accidental file overwrite using storage-level versioning | Met | Prior versions of any stored object are recoverable. |
| Restore the platform's metadata (registry, permissions) to any point in the last 35 days | Met | Continuous backup on the metadata store with point-in-time recovery. |
| Recover from accidental deletion of a dataset | Met | Soft-delete with retention; restoration is a recorded operation. |
| Tested disaster-recovery process | Partial | Plan is documented; production exercise is a deployment concern, not a platform-supplied test. |
| Cross-region disaster recovery | Adjacent | Single-region by default; cross-region failover requires configuration work and is not built. |

### 17. Security

| What you get | Status | Notes |
|---|---|---|
| All traffic encrypted end to end | Met | Standard practice across every component. |
| Data encrypted at rest | Met | Storage encryption with customer-managed keys supported. |
| No backend services reachable from the public internet | Met | One controlled public entry point; everything else is private. |
| Least-privilege internal access between components | Met | Per-service permissions documented. |
| Access credentials stored safely (never in plain text) | Met | Hashed and managed via the cloud secret store. |
| Cap the damage of a leaked credential to the scope it was issued for | Met | Credentials issued to a person drop to public-only by default; credentials issued to a group inherit only that group's permissions at viewer level. A leaked credential can never exercise more than what it was issued for. |
| Independent security review and penetration testing | Out of scope | The platform's architecture is shaped to be testable (small attack surface, single ingress); the test itself is the deploying team's operational responsibility. |
| Software bill of materials and supply-chain scanning | Adjacent | Standard container scanning is in place; a published bill of materials is a deployment concern. |

### 18. Compliance and data governance

| What you get | Status | Notes |
|---|---|---|
| Data stays in a configurable single region | Met | Region is a deployment parameter; data does not cross regions. |
| Audit trail of access and changes for sensitive data | Partial | Per-record history plus access logs are captured; reviewing them today uses standard query tools rather than a dedicated UI. |
| Wind down a dataset through visible lifecycle states (active → deprecated → retired → archived) rather than silent deletion | Met | Each transition is observable, audited, and reversible up to the archive step. See [10 Discovery](10_DISCOVERY.md). |
| Configurable retention for logs and historical records | Met | Standard retention controls. |
| Apply different retention to live data versus historical change records | Met | Per-dataset history retention is configurable; lifecycle rules differ per data class. |
| Classify datasets (e.g. public, internal, restricted) | Adjacent | Tagging is available; a structured classification taxonomy is the deploying organisation's choice. |
| Respond to data subject access requests (GDPR-style) | Adjacent | The platform supports the underlying queries; a self-service request portal is not built. |
| Hard-delete records on request (right to be forgotten) | Adjacent | Hard delete is supported; a request-driven automated workflow is not built. |
| Certified for regulated industries (HIPAA, PCI-DSS) | Out of scope | The platform's architecture admits regulated deployment but does not itself ship with certification. The deploying organisation operates within their own accreditation. |

### 19. Operability

| What you get | Status | Notes |
|---|---|---|
| Centralised monitoring of platform health | Met | Dashboards per service group documented in [13 Operations](13_OPERATIONS.md). |
| Alarms for common failure modes | Met | Standard alarms documented; integration with on-call tooling is a deployment detail. |
| Runbooks for common operational incidents | Met | See [13 Operations](13_OPERATIONS.md). |
| Trace each edit through its workflow execution for audit and troubleshooting | Met | Each edit produces a visual workflow execution that can be inspected end to end. |
| Cancel an in-flight edit job and free the dataset for the next one | Met | A cancel operation transitions the job and releases the per-dataset queue. |
| Predictable deployment process (blue/green, rolling updates) | Met | Standard cloud deployment patterns used throughout. |
| Configuration captured as code | Met | The recommended pattern; the design is implementation-independent. |
| Capacity guidance for sizing decisions | Met | See [12 Deployment](12_DEPLOYMENT.md). |

### 20. Standards your tools and partners can rely on

| What you get | Status | Notes |
|---|---|---|
| Standard map tile services (WMTS, WMS) so QGIS, ArcGIS, and any standards-compliant mapping client can read maps | Met | |
| Standard feature services (OGC API Features) so applications can query individual records | Met | |
| Standard coverage services (OGC API Coverages) so scientific applications can read elevation and continuous-field data | Met | |
| Standard catalogue (STAC) so other systems can browse what's available | Met | |
| Common cloud-native data formats (GeoParquet, Cloud-Optimised GeoTIFF) so downstream tools and other clouds can read the data directly | Met | |

### 21. Vendor independence

| What you get | Status | Notes |
|---|---|---|
| Open data formats throughout — no proprietary lock-in | Met | Every format the platform stores is open and standards-based. |
| Open-source engines for the spatial work — no licensed software required | Met | All processing engines are open-source. |
| Standard interfaces — no platform-specific client libraries required | Met | Any standards-compliant tool works. |
| Data is exportable at any time | Met | The same interfaces clients read from work as export endpoints. |
| Portable to another cloud provider if needed | Partial | The data formats and engines are portable; the cloud-specific networking and identity layers would need redesigning. The corpus is structured around this kind of substitution. See [12 Deployment](12_DEPLOYMENT.md). |
| Individual components substitutable without rebuilding the platform | Met | Each component is documented behind a contract; alternative engines can be swapped in. The platform has done this in earnest (tile server replacement, catalogue replacement). |

### 22. Interoperating with an existing data platform (lakehouse, warehouse)

| What you get | Status | Notes |
|---|---|---|
| Let an analytics platform (Databricks, Snowflake, BigQuery) read the platform's spatial data as an external table, without copying it | Met | The on-disk format and partition layout are directly readable by any modern analytical engine. See [18 Lakehouse Integration](18_LAKEHOUSE_INTEGRATION.md). |
| Ingest spatial data that was prepared, enriched, or modelled in the lakehouse, then distribute it widely through the platform | Met | The documented "lakehouse-as-source" pattern uses the analytics platform for heavy preparation and this platform for wide-scale serving. |
| Avoid duplicating spatial governance between the lakehouse and the serving layer | Partial | Both systems can federate to the same identity provider and share the same storage; row-by-row permission passthrough between the two governance surfaces is not designed today. |
| Replace the analytics platform's serving layer with this platform | Met | The platform's purpose is wide-scale serving and lightweight querying; analytical engines that are good at preparation are typically poor at high-concurrency tile and feature serving. |
| Replace this platform's analytical query layer with the analytics platform | Met | For workloads that exceed what this platform's query layer is designed for, the lakehouse is the right home; the platform's catalogue points consumers at the right surface. |

---

## Reading by intent

If you are evaluating against a specific need:

- **"Do we still need our existing map server?"** — Read §6 Serving data, §20 Standards. Most map-server use cases are *Met*.
- **"Can we run our editing workflow on this?"** — Read §4 Editing, §5 History.
- **"Can we replace our access-control patchwork?"** — Read §2 Controlling access.
- **"Will this work for a BI or analytics workload?"** — Read §7 Analysis, then §22 Interoperating with an existing data platform, then [18 Lakehouse Integration](18_LAKEHOUSE_INTEGRATION.md). The honest answer is "use a lakehouse alongside, not instead."
- **"We already have a lakehouse — what does this add?"** — Read §22 Interoperating with an existing data platform and [18 Lakehouse Integration](18_LAKEHOUSE_INTEGRATION.md).
- **"Will it scale to our user base?"** — Read §14 Cost, §15 Scale, §16 Reliability.
- **"Is it compliant with our security posture?"** — Read §17 Security, §18 Compliance.
- **"Can we run this in our preferred cloud?"** — Read §21 Vendor independence and the cross-cloud notes in [12 Deployment](12_DEPLOYMENT.md).

## When this document is wrong

This is a snapshot. If you find a requirement marked *Met* that the platform can't actually deliver, that is a documentation bug — log it, and the relevant chapter should be amended. If you find something marked *Adjacent* or *Planned* that you actually need, that is useful evaluation signal: either the platform needs that work commissioned, or another platform is a better fit for your project.

The point of this document is to make the fit conversation short and concrete, not to dress the platform in capabilities it does not have.

---

**Read next:** [20 Glossary and References](20_GLOSSARY_AND_REFERENCES.md) — every term, format, service, standard, library, and peer geospatial stack named across the documentation, with canonical URLs.
