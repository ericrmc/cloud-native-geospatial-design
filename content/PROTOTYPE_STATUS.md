# Prototype Status Manifest

This is a code-grounded snapshot of the prototype that informed the design corpus, captured on 2026-05-26 to brief the receiving team on what code exists today and in what state. The reading deliberately ignores the prototype's own in-repo documentation — the design corpus is the canonical narrative — and is derived from CDK stack definitions, Lambda handlers, container source, and the React client.

Unlike the rest of the corpus, this document **dates quickly**. The design chapters describe a durable shape; this manifest describes a code state that will move under any active maintenance. Treat it as a snapshot, not a contract.

## Repository

- **Languages.** Python 3.12 (infrastructure, Lambdas, ECS services); TypeScript / React 19 (web client); Bash (build and ops scripts).
- **Build and deploy.** AWS CDK v2 in Python. Entry point `infrastructure/app.py`, driver config `cdk.json`, dependencies `requirements.txt`. Container images are built with the `scripts/build-stac-images.sh` family and pushed to ECR; the client is bundled with Vite.
- **Top-level layout.**
  - `infrastructure/stacks/` — 18 CDK stack modules plus `scaling_config.py` (~5,700 LoC).
  - `functions/` — 17 Lambda packages (~4,400 LoC of handlers, plus `editing_api/`, `policy_api/`, `features_api/` sub-packages).
  - `services/` — 11 container-service folders (Fargate workloads; ~12,000 LoC across Python services).
  - `map-client/` — React 19 + MapLibre GL single-page app (~5,500 LoC of TS/TSX).
  - `viewer/` — single 767-line static `map-viewer.html` demo.
  - `scripts/` — ~40 shell and Python operational scripts (data loading, ECS exec, tile testing).
  - `catalogues/`, `cdk.out/`, `.venv/` — generated or build artefacts.

## Infrastructure stacks

All stack names follow `{project_name}-{suffix}-{env}`. Service enablement is driven by `ENVIRONMENT_PROFILES` in `infrastructure/scaling_config.py`: `dev` deploys everything; `test` and `prod` drop the `raster`, `coverages`, and `sync` groups.

