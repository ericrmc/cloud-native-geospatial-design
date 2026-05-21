# 13 — Operations

This document describes day-to-day operations: monitoring, alarms, troubleshooting, scheduled maintenance, and disaster recovery considerations. It assumes the platform is deployed as described in [12 Deployment](12_DEPLOYMENT.md).

## Monitoring surface

Two **Amazon CloudWatch** dashboards are recommended, with metrics drawn from CloudWatch metrics for ALB, API Gateway, CloudFront, ECS, Lambda, Step Functions, DynamoDB, and S3.

### Operations dashboard

For platform operators. Tracks the health of the components themselves.

| Panel | Source | Purpose |
|---|---|---|
| ALB request rate, 4xx/5xx counts, p50/p95/p99 latency | CloudWatch (ALB metrics) | Detect traffic anomalies and latency drift |
| API Gateway HTTP API request rate, integration latency, authoriser duration | CloudWatch (API Gateway metrics) | Identify gateway-level issues |
| CloudFront cache hit rate, edge request counts, byte counts | CloudWatch (CloudFront metrics) | Quantify cache effectiveness |
| Fargate service task counts, CPU/memory utilisation, scaling actions | CloudWatch (ECS service metrics) | Capacity health |
| Lambda authoriser invocations, errors, cold-start init duration | CloudWatch (Lambda metrics) | Auth path health |
| Step Functions executions started/succeeded/failed, current running | CloudWatch (Step Functions metrics) | Editing pipeline health |
| S3 storage growth per prefix | S3 Storage Lens | Storage trend |
| DynamoDB throttling, latency, consumed capacity | CloudWatch (DynamoDB metrics) | Data layer health |

### Usage dashboard

For platform owners and users.

| Panel | Purpose |
|---|---|
| Per-credential request counts (top 20) | Who is using the platform |
| Per-credential data egress | Volume per consumer |
| Per-service request breakdown | Which capabilities are exercised |
| Feature downloads (count, bytes) | OGC Features API usage |
| Tile requests (vector and raster) | Tile traffic |
| Editing activity (jobs per dataset, success/failure) | Edit workflow usage |
| Error rate by user | Identify clients with problems |

## Alarms

A small set of alarms covers the failure modes that need human attention.

| Alarm | Condition | What it means |
|---|---|---|
| Load balancer 5xx rate | ≥ 10 in 5 minutes for 2 periods | Backend errors, capacity, or configuration issue |
| Backend 5xx rate | ≥ 20 in 5 minutes for 2 periods | Specific backend is failing |
| Load balancer p95 latency | > 5 seconds for 3 periods | Slow responses; possible cold start storm or saturation |
| API gateway 5xx rate | ≥ 10 in 5 minutes for 2 periods | Gateway or authoriser failures |
| Authoriser errors | ≥ 5 in 5 minutes for 2 periods | Authoriser crashing |
| Container CPU (per service) | > 80% for 3 periods | Service needs more capacity |
| Workflow engine failures | ≥ 1 per period | Editing pipeline failure |
| Validation dead-letter queue depth | > 0 | Uploads failing to parse |

Each alarm should link to a runbook section below.

## Log sources

| Source | Destination | Retention | Content |
|---|---|---|---|
| API Gateway HTTP API access logs | CloudWatch Logs | 30 days | `userId`, path, status, response length, latency |
| ALB access logs | S3 `alb-logs/` prefix | 90 days | Client IP, path, status, latency |
| CloudFront standard logs | S3 `cloudfront-logs/` prefix | 90 days | Edge location, bytes, URI, status, user agent |
| ECS / Fargate container logs | CloudWatch Logs | 7 days | Application stdout/stderr |
| Lambda function logs | CloudWatch Logs | 14 days | Per-invocation output and structured logs |
| VPC flow logs | CloudWatch Logs | 7 days | Network traffic metadata |
| Dataset event log | S3 `metadata/dataset_events/` | Indefinite (compacted monthly) | Per-dataset events (jobs, schema changes, SQL edits) |

## Common queries

