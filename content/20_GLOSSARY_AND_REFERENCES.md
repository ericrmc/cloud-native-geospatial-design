# 20 — Glossary and References

A reference index for everything named in this corpus — formats, services, standards, libraries, concepts, and the peer geospatial stacks worth being aware of. Each entry gives a one-line description and a canonical URL.

> *In plain terms:* the lookup you reach for when a previous chapter mentions a thing and you want the official documentation. Quartz's backlinks panel shows you where each term is used; this page tells you where to learn more.

Categories:

1. Cloud-native data formats
2. Data engines and processing tools
3. AWS services
4. OGC and related standards
5. Identity, auth, and security
6. Map clients, libraries, and frontend tools
7. Spatial and data concepts
8. Peer geospatial stacks
9. Infrastructure-as-code
10. Other references

Within each category, entries are alphabetical. Where a canonical URL does not exist (concepts rather than products), the closest authoritative reference is given.

---

## 1. Cloud-native data formats

- **[Cloud Optimised Point Cloud (COPC)](https://copc.io/)** — LAZ point cloud reorganised as a clustered octree with a header-resident index, readable by HTTP byte range.
- **[Cloud-Optimized GeoTIFF (COG)](https://www.cogeo.org/)** — tiled, overview-bearing GeoTIFF designed for partial HTTP range reads from object storage.
- **[FlatGeobuf](https://flatgeobuf.org/)** — binary streamable vector format used as an efficient intermediate before tile generation.
- **[GeoJSON (RFC 7946)](https://datatracker.ietf.org/doc/html/rfc7946)** — JSON encoding for geographic feature data.
- **[GeoParquet](https://geoparquet.org/)** — Apache Parquet with a standardised geometry encoding, enabling predicate-pushdown spatial reads from object storage.
- **[Mapbox Vector Tile (MVT)](https://github.com/mapbox/vector-tile-spec)** — protobuf-encoded vector tile format used inside PMTiles archives.
- **[MosaicJSON](https://github.com/developmentseed/mosaicjson-spec)** — descriptor format for virtual mosaics over many COGs, quadkey-indexed.
- **[PMTiles](https://github.com/protomaps/PMTiles)** — single-file archive of map tiles indexed for HTTP range reads from object storage.
- **[Zarr](https://zarr.dev/)** — chunked, compressed, n-dimensional array storage format for multidimensional scientific raster.

## 2. Data engines and processing tools

- **[cogeo-mosaic](https://github.com/developmentseed/cogeo-mosaic)** — Python library for building quadkey-indexed MosaicJSON descriptors from COG collections.
- **[DuckDB](https://duckdb.org/)** — in-process analytical SQL engine that reads Parquet and GeoParquet directly with predicate pushdown.
- **[DuckDB httpfs extension](https://duckdb.org/docs/stable/core_extensions/httpfs/overview.html)** — DuckDB extension enabling reads from HTTP and S3 URLs.
- **[DuckDB spatial extension](https://duckdb.org/docs/stable/core_extensions/spatial/overview.html)** — DuckDB extension providing geometry types and ST_* spatial functions.
- **[Entwine](https://entwine.io/)** — toolkit for organising large point clouds into octree structures for streaming.
- **[FastAPI](https://fastapi.tiangolo.com/)** — Python async web framework used by TiTiler and suggested for the CV inference proxy.
- **[GDAL](https://gdal.org/)** — Geospatial Data Abstraction Library; the universal raster and vector translation and processing library.
- **[gdalbuildvrt](https://gdal.org/programs/gdalbuildvrt.html)** — GDAL utility that builds a virtual raster mosaic over multiple source files.
- **[gdal_translate](https://gdal.org/programs/gdal_translate.html)** — GDAL utility for raster format conversion, including the COG driver.
- **[go-pmtiles](https://github.com/protomaps/go-pmtiles)** — Go-based PMTiles HTTP server with S3 byte-range reads and ETag-driven cache invalidation.
- **[PDAL](https://pdal.io/)** — Point Data Abstraction Library for filtering, transforming, and converting LiDAR data.
- **[rasterio](https://rasterio.readthedocs.io/)** — Python bindings over GDAL for reading and writing geospatial raster.
- **[Samgeo](https://samgeo.gishub.org/)** — geospatial wrapper for Meta's Segment Anything Model that returns georeferenced GeoJSON detections.
- **[Segment Anything Model (SAM)](https://segment-anything.com/)** — Meta's foundation model for promptable image segmentation.
- **[Tippecanoe (Felt fork)](https://github.com/felt/tippecanoe)** — vector tile generator producing PMTiles/MBTiles with geometry-aware simplification.
- **[TiTiler](https://developmentseed.org/titiler/)** — FastAPI dynamic tile server for COGs and MosaicJSON built on rasterio.
- **[Valhalla](https://valhalla.github.io/valhalla/)** — open-source routing engine using OSM tile hierarchies; supports route, isochrone, map-match.

## 3. AWS services

- **[Amazon API Gateway HTTP API](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html)** — lightweight managed HTTP gateway supporting custom Lambda authorisers and VPC Link integrations.
- **[Amazon Application Load Balancer (ALB v2)](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html)** — Layer-7 load balancer with path-based listener rules, URL rewrite transforms, and IP/Lambda target groups.
- **[Amazon Bedrock](https://aws.amazon.com/bedrock/)** — managed service for accessing foundation models from multiple providers via a single API.
- **[Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/)** — Bedrock runtime for building multi-agent systems with session memory, tool use, and identity passthrough.
- **[Amazon Bedrock Knowledge Base](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)** — managed RAG service over a vector store, exposing retrieval as a Bedrock API.
- **[Amazon CloudFront](https://docs.aws.amazon.com/cloudfront/)** — AWS content delivery network with per-behaviour cache policies and credential-header keying.
- **[Amazon CloudWatch](https://docs.aws.amazon.com/cloudwatch/)** — AWS metrics, logs, and alarms service for operational observability.
- **[Amazon CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html)** — query language and engine for ad-hoc analysis of CloudWatch log groups.
- **[Amazon Cognito User Pool](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools.html)** — AWS-managed OIDC identity provider with hosted UI and federation support.
- **[Amazon Cognito post-authentication Lambda trigger](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-post-authentication.html)** — Cognito hook invoked after successful sign-in, used here to convert invitations into platform memberships.
- **[Amazon DynamoDB](https://docs.aws.amazon.com/dynamodb/)** — AWS-managed key-value/document store with single-table design support, GSIs, conditional writes, and PITR.
- **[Amazon DynamoDB Global Secondary Index (GSI)](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GSI.html)** — alternate index over a DynamoDB table enabling inverse-direction or attribute-keyed queries.
- **[Amazon DynamoDB Point-In-Time Recovery (PITR)](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/PointInTimeRecovery.html)** — continuous DynamoDB backup with per-second restore points over the prior 35 days.
- **[Amazon DynamoDB TTL](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html)** — per-item time-to-live attribute that triggers asynchronous deletion when expired.
- **[Amazon ECS Exec](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-exec.html)** — mechanism to open an interactive shell into a running ECS task without SSH.
- **[Amazon ECS Service Auto Scaling](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-auto-scaling.html)** — auto-scaling for ECS services driven by CloudWatch metrics.
- **[Amazon ElastiCache](https://docs.aws.amazon.com/elasticache/)** — managed in-memory cache service (Redis or Memcached engines).
- **[Amazon EventBridge](https://docs.aws.amazon.com/eventbridge/)** — AWS event bus and scheduler for inter-service events and cron-based Lambda invocations.
- **[Amazon OpenSearch Serverless](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless.html)** — on-demand OpenSearch with `geo_point` and `geo_shape` support for spatial and full-text queries.
- **[Amazon S3](https://docs.aws.amazon.com/s3/)** — AWS object storage with byte-range reads, versioning, lifecycle policies, and atomic CopyObject.
- **[Amazon S3 CopyObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CopyObject.html)** — atomic server-side object copy used here for live/staging swap of PMTiles archives.
- **[Amazon S3 Glacier Deep Archive](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html#sc-glacier)** — lowest-cost S3 storage class with multi-hour retrieval time, used for long-term archive.
- **[Amazon S3 Intelligent-Tiering](https://docs.aws.amazon.com/AmazonS3/latest/userguide/intelligent-tiering.html)** — S3 storage class that auto-moves objects between access tiers based on usage.
- **[Amazon S3 Lifecycle policy](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)** — prefix-scoped rules that transition or expire S3 objects on a schedule.
- **[Amazon S3 Storage Lens](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage_lens.html)** — organisation-wide S3 storage analytics dashboard.
- **[Amazon S3 Versioning](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html)** — bucket-level setting that keeps non-current object versions for recovery.
- **[Amazon SageMaker Async Inference](https://docs.aws.amazon.com/sagemaker/latest/dg/async-inference.html)** — SageMaker endpoint mode supporting long-running queued GPU inference requests.
- **[Amazon SES](https://docs.aws.amazon.com/ses/)** — managed email-sending service for notifications.
- **[Amazon SNS](https://docs.aws.amazon.com/sns/)** — pub/sub messaging service supporting email, SMS, and HTTP delivery.
- **[Amazon SQS](https://docs.aws.amazon.com/sqs/)** — managed message queue used here to bridge S3 events into Step Functions, including dead-letter queues.
- **[Amazon VPC Gateway Endpoints (S3, DynamoDB)](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html)** — private route-table entries that allow VPC traffic to reach S3 and DynamoDB without an internet path.
- **[AWS Batch](https://docs.aws.amazon.com/batch/)** — managed batch-job scheduler over ECS, Fargate, or EC2.
- **[AWS Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)** — serverless container runtime for ECS tasks and services with per-task ephemeral storage up to 200 GiB.
- **[AWS IAM](https://docs.aws.amazon.com/iam/)** — Identity and Access Management; policy-based access control for AWS resources.
- **[AWS Lambda](https://docs.aws.amazon.com/lambda/)** — serverless function runtime billed per invocation.
- **[AWS Step Functions](https://docs.aws.amazon.com/step-functions/)** — managed workflow engine with state machines defined in Amazon States Language and visual execution history.
- **[VPC Link for HTTP API](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-vpc-link.html)** — private connectivity layer between API Gateway HTTP API and VPC resources (such as an internal ALB).

## 4. OGC and related standards

- **[3D Tiles](https://www.ogc.org/standard/3dtiles/)** — OGC Community Standard for streaming 3D content (textured meshes, photogrammetry, point clouds, 3D models). Natively consumed by CesiumJS and TerriaJS; the sibling streaming format to PMTiles and COG for the 3D-asset class — see [17 Further Directions §12](17_FURTHER_DIRECTIONS.md#12-3d-and-visual-asset-management--vams-style-extension).
- **[CQL2](https://docs.ogc.org/is/21-065r2/21-065r2.html)** — OGC Common Query Language v2, text/JSON filter syntax for OGC API endpoints.
- **[CRS84 and EPSG codes](https://epsg.io/)** — coordinate reference system identifiers; CRS84 is the OGC alias for WGS84 lon/lat, EPSG codes index all CRSes.
- **[CZML](https://github.com/AnalyticalGraphicsInc/czml-writer/wiki/CZML-Structure)** — JSON streaming format for time-dynamic 3D scene data, native to CesiumJS.
- **[GTFS Realtime](https://gtfs.org/realtime/)** — protobuf-based feed format for live public-transit vehicle positions and alerts.
- **[OGC API - Coverages](https://ogcapi.ogc.org/coverages/)** — OGC standard for programmatic access to coverage (raster) data subsets.
- **[OGC API - Features](https://ogcapi.ogc.org/features/)** — OGC standard for HTTP/JSON access to feature collections.
- **[OGC WMS 1.3.0](https://www.ogc.org/standard/wms/)** — Web Map Service; XML+image protocol for rendered map images, the legacy desktop-GIS standard.
- **[OGC WMTS 1.0.0](https://www.ogc.org/standard/wmts/)** — Web Map Tile Service; capabilities-driven tile delivery protocol consumed by QGIS and ArcGIS.
- **[STAC 1.0.0 (SpatioTemporal Asset Catalog)](https://stacspec.org/)** — JSON schema and API for cataloguing geospatial assets.
- **[STAC pointcloud extension](https://github.com/stac-extensions/pointcloud)** — STAC extension describing point-cloud assets such as COPC files.
- **[TileJSON](https://github.com/mapbox/tilejson-spec)** — JSON descriptor for tile endpoints; URL template, bounds, zoom, attribution.

## 5. Identity, auth, and security

- **[JSON Web Key Set (JWKS) (RFC 7517)](https://datatracker.ietf.org/doc/html/rfc7517)** — JSON document publishing an issuer's signing keys, used to verify JWT signatures.
- **[JSON Web Token (JWT) (RFC 7519)](https://datatracker.ietf.org/doc/html/rfc7519)** — signed/encrypted token format used for OIDC bearer credentials.
- **[Microsoft Entra ID](https://learn.microsoft.com/entra/identity/)** — Microsoft's enterprise identity service (formerly Azure AD), an OIDC provider option.
- **[OpenID Connect (OIDC)](https://openid.net/developers/specs/)** — identity layer over OAuth 2.0 producing signed JWT ID tokens.
- **[OpenID Connect Discovery](https://openid.net/specs/openid-connect-discovery-1_0.html)** — standardised endpoint for discovering an OIDC provider's metadata; the basis for the trusted-issuers configuration.
- **Row-level security (RLS)** — per-row access filtering applied transparently based on the requester's identity or claims. Closest canonical reference: [PostgreSQL Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html).
- **[RS256 / RS384 / RS512 (RFC 7518)](https://datatracker.ietf.org/doc/html/rfc7518)** — RSA SHA JWT signing algorithms accepted for token signature verification.
- **[SHA-256 (NIST FIPS 180-4)](https://csrc.nist.gov/publications/detail/fips/180/4/final)** — cryptographic hash used here to store API key fingerprints at rest.

## 6. Map clients, libraries, and frontend tools

- **[amazon-cognito-identity-js](https://github.com/aws-amplify/amplify-js/tree/main/packages/amazon-cognito-identity-js)** — JavaScript SDK for Cognito User Pool authentication flows.
- **[CesiumJS](https://cesium.com/platform/cesiumjs/)** — WebGL 3D globe and map engine supporting COPC, terrain, and CZML.
- **[deck.gl](https://deck.gl/)** — WebGL2 layer framework for large-scale data visualisation, commonly paired with MapLibre. Evaluated for the first-party map client; MapLibre alone covered the platform's needs without deck.gl's additional surface area.
- **[Esri VectorTileServer REST](https://developers.arcgis.com/rest/services-reference/enterprise/vector-tile-service/)** — Esri's proprietary REST contract for vector tile services consumed by ArcGIS Enterprise.
- **[Form.io](https://form.io/)** — offline-capable form runtime and builder, suggested for field-data capture.
- **[GraphiQL](https://github.com/graphql/graphiql)** — in-browser IDE for interactive GraphQL query construction with schema introspection.
- **[Kepler.gl](https://kepler.gl/)** — Open-source large-scale geospatial data visualisation tool built on deck.gl. Evaluated alongside deck.gl; same reasoning — additional capability the platform's map client did not require.
- **[MapLibre GL JS](https://maplibre.org/)** — open-source WebGL renderer for vector and raster maps, fork of Mapbox GL JS v1.
- **[MapLibre Style Spec](https://maplibre.org/maplibre-style-spec/)** — JSON specification for declarative styling of vector and raster maps.
- **[Potree](https://github.com/potree/potree)** — Web-based point cloud viewer; common pair with COPC. Evaluated alongside CesiumJS for any 3D direction; CesiumJS was preferred for breadth (handles point cloud, mesh, terrain, and imagery in one engine) given the platform's focus on hosting rather than specialist visualisation.
- **[React](https://react.dev/)** — JavaScript library for component-based user interfaces; v19 with the React Compiler used in the map client.
- **[React JSON Schema Form (RJSF)](https://github.com/rjsf-team/react-jsonschema-form)** — React library that renders forms from JSON Schema definitions with client-side validation.
- **[TerriaJS](https://terria.io/)** — open-source spatial-data explorer shell built on CesiumJS, originated by CSIRO Data61.
- **[Vite](https://vitejs.dev/)** — modern dev server and bundler for single-page-app builds.

## 7. Spatial and data concepts

- **[Atomic S3 CopyObject swap](https://docs.aws.amazon.com/AmazonS3/latest/userguide/copy-object.html)** — promotion pattern using S3's in-bucket copy to switch live artefacts without a half-written state.
- **[Byte-range read (RFC 7233)](https://datatracker.ietf.org/doc/html/rfc7233)** — HTTP Range request returning a subset of an object's bytes; the substrate for COG/PMTiles/COPC.
- **[ETag-driven cache refresh](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObject.html)** — pattern of invalidating an in-memory cache when an object's S3 ETag changes after an atomic swap.
- **[Hive-style partitioning](https://cwiki.apache.org/confluence/display/Hive/LanguageManual+DDL#LanguageManualDDL-PartitionedTables)** — directory convention `key=value/...` understood by analytical engines for partition-key pushdown.
- **[Optimistic locking](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBMapper.OptimisticLocking.html)** — concurrency control via a version attribute and conditional write, rejecting stale updates.
- **[Predicate pushdown](https://parquet.apache.org/docs/file-format/)** — engine pushes filter predicates down to the storage layer (Parquet row-group statistics, partition paths) to skip data.
- **[Quadkey index](https://learn.microsoft.com/en-us/bingmaps/articles/bing-maps-tile-system)** — string encoding of tile coordinates used by MosaicJSON to index COGs by spatial cell.
- **Slowly Changing Dimension Type 2 (SCD2)** — dimensional-modelling pattern that tracks change history with `valid_from`/`valid_to`/`is_current` columns. See [Kimball Group: Type 2](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/type-2/).
- **[Tile coordinates (z/x/y)](https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames)** — Web Mercator slippy-map tiling scheme; the basis for XYZ tile URLs and PMTiles indexing.
- **[Web Mercator (EPSG:3857)](https://epsg.io/3857)** — projected CRS used by most web mapping tile pyramids.

## 8. Peer geospatial stacks

These are the geospatial stacks worth being aware of when considering or extending this platform. Most are standards-compliant OGC peers; one (VAMS) is adjacent — a 3D / visual-asset platform that shares this platform's serverless substrate. Several were evaluated explicitly during the design — see [Peer stacks and prior art](16_DESIGN_DECISIONS.md) in [16 Design Decisions](16_DESIGN_DECISIONS.md).

- **[Apache Sedona](https://sedona.apache.org/)** — Distributed spatial SQL extension for Apache Spark, Flink, and Snowflake; underpins Databricks GeoBrix and Wherobots. Evaluated; analytical-first — well-suited to lakehouse compute, not to stateless serving. See [18 Lakehouse Integration](18_LAKEHOUSE_INTEGRATION.md).
- **[CARTO](https://carto.com/)** — Commercial spatial analytics platform; Analytics Toolbox runs inside Snowflake, BigQuery, Databricks, and Redshift. Evaluated; requires a warm cluster as its substrate, which conflicts with the scale-to-zero target.
- **[eoAPI](https://eoapi.dev/)** — Development Seed's reference stack bundling pgSTAC, TiTiler, and tipg; the closest peer assembly to this platform. NASA IMPACT, MAAP, and VEDA build on it.
- **[Felt](https://felt.com/)** — Browser-native collaborative mapping platform; current maintainer of Tippecanoe (see [D6 in 16 Design Decisions](16_DESIGN_DECISIONS.md)). Evaluated; per-seat licensing does not fit a platform whose consumers are mostly anonymous or programmatic.
- **[GeoMesa](https://www.geomesa.org/)** — Spatio-temporal indexing layer over Accumulo, HBase, Cassandra, or Kafka. Evaluated; needs a managed cluster of its own, which conflicts with the scale-to-zero target.
- **[GeoNetwork](https://geonetwork-opensource.org/)** — Long-standing open-source metadata catalog implementing OGC CSW and ISO 19115/19139. Evaluated as the discovery layer; the DynamoDB dataset registry plus a STAC façade filled the same role with less always-on overhead.
- **[GeoNode](https://geonode.org/)** — Django-based geospatial CMS layered on GeoServer.
- **[GeoServer](https://geoserver.org/)** — Java-based OGC services server (WMS, WFS, WCS, WMTS, plus OGC APIs).
- **[GeoServer Cloud](https://github.com/geoserver/geoserver-cloud)** — Spring Boot microservices refactor of GeoServer for cloud-native ECS/Kubernetes deployment. Trialled here and rejected for specific gaps (private-S3 COG reads, SOAP mosaic generation, UI friction); see [Peer stacks and prior art](16_DESIGN_DECISIONS.md) for the full assessment.
- **[ldproxy](https://github.com/interactive-instruments/ldproxy)** — Java OGC API server emphasising linked-data and HTML output.
- **[MapProxy](https://mapproxy.org/)** — Python tile-caching proxy for WMS/WMTS layers.
- **[MapServer](https://mapserver.org/)** — long-standing C-based OGC web map server.
- **[Martin](https://martin.maplibre.org/)** — Rust vector-tile server backed by PostgreSQL/PostGIS or PMTiles; replaced here by go-pmtiles.
- **[pg_featureserv](https://github.com/CrunchyData/pg_featureserv)** — lightweight Go OGC API Features server over PostGIS.
- **[pg_tileserv](https://github.com/CrunchyData/pg_tileserv)** — lightweight Go vector tile server over PostGIS.
- **[pgRouting](https://pgrouting.org/)** — PostGIS extension for in-database network routing. Evaluated; eliminated by D1 (no PostgreSQL in the read path). Valhalla — see [09 Routing](09_ROUTING.md) — covers the same use cases without a database dependency.
- **[pgSTAC](https://github.com/stac-utils/pgstac)** — PostgreSQL-backed STAC implementation used in this platform's prior iteration, since replaced.
- **[pygeoapi](https://pygeoapi.io/)** — Python OGC API reference implementation (Features, Coverages, Tiles, Processes, EDR, Records). Did not (at the time of this design) provide GeoJSON feature editing over object-store-backed providers, which is the gap the editing pipeline fills.
- **[stac-browser](https://github.com/radiantearth/stac-browser)** — Static UI for browsing any STAC API; common companion to stac-fastapi. Evaluated as the catalogue front-end; the first-party map client absorbed the same role within the platform's auth gate.
- **[stac-fastapi](https://stac-utils.github.io/stac-fastapi/)** — Python/FastAPI STAC API server with multiple backend adapters (pgSTAC, OpenSearch, ElasticSearch).
- **[Tegola](https://tegola.io/)** — Go vector tile server backed by PostGIS, GeoPackage, or HANA. Evaluated; limited fit for the platform's PMTiles-first, database-free serving model.
- **[TiMVT](https://developmentseed.org/timvt/)** — Lightweight Python dynamic vector tile server over PostGIS from Development Seed. Evaluated; limited fit for the same database-free reasons as Tegola.
- **[tipg](https://developmentseed.org/tipg/)** — Development Seed's OGC API Features and Tiles server over PostGIS.
- **[titiler-pgstac](https://stac-utils.github.io/titiler-pgstac/)** — TiTiler variant that builds raster mosaics from STAC search backed by pgSTAC.
- **[T-Rex](https://t-rex.tileserver.ch/)** — Rust vector tile server over PostGIS. Evaluated; limited fit for the same database-free reasons as Tegola, and less actively maintained than Martin.
- **[Visual Asset Management System (VAMS)](https://awslabs.github.io/visual-asset-management-system/)** — AWS Labs' serverless 3D / point cloud / CAD asset management platform on S3 + DynamoDB + OpenSearch, with configurable processing pipelines, a browser viewer with 17+ format plugins, and ABAC/RBAC at API and data-entity levels. Adjacent rather than OGC; partly inspired this platform's authorisation design and is the natural reference if 3D and visual assets become first-class — see [17 Further Directions §12](17_FURTHER_DIRECTIONS.md#12-3d-and-visual-asset-management--vams-style-extension).

## 9. Infrastructure-as-code

- **[Amazon States Language (ASL)](https://states-language.net/spec.html)** — JSON-based state-machine language used to define Step Functions workflows.
- **[AWS CDK](https://docs.aws.amazon.com/cdk/)** — AWS Cloud Development Kit; define cloud resources in code (Python, TypeScript, etc.) and compile to CloudFormation.
- **[AWS CloudFormation](https://docs.aws.amazon.com/cloudformation/)** — AWS declarative infrastructure-as-code service that CDK compiles to.
- **[CfnListenerRule (CloudFormation)](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-elasticloadbalancingv2-listenerrule.html)** — CloudFormation primitive for ALB v2 path-based listener rules and URL-rewrite transforms.

## 10. Other references

- **[GraphQL](https://graphql.org/)** — typed, introspectable query language and runtime used for the platform's internal query layer.
- **[HTTP 410 Gone (RFC 9110)](https://datatracker.ietf.org/doc/html/rfc9110#name-410-gone)** — HTTP status indicating a resource is intentionally permanently removed; used for retired datasets.
- **[OpenStreetMap (OSM)](https://www.openstreetmap.org/)** — open-licence global road network and feature database used to build Valhalla routing graphs.
- **[RFC 3339 datetime](https://datatracker.ietf.org/doc/html/rfc3339)** — internet-friendly datetime format used by OGC API Features for temporal queries.

---

Suggestions, corrections, and broken links: this is the kind of reference page that needs occasional refresh. The canonical URLs were checked at publication; some will move. The descriptions are deliberately brief — each is a pointer, not an explanation.