- **StorageStack** (`storage_stack.py`) — Two S3 buckets: `SpatialDataBucket` (versioned, SSE-S3, lifecycle: `drafts/` 90d, `landing/` 7d, Intelligent-Tiering transition at 30d) and `AccessLogsBucket` (90d retention). Complete.
- **NetworkStack** (`network_stack.py`) — VPC (`10.250.0.0/24`, 2 AZs, 2 NAT GWs), public and private subnets, internal ALB with HTTP listener, security groups for ALB / ECS / VPC Link / RDS. The `rds_security_group` is created but no Aurora cluster is provisioned anywhere. Complete for ALB; the RDS SG is dead weight.
- **ComputeInfraStack** (`compute_infra_stack.py`) — ECS cluster, shared task execution and task roles, shared CloudWatch log group. Complete.
- **AuthStack** (`auth_pipeline_stack.py`) — Cognito user pool + app client (email sign-in, MFA optional), `PoliciesTable` and `ApiKeysTable` DynamoDB tables, `post-auth` Cognito trigger Lambda, `policy-api` Lambda fronted by ALB at `/rest/*`. Complete.
- **ApiGatewayStack** (`api_gateway_stack.py`) — API Gateway v2 HTTP API with a catch-all `/{proxy+}` route, Lambda authorizer, VPC Link to the internal ALB, parameter mapping that promotes authorizer context into `X-Auth-*` headers, JSON access logging to CloudWatch. Complete.
- **CdnStack** (`cdn_stack.py`) — CloudFront distribution with API Gateway origin (low cache, forwards `Authorization`), S3 origins for viewer and map-client static assets, custom response headers policy, S3 access logging. Complete.
- **EditingPipelineStack** (`editing_pipeline_stack.py`, ~1,000 LoC — the largest stack) — `JobsTable`, `DatasetsTable`, `EditSessionsTable` (each with multiple GSIs); `ValidationQueue` + DLQ; CloudWatch alarms on DLQ depth, history-vacuum errors, state-machine failures; Fargate task definitions for `validation-task` and `generation-task`; eight Lambdas (`sql-edit-executor`, `failure-handler`, `post-generation`, `pipeline-trigger`, `upload-gate`, `job-api`, `dataset-sync`, `history-vacuum`, `event-log-compactor`); two Step Functions state machines (main `validate → generate → post-generation` plus `regeneration`); EventBridge schedules (15-min dataset sync, daily history vacuum, daily event-log compaction). Complete and battle-scarred. **Note:** the S3-bucket-to-SQS notification is *not* wired by CDK due to a cyclic dependency — it is configured out of band by `scripts/bootstrap_auth.sh`. This is a load-bearing manual step.
- **EditingApiStack** (`editing_api_stack.py`) — FastAPI Lambda (`functions/editing-api`) mounted on the ALB at `/edit-sessions/*`, `/editing/*`, `/validation-checks/*`, `/validation-sequences/*`. Complete.
- **TiTilerServiceStack** (`titiler_service_stack.py`) — Fargate service running upstream `developmentseed/titiler` (Dockerfile builds locally with GDAL). Complete; only enabled in `dev`.
- **WmtsProxyStack** (`wmts_proxy_stack.py`) — Custom Fargate service from `services/wmts-proxy/`. Complete; only enabled in `dev`.
- **PMTilesServiceStack** (`pmtiles_service_stack.py`) — Fargate service running `ghcr.io/protomaps/go-pmtiles:latest`, routed via ALB `/tiles/vector/*`. Comment notes "replaces Martin." Complete.
- **GraphQLApiStack** (`graphql_api_stack.py`) — Fargate service from `services/graphql-api/` (Strawberry + DuckDB). Complete.
- **FeaturesApiStack** (`features_api_stack.py`) — Thin OGC API Features facade Lambda calling graphql-api over HTTP. Complete.
- **CoveragesApiStack** (`coverages_api_stack.py`) — Fargate service from `services/coverages-api/` (rasterio + COG/S3). Complete; only `dev`.
- **StacServiceStack** (`stac_service_stack.py`) — Lambda-based STAC API behind ALB at `/stac/*`. Reads from the datasets table; uses bundled dependencies via CDK `BundlingOptions`. Complete.
- **ValhallaServiceStack** (`valhalla_service_stack.py`) — Fargate service from a Dockerfile that bakes Victoria-only OSM tiles into the image at build time. Complete but the routing graph is hard-coded to Victoria, AU.
- **MonitoringStack** (`monitoring_stack.py`) — Two CloudWatch dashboards (Ops and Usage), alarms for ALB 5xx, API Gateway 5xx, authorizer errors, ECS service health, Step Functions failures. Complete; adapts to which services are enabled.
- **DeltaVicSyncStack** (`deltavic_sync_stack.py`) — **Defined but never instantiated** — not imported in `app.py`. The `sync` group is referenced in `scaling_config.py` and listed in the `dev` profile, but deployment silently no-ops for it. Effectively dead code.

## Lambda functions