Useful queries to keep handy, expressed in **CloudWatch Logs Insights** syntax against the API Gateway access-log group:

**Top users by request count (last 24 hours)**:
```
filter userId != '' and userId != 'anonymous'
| stats count(*) as requests by userId
| sort requests desc | limit 20
```

**Data egress per user**:
```
filter userId != '' and userId != 'anonymous'
| stats sum(responseLength) as bytes by userId
| sort bytes desc
```

**Feature downloads by dataset**:
```
filter path like '/features/v1/collections/'
| stats count(*) as requests by path
| sort requests desc
```

**Job failures by dataset**:
```
filter status = 'failed'
| stats count(*) as failures by dataset_id
| sort failures desc
```

## Runbook — common failures

### Service won't start

Check container service logs and event history. The most common causes:

1. Image not present — verify the image tag is in the image registry.
2. Task role permissions — verify the task IAM role can reach the key-value store and object storage.
3. Resource starvation — check whether the container cluster has capacity.
4. Health check failing — confirm the service is binding to the expected port and responding to the health endpoint.

### Pipeline job stuck in `pending`

The job has been created but the workflow has not started:

1. Check the dataset's `pipeline_status` — if another job is running, the new job is `queued`, not `pending`.
2. Check the workflow engine's execution history for the dataset — if no execution exists, the editing API's call to start the workflow may have failed silently.
3. Inspect the editing API logs for the corresponding job ID.
4. If genuinely stuck, manually invoke the workflow with the job's payload; mark the original job `failed` if duplicate is unsafe.

### Pipeline job stuck in `validating` or `generating`

The container task has been launched but has not completed:

1. List running container tasks for the validation or generation task definition.
2. Tail the task's logs to see where it is.
3. If the task has been running longer than the timeout, mark it failed via the failure handler.
4. If the task is making progress (logs continue), let it complete; check whether the workflow engine's per-task timeout is appropriately set.

### Dead-letter queue has messages

Messages in the validation DLQ indicate uploads that failed to be parsed and never started a workflow execution:

1. Inspect the message bodies — they contain the original storage event.
2. Identify the offending object in `landing/`.
3. Determine the cause (corrupt file, unexpected format, missing job record).
4. If the upload was legitimate, manually trigger the workflow with the correct payload.
5. Delete the DLQ messages once handled.

### Authoriser returning 401 unexpectedly

Check, in order:
1. Was the token issued by a trusted issuer? The trusted-issuers list is a deployment parameter.
2. Has the token expired?
3. Has the user's policy been recently changed? Cache TTL is up to 5 minutes; wait or invalidate.
4. Is the user's IdP group recognised by the ceiling table? An unknown group results in a denied request.
5. For API keys: is the key still `active` in the keys table?

### CDN returning stale tiles after a promotion

Either:
- The CDN invalidation in the promotion function did not complete; check the function logs.
- The tile server cache has not picked up the new ETag; restart the affected task or wait for the cache TTL.

### Cognito (or other IdP) user cannot sign in

For Cognito specifically:
1. Verify the user exists in the user pool.
2. Verify the user is `CONFIRMED` (not still `FORCE_CHANGE_PASSWORD` if invited).
3. Check the app client's allowed auth flows.

For other IdPs, the relevant checks are IdP-specific and outside the platform's control.

### Key-value store throttling

Either:
- A pathological access pattern (a hot partition); inspect the most-accessed partitions and consider splitting the workload.
- A sudden traffic spike beyond on-demand capacity; check the cloud's provisioned/on-demand setting.
- Cascading retries from a transient cloud-side issue; back off and retry.

## Scheduled maintenance

| Job | Cadence | Purpose |
|---|---|---|
| Dataset sync | Every 15 minutes | Reconcile registry with object storage |
| History vacuum | Daily | Compact per-job history into monthly archives |
| Event log compactor | Daily | Compact per-job events into monthly archives |
| Authoriser cache flush | None scheduled (TTL-driven) | Permissions propagate within minutes |

## Storage cost management

