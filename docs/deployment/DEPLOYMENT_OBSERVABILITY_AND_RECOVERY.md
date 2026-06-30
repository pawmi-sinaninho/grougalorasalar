# DEPLOYMENT, OBSERVABILITY & RECOVERY — Phase 5

## 1. Topologies

### Local development

Two containers through Compose: `web` and `api`. Bind-mounted source is allowed only in development.

### Preview / closed testing

- one web container;
- one API container/replica;
- private ephemeral volume;
- reverse proxy/TLS;
- no external evidence store unless the consent workflow is explicitly enabled;
- deployment is disposable and recreated from manifests.

The single API replica is deliberate because the Phase-6 in-process job registry is not distributed. Horizontal scaling is forbidden until a durable queue/session store is implemented and tested.

### Future production hardening

Phase 9 may split worker execution and add durable session/rate-limit infrastructure. That is not a Phase-6 prerequisite and may not alter contract semantics.

## 2. Build and release

- multi-stage containers, non-root runtime user;
- read-only root filesystem where library constraints permit;
- dependency and image vulnerability scan;
- SBOM generated per image;
- schema/data/model manifest signed or checksum-pinned;
- release identifier exposed by `/meta`;
- database migration step absent until a persistent store is introduced;
- rollback uses the prior immutable image pair and its matching manifest.

## 3. Health checks

- liveness: process responds;
- readiness: contracts, arena/rule data, templates/models and writable ephemeral directory verified;
- startup: cleanup stale temp files before accepting traffic;
- degraded readiness is false when solver or deletion subsystem cannot operate safely.

## 4. Structured logs

Required fields:

- timestamp, level, service, release;
- request ID, opaque analysis ID suffix or one-way short correlation token;
- event name, duration, outcome and stable reason codes;
- model/policy/rules profile identifiers where relevant.

Forbidden:

- image bytes, filenames, hashes, access tokens;
- full request/response bodies;
- OCR text, logical board state or action sequence by default;
- IP address in application logs;
- stack traces in user responses.

## 5. Metrics

- request count/error count/latency by endpoint and status family;
- active analyses and queue depth;
- ingest/registration/recognition/solver duration histograms;
- review/reject/ready gate counts by reason code;
- solver domain outcome counts;
- deletion and expiry counts;
- critical false-safe is an offline evaluation metric, not inferred from production clicks.

Metrics labels may not contain analysis IDs, filenames, coordinates or unbounded reason text.

## 6. Alerts for preview

- readiness failing for 5 minutes;
- API 5xx >5% over 10 minutes with at least 20 requests;
- recognition hard-timeout >10% over 15 minutes;
- ephemeral disk >70% warning, >85% critical;
- cleanup job failure twice consecutively;
- delete operation failures >0;
- manifest mismatch at startup is a hard deployment failure, not an alert-only condition.

## 7. Rate limits

Preview defaults:

- 10 analysis creations per 10 minutes per transient client key;
- 20 uploads per hour;
- three concurrent analyses;
- 30 solver calls per analysis;
- asset download bandwidth cap.

Local development has no rate limits. Limits return a retryable API error with `Retry-After`; they never alter an existing recommendation.

## 8. Recovery

- process crash: ephemeral sessions may be lost in Phase 6; UI reports expiry/technical loss honestly;
- recognition timeout: preserve uploaded normalised image and manual-editor route where safe;
- solver timeout: preserve confirmed state, return capacity status, no partial sequence;
- disk pressure: stop accepting uploads before deletion becomes unreliable;
- manifest mismatch: do not start;
- deployment rollback: session loss is accepted for pre-live and stated in release notes.

## 9. Backup policy

Ephemeral analysis data is never backed up. Versioned source, schemas, fixtures, manifests and consented evidence metadata have separate backups. A backup must not accidentally convert ephemeral screenshots into retained data.