| Function | Source | Purpose and integration | State |
|---|---|---|---|
| `gateway-authorizer` | `functions/gateway_authorizer/handler.py` + `functions/auth/authorizer.py` (~740 LoC) | API Gateway HTTP Lambda authorizer; validates Cognito JWT or API key, resolves RLS and dataset access, returns context for header injection. In-memory LRU cache. | Implemented; one TODO at `authorizer.py` re. `scope_ceiling` dataset filter. |
| `policy-api` | `functions/policy-api/handler.py` + `policy_api/` package (~2,400 LoC) | REST admin API at `/rest/*` — auth ceilings, platform groups, group members, invites, projects, API keys, datasets, validation schemas, self-service. Heaviest single Lambda. | Implemented; well-tested (11 test files). |
| `editing-api` | `functions/editing-api/handler.py` (Mangum) + `editing_api/routes/*.py` | FastAPI behind ALB. Versioned edit-session workflow, presigned uploads, approve/reject/regenerate, check + sequence CRUD, OGC-style feature CRUD via job queue. | Implemented; tests cover 4 of 6 route modules. One TODO in `sequences.py` re. dataset-sequence-reference check on delete. |
| `features-api` (Lambda) | `functions/features-api/` (~720 LoC) | OGC API Features Lambda behind ALB at `/features/*`. Mangum wrapper; delegates to graphql-api. **Note:** an almost-identical `services/features-api/` container variant also exists. | Implemented but partially duplicated with the container service, only one needs to be deployed, latest preference was Lambda as GraphQL ECS would maintain the DuckDB connection. |
| `stac-api` | `functions/stac-api/handler.py` (~530 LoC) | Lambda-backed STAC 1.0.0 discovery layer reading the DynamoDB datasets table; in-memory TTL cache. | Implemented. |
| `job-api` | `functions/job-api/handler.py` (~280 LoC) | ALB Lambda at `/jobs/*`: GET, list, cancel. Role and ACL filtering. | Implemented. |
| `upload-gate` | `functions/upload-gate/handler.py` (~160 LoC) | ALB Lambda at `/uploads/request`: returns presigned S3 PUT URLs after role and dataset access checks. | Implemented. |
| `sqs-trigger` (pipeline-trigger) | `functions/sqs-trigger/handler.py` | SQS → Step Functions bridge; parses S3 event from SQS body, starts the unified state machine. | Implemented. |
| `post-generation` | `functions/post-generation/handler.py` (~700 LoC) | Step Functions task: atomic tile promotion (S3 `CopyObject`), CloudFront invalidation, job completion, staging cleanup. Largest pipeline Lambda. | Implemented. |
| `failure-handler` | `functions/failure-handler/handler.py` | Step Functions catch-block target: marks job and dataset failed and dequeues next job. | Implemented. |
| `sql-edit-executor` | `functions/sql-edit-executor/handler.py` | Lambda invoked by policy-api or pipeline; runs DuckDB SQL against source Parquet for dry-run preview or full edit. | Implemented. |
| `dataset-sync` | `functions/dataset-sync/handler.py` | EventBridge target every 15 min; validates S3 paths referenced by datasets table; flags stale records. Does **not** create dataset records. | Implemented; scoped intentionally narrow. |
| `history-vacuum` | `functions/history-vacuum/handler.py` (~250 LoC) | EventBridge target daily; compacts SCD2 history delta files into monthly Parquet archives via pyarrow. Honours `history_retention_days`. | Implemented; has its own error alarm. |
| `event-log-compactor` | `functions/event-log-compactor/handler.py` (~280 LoC) | EventBridge target daily; merges small per-event Parquet files under `metadata/dataset_events/`. | Implemented. |
| `post-auth` | `functions/post-auth/handler.py` | Cognito post-authentication trigger: converts pending INVITE# items into MEMBER# items. Header comment flags a future migration to an API endpoint when Cognito is replaced by Entra. | Implemented. |
| `time-proxy` | `functions/time-proxy/handler.py` | Maps a WMS/WMTS `TIME` parameter to a date-stamped MosaicJSON before forwarding to TiTiler. | Implemented; **not wired into any stack** (search of `infrastructure/stacks/` returns no references). Appears orphaned; only used by `scripts/test_time_api.py`. |

## Container services

| Service | Source | Engine / entrypoint | State |
|---|---|---|---|
| `titiler` | `services/titiler/Dockerfile` only | Python 3.12 + GDAL; runs upstream `titiler.application` 0.18.0 on port 8080. No custom code. | Off-the-shelf, complete. |
| `pmtiles` | (no source dir; image pulled directly) | `ghcr.io/protomaps/go-pmtiles:latest`; ALB `/tiles/vector/*`. | Off-the-shelf, complete. |
| `valhalla` | `services/valhalla/Dockerfile` | Builds from `ghcr.io/valhalla/valhalla:latest`; downloads `victoria-latest.osm.pbf` at build time and bakes routing tiles. Port 8002. | Complete but region-locked to Victoria, AU. |
| `graphql-api` | `services/graphql-api/graphql_api/` (~5,000 LoC across schema, engines, resolvers) | Python 3.12 / FastAPI + Strawberry + DuckDB; `graphql_api.main:app` on port 8000. Rich engine layer: filters, geometry_ops (~710 LoC), spatial_queries (~490 LoC), joins, linear_referencing, validation. Resolvers cover aggregation, fanout, geometry, history, joins, linear-ref, mutations, nested, provenance, routing. | Implemented; substantial test suite (6 modules). |
| `coverages-api` | `services/coverages-api/app.py` (~470 LoC) | Python 3.12 / FastAPI + rasterio; reads COGs from S3 via GDAL `vsis3`; collections sourced from the datasets table. Port 8000. | Implemented; no tests. |
| `wmts-proxy` | `services/wmts-proxy/wmts_proxy/` (~900 LoC; includes `esri_adapter.py`) | Python 3.12 / FastAPI; serves WMS + WMTS facades and proxies tile bytes. | Implemented; `test_app.py` plus a Docker test rig. |
| `features-api` (container) | `services/features-api/features_api/` (~815 LoC) | Python 3.12 / FastAPI; thin OGC façade calling graphql-api via httpx. Duplicates the Lambda variant. | Implemented; only `tests/conftest.py` — no actual tests. |
| `validation-task` | `services/validation-task/` (`handler.py` ~780, `validate.py` ~880, `custom_checks.py` ~580 LoC) | Python entrypoint `handler.py`; DuckDB-driven validation runs invoked by Step Functions. | Implemented; only `test_custom_checks.py` covers a slice. |
| `generation-task` | `services/generation-task/` (`generate.py` ~340, `delta_generate.py` ~590 LoC) | Tippecanoe 2.79.0 + DuckDB; entrypoint `delta_generate.py` dispatches: `SESSION_ID` present → session tiles, else → legacy `generate.py`. | Implemented; no tests. Dispatcher comment flags the legacy path explicitly. |
| `deltavic` | `services/deltavic/Dockerfile` + `entrypoint.sh` | Wraps external `deltavic:latest` image; generates `config.ini` from env vars and runs `python deltaVic.py "$@"`. Requires Aurora PostGIS. | Container is ready, but **not deployed** because `DeltaVicSyncStack` is not instantiated in `app.py`. |
| `pipeline` | `services/pipeline/` | Shared Python package (`models.py`) copied into validation and generation containers at build time. Not a runtime service. | Shared library, complete. |