The single S3 bucket carries an **S3 Lifecycle policy** that transitions objects to **S3 Intelligent-Tiering** after 30 days. Recommended additional rules (also documented in [04 Data Layout](04_DATA_LAYOUT.md)):

- `landing/` — delete after job completion (handled by promotion Lambda; lifecycle rule as backstop after 7 days).
- `pmtiles/staging/` — delete after promotion (handled by promotion Lambda; lifecycle rule after 1 day).
- `drafts/` — delete after **90 days** regardless of session status. This governs the *content files* (delta and diff PMTiles, validation results) in S3. It is distinct from the **DynamoDB TTL** on the `edit-sessions` table, which expires the *session record* after one month of inactivity (non-terminal) or six months (terminal). The two mechanisms can run on different schedules without coordination — a session whose drafts content has been lifecycle-deleted can still be inspected via its DynamoDB record and re-generated if needed.
- Old `history/` archives — transition to **S3 Glacier Deep Archive** after one year for datasets with long retention requirements.

## Disaster recovery

### Recovery point objectives

| Resource | RPO |
|---|---|
| S3 (Versioning enabled) | 0 — object versioning preserves prior states |
| DynamoDB (PITR enabled) | 5 minutes (DynamoDB Point-In-Time Recovery resolution) |
| Cognito User Pool / external IdP | Provider-dependent |

### Recovery time objectives

| Scenario | RTO |
|---|---|
| Loss of a single service | Minutes — redeploy from IaC |
| Loss of the entire deployment | Hours — re-bootstrap from IaC; data is intact in object storage and the key-value store |
| Loss of an entire cloud region | Hours plus data restore — requires cross-region replication of object storage and key-value store |

### Tested DR

DR drills should exercise:
1. Re-deploying the IaC into a clean account against an existing data store. The expectation is that the platform is fully operational after the deployment completes.
2. Restoring the key-value store to a point in time and verifying authorisation policies and dataset registries are intact.
3. For high-availability deployments: failing over to a secondary region (if cross-region replication is configured).

The platform's design — stateless services, data in durable storage — makes the deployment-side of DR a normal redeploy. The data side relies on the durability and recoverability of the chosen object storage and key-value store, both of which offer multi-AZ durability by default.

## Capacity planning

Two dimensions to plan:

**Read traffic** is dominated by tile requests. CDN cache hit rate is the leading indicator: at high hit rates, backend load is decoupled from request volume. Capacity for the vector and raster tile servers should be planned for the unique tile rate (cache-miss rate × request rate), not the total request rate.

**Edit traffic** is dominated by workflow executions. Validation and generation tasks scale per execution; the limiting factor is concurrent workflow executions and container cluster capacity. Plan for peak concurrent edit submissions across all datasets.

The authoriser and the function-runtime services scale per request; their cost is proportional to request count, with negligible per-instance overhead.

## Cost shape

In `off` mode, baseline cost approaches the storage and registry minimums. Storage cost is proportional to data volume; key-value store on-demand costs are proportional to request count; the CDN charges for transfer.

In `minimal` mode, baseline cost adds the always-running container service tasks (one per service group's services). For a deployment with vector tiles, query layer, and editing enabled, this is a small number of tasks at modest sizing.

In `performance` mode, baseline cost adds the pre-warmed task count at the larger CPU/memory allocations. This is the highest steady-state cost.

A meaningful cost optimisation, especially in `off` and `minimal` modes, is removing NAT gateways (where used) and replacing them with private endpoints to the cloud's managed services (key-value store, object storage, container registry). The platform requires no outbound internet egress for its read or write paths; running private-only is feasible.

## Bootstrap

A fresh deployment requires a one-time bootstrap to create the first administrator:

1. Deploy the authoriser stack and the editing-pipeline stack.
2. Run a bootstrap script that:
   - Creates the first user in the IdP.
   - Maps that user's IdP group to a ceiling with the `platform_admin` role.
   - Creates a platform-admins group and adds the user to it.
3. The user can now sign in and manage everything else through the admin REST API.

After bootstrap, no further direct writes to the key-value store should be needed; the admin API covers all operations.