## Web client (`map-client/`)

- **Framework.** React 19 + Vite 8 + TypeScript 5.9; MapLibre GL 5.20 for the map; raw `fetch` for GraphQL; React JSON Schema Form (`@rjsf/core` 6) for dynamic forms; `amazon-cognito-identity-js` for sign-in; `@graphiql/react` embedded.
- **App composition** (`src/App.tsx`). Nested providers — `AuthProvider` › `ApiKeyProvider` › `LayerProvider` › `MapInstanceProvider` › `SpatialParamsProvider` › `EditSessionProvider`. Layout: Sidebar + MapView + TimeSlider + DrawControls + DrawTools + MeasureTool + FeaturePopup + EditWidget + JobToast + LayerSyncBridge.
- **Implemented surfaces.**
  - **Auth and API keys** — `LoginPanel`, `AuthContext` (Cognito), `ApiKeyContext` (with tests).
  - **Catalogue / TOC** — `DatasetSearch` (with test), `TableOfContents`, `StylePanel`, `PreferencesPanel`.
  - **Map interaction** — `MapView`, `DrawControls`, `DrawTools`, `MeasureTool`, `FeaturePopup`, `TimeSlider`.
  - **Editing** — `EditWidget`, `SchemaForm` (RJSF), `EditSessionContext` (~460 LoC — heaviest context).
  - **Review** — `ReviewPanel` (~440 LoC), `useReviewLayers`, `DatasetHistory` with diff visualisation styling.
  - **Query** — embedded `GraphiQLPanel` (~460 LoC) with bbox-placeholder substitution and view-save UI.
  - **Job toasts** — `JobToast` for async pipeline progress.
- **Hooks and utilities.** Dynamic layer hooks for vector tiles, raster, GeoJSON; permission lookup; auth fetch wrapper; layer URL builders; colour palette; GraphQL normalisation. All utilities have Vitest tests.
- **Notably stubbed or absent.** No platform-admin surfaces in the client — group management, invite issuance, ceiling configuration, and API-key minting all live exclusively in the policy-api REST routes; there is no UI calling them. No standalone dataset-detail page (dataset info appears via popups and TOC). `viewer/map-viewer.html` is a separate 767-line static demo, independent of the React app.

## Tests

- **Python.** `pytest`. Test suites exist for `policy-api` (11 files), `editing-api` (4 files), `graphql-api` (6 files), `validation-task` (1 file), `wmts-proxy` (1 file + Docker harness). Tests are pure unit tests — no `moto` or `mock_aws` usage despite `moto>=4.2.0` being declared in `requirements.txt`. No `boto3` mocking visible in shared `conftest.py` files.
- **TypeScript.** `vitest` + Testing Library; 7 test files (5 utility, 1 context, 1 component). Coverage is utility-heavy, light on components.
- **Missing test coverage.** No tests for `coverages-api`, `features-api` (either variant has only an empty `conftest.py`), `generation-task`, most Lambda handlers in `functions/` (only the FastAPI-based ones have suites), or any of the React feature components (`MapView`, `EditWidget`, `ReviewPanel`, `GraphiQLPanel`).
- **Integration and end-to-end.** No fixtures, no compose files for cross-service tests. `scripts/integration_test.sh`, `scripts/test_pipeline_local.sh`, `scripts/test_titiler.py` are ad-hoc smoke tests against a live deployment, not automated.

## Open issues visible in code

- **Explicit `TODO` / `FIXME`.** Only two in non-test source — `functions/auth/authorizer.py` (dataset filtering by `scope_ceiling`) and `functions/editing-api/editing_api/routes/sequences.py` (sequence-reference check on delete). The codebase is unusually clean of inline TODO markers; either disciplined cleanup or decisions are tracked externally (in the design corpus).
- **Orphaned / dead code.**
  - `infrastructure/stacks/deltavic_sync_stack.py` and `services/deltavic/` — defined and listed in the `dev` profile but never instantiated in `app.py`.
  - `functions/time-proxy/handler.py` — has no CDK stack referencing it; only `scripts/test_time_api.py` mentions it.
  - `network_stack.py` creates an `rds_security_group` for an Aurora cluster nothing else provisions.
- **Duplicated implementations.** `functions/features-api/` (Lambda+Mangum) and `services/features-api/` (Fargate container) both wrap the same FastAPI app. Both stacks reference different code paths; resolve before handover.
- **Out-of-band wiring.** The S3 → SQS validation notification is not created by CDK (a comment on `editing_pipeline_stack.py` says the cyclic dependency forces it to be done by `scripts/bootstrap_auth.sh`). Load-bearing manual step.
- **Hard-coded assumptions.** Valhalla bakes Victoria, AU OSM data at build time. `cdk.json` defaults region to `ap-southeast-2`. `services/deltavic/entrypoint.sh` embeds a specific Vicmap API base URL. None are parameterised.
- **Deprecated patterns being phased out.** `generation-task/delta_generate.py` is the new dispatcher; `generate.py` is explicitly labelled legacy but still ships. `wmts_proxy_stack.py` comment refers to "replaces Martin." `post-auth/handler.py` flags a future migration off Cognito to Entra ID.
- **Backwards-compat shims.** `storage_stack.py` exposes `self.cog_bucket = self.spatial_data_bucket` and `self.pmtiles_bucket = self.spatial_data_bucket` to support old attribute names.
- **`moto` declared but unused.** `requirements.txt` pulls `moto>=4.2.0` for tests; no test imports it. Either drop it or actually use it.

## What's notably absent

Components or capabilities the design corpus describes that have no corresponding code, or only skeleton code:

- **Geocoder / gazetteer service** — not present (no matches under `services/`, `functions/`, or stacks).
- **Point-cloud API** — only a commented-out group placeholder in `scaling_config.py` (`# "pointcloud": {"pointcloud-api"}`).
- **Aurora PostGIS database** — referenced indirectly (RDS SG, deltavic env vars) but no cluster is provisioned anywhere in CDK. DeltaVic sync is the only would-be consumer and that stack is orphaned.
- **Admin web UI** — no React routes or components for group, invite, ceiling, project, or API-key management; all admin surfaces are REST-only via `policy-api`.
- **WAF / Shield / public DNS / TLS cert** — not visible in CDN or API Gateway stacks; only the basic CloudFront default cert is implied.
- **End-to-end / integration test harness** — only ad-hoc shell scripts; no recorded fixtures, no compose, no synthetic monitoring construct.
- **Multi-region / DR** — single-region (`ap-southeast-2`), single-VPC. No replication primitives in `storage_stack.py`.

## State indicators

| Component | Code present | State | Notes |
|---|---|---|---|
| StorageStack | Y | Complete | Two buckets, lifecycle and logging |
| NetworkStack | Y | Complete (RDS SG unused) | `rds_security_group` orphan |
| ComputeInfraStack | Y | Complete | Shared cluster, roles, log group |
| AuthStack | Y | Complete | Cognito + 2 DDB tables + 2 Lambdas |
| ApiGatewayStack | Y | Complete | HTTP API v2, single catch-all route |
| CdnStack | Y | Complete | CloudFront + headers + S3 origins |
| EditingPipelineStack | Y | Complete (with manual S3→SQS step) | Largest stack |
| EditingApiStack | Y | Complete | FastAPI Lambda on ALB |
| TiTilerServiceStack | Y | Complete | dev-only |
| WmtsProxyStack | Y | Complete | dev-only |
| PMTilesServiceStack | Y | Complete | go-pmtiles image |
| GraphQLApiStack | Y | Complete | Heavy engine layer |
| FeaturesApiStack | Y | Complete | Thin Lambda over graphql-api |
| CoveragesApiStack | Y | Complete | dev-only; no tests |
| StacServiceStack | Y | Complete | Lambda + CDK bundling |
| ValhallaServiceStack | Y | Complete (Victoria-only) | OSM baked into image |
| MonitoringStack | Y | Complete | 2 dashboards + alarms |
| DeltaVicSyncStack | Y | **Orphaned** | Not in `app.py` |
| Lambda: gateway-authorizer | Y | Implemented | 1 TODO re scope filter |
| Lambda: policy-api | Y | Implemented | Best-tested Lambda |
| Lambda: editing-api | Y | Implemented | 6 route modules, 1 TODO |
| Lambda: features-api | Y | Implemented (duplicates container) | Resolve duplication |
| Lambda: stac-api | Y | Implemented | TTL cache |
| Lambda: job-api | Y | Implemented | Auth-aware listing |
| Lambda: upload-gate | Y | Implemented | Presigned PUTs |
| Lambda: sqs-trigger | Y | Implemented | SQS → SFN |
| Lambda: post-generation | Y | Implemented | Atomic promote |
| Lambda: failure-handler | Y | Implemented | SFN catch target |
| Lambda: sql-edit-executor | Y | Implemented | DuckDB |
| Lambda: dataset-sync | Y | Implemented | 15-min schedule |
| Lambda: history-vacuum | Y | Implemented | Daily SCD2 vacuum |
| Lambda: event-log-compactor | Y | Implemented | Daily Parquet merge |
| Lambda: post-auth | Y | Implemented | Cognito trigger |
| Lambda: time-proxy | Y | **Orphaned** | No stack references it |
| Container: titiler | Y | Off-the-shelf | upstream image |
| Container: pmtiles | N (image only) | Off-the-shelf | ghcr.io |
| Container: valhalla | Y | Complete (region-locked) | Victoria OSM |
| Container: graphql-api | Y | Implemented + tested | Strawberry + DuckDB |
| Container: coverages-api | Y | Implemented, no tests | rasterio |
| Container: wmts-proxy | Y | Implemented + tests | WMS + WMTS facade |
| Container: features-api | Y | Implemented, conftest only | Duplicate of Lambda |
| Container: validation-task | Y | Implemented, partial tests | ~2,200 LoC |
| Container: generation-task | Y | Implemented, no tests | legacy `generate.py` still ships |
| Container: deltavic | Y | **Not deployed** | Stack orphaned |
| Web: catalogue + map | Y | Implemented + tested utilities | TableOfContents, MapView |
| Web: editing UI | Y | Implemented | EditWidget + RJSF SchemaForm |
| Web: review UI | Y | Implemented | ReviewPanel + DatasetHistory |
| Web: query UI | Y | Implemented | embedded GraphiQL |
| Web: admin UI | N | Absent | REST-only via policy-api |
| Tests: unit (Python) | Y | Patchy | policy-api / graphql-api solid, others sparse |
| Tests: unit (TS) | Y | Patchy | utilities covered, components not |
| Tests: integration / e2e | N | Absent | only ad-hoc shell scripts |
| Geocoder / gazetteer | N | Absent | design only |
| Point-cloud service | N | Absent | commented-out placeholder |
| Aurora PostGIS | N | Absent | SG only |

## Suggested first steps for the receiving team

- **Stand up a sandbox** with `cdk deploy --all --context environment=dev --context scaling_mode=off` (zero-cost baseline), then bring services up with `scaling_mode=minimal`. Run `scripts/bootstrap_auth.sh` afterwards to install the S3→SQS notification — without it the editing pipeline never fires.
- **Resolve the `features-api` duplication** (Lambda in `functions/features-api/` vs container in `services/features-api/`) before any cleanup or refactor. The two share a package name but live in different deploy paths.
- **Decide the fate of orphaned code.** Either wire `DeltaVicSyncStack` and `time-proxy` into `app.py` (and provision the Aurora cluster the deltavic flow needs), or delete them. Same for the unused `rds_security_group`.
- **Add an end-to-end smoke test** that exercises ingest → validate → generate → promote across a deployed sandbox; `scripts/integration_test.sh` is the closest starting point and is not run by CI.
- **Backfill tests on the container services with zero coverage** (`coverages-api`, `generation-task`, `features-api`) and the unwrapped Lambdas (`post-generation`, `sql-edit-executor`, `history-vacuum`, `event-log-compactor`) — these are the highest-blast-radius pieces and currently rely on production runs to catch regressions.
