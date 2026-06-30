# HTTP API & EVENT CONTRACTS — Phase 5

## 1. General rules

Base path: `/api/v1`. JSON uses UTF-8, camelCase and explicit schema versions. Image upload uses `multipart/form-data`. No endpoint accepts pixel coordinates for solver operations.

Every response includes:

- `X-Request-Id`;
- `Cache-Control: no-store` for analysis data;
- a schema-valid body;
- no raw exception text.

Mutation requests accept `Idempotency-Key` where creating a session, uploading or solving could be retried. Mutations to an existing analysis require `expectedStateVersion`.

## 2. Endpoint catalogue

### `GET /health/live`

Process liveness only. Returns 200 when the process event loop responds.

### `GET /health/ready`

Returns 200 only when schemas, arena model, rule catalogue, policies and required model/template files load and their manifest checksums match.

### `GET /meta`

Returns release version, schema manifest, runtime versions, model calibration status, fixture-mode flag and supported locales. It never returns filesystem paths or secrets.

### `POST /analyses`

Creates an ephemeral analysis session.

Request:

```json
{
  "schemaVersion": "0.6.0",
  "locale": "fr",
  "retentionConsent": "ephemeral_only",
  "qualityImprovementConsent": false
}
```

Response: `201 AnalysisSession` with opaque `analysisId`, `accessToken`, state `created`, expiry and upload limits.

### `POST /analyses/{analysisId}/image`

Multipart fields:

- `file`: PNG/JPEG/WebP;
- `expectedStateVersion`;
- optional `captureSessionId` when consent permits evidence grouping.

Response: `202 AnalysisSession`, state `ingesting` or `recognition_running`. The API never trusts filename, browser MIME or EXIF without decoding.

### `GET /analyses/{analysisId}`

Returns the current `AnalysisSession`, recognition summary, unresolved review items and recommendation summary. Image bytes are obtained from the protected asset endpoint, not embedded in JSON.

### `GET /analyses/{analysisId}/asset/{assetKind}`

Allowed kinds: `normalised`, `thumbnail`, `annotated`. Requires the analysis access token; no public URL; `Content-Disposition: inline`; `no-store`; short-lived response. `original` is not exposed after normalisation unless an explicit diagnostics build is used locally.

### `POST /analyses/{analysisId}/commands`

Applies one auditable editor command. Request validates against `editor-command.schema.json`.

Supported commands:

- `accept_detection`;
- `set_registration_anchors`;
- `set_player_cell`;
- `add_pillar`, `move_pillar`, `set_pillar_type`, `delete_pillar`;
- `set_pillar_set_complete`;
- `paint_glyph_cell`, `erase_glyph_cell`, `set_projection_anchor_confirmation`;
- `set_action_budget`, `set_spell_state`, `set_progress`;
- `resolve_conflict`, `undo`, `redo`.

The response contains the updated session and exact validation deltas. Commands are rejected atomically when state version, target ID, invariant or permission fails.

### `POST /analyses/{analysisId}/solve`

Request:

```json
{
  "schemaVersion": "0.6.0",
  "expectedStateVersion": 12,
  "mode": "authoritative",
  "confirmedSingleSourceRuleIds": [],
  "maxAlternatives": 2
}
```

Response:

- `200` with recommendation when completed within the request budget;
- `409` only for lifecycle/state-version conflicts;
- `422` only for structurally invalid API payloads;
- solver outcomes such as `blocked_unverified_rule` remain a 200 domain result.

### `GET /analyses/{analysisId}/overlay`

Returns `OverlayDocument` generated from the currently valid recognition/recommendation. An invalidated recommendation yields an overlay containing review markers but no action sequence.

### `DELETE /analyses/{analysisId}`

Deletes ephemeral assets, session data and any not-yet-exported evidence copy. Returns `204`. A repeated request is idempotent and also returns `204` when the signed token is valid.

### Development-only endpoints

`GET /fixtures`, `POST /fixtures/{fixtureId}/load`, and `GET /diagnostics/contracts` exist only when `GS_FIXTURE_MODE=1` and the request originates from loopback/test network. They are absent, not merely hidden, in preview/production routing.

## 3. Error envelope

All non-domain errors use `ApiError`:

```json
{
  "schemaVersion": "0.6.0",
  "error": {
    "code": "API-STATE-VERSION-CONFLICT",
    "httpStatus": 409,
    "messageKey": "errors.stateVersionConflict",
    "requestId": "req_...",
    "retryable": false,
    "fieldErrors": [],
    "details": {"currentStateVersion": 13}
  }
}
```

Stable code families:

- `API-AUTH-*` analysis-token failures;
- `API-FILE-*` transport/file handling;
- `API-STATE-*` lifecycle and optimistic concurrency;
- `API-CONTRACT-*` schema/manifest mismatch;
- `API-CAPACITY-*` timeout, queue or node cap;
- `API-INTERNAL-*` unexpected technical failure.

Gameplay/recognition reason codes remain in their existing domain catalogues.

## 4. Progress events

Phase 6 uses polling as the normative transport. The API may additionally expose Server-Sent Events at `/analyses/{id}/events`, but the product must work without SSE.

Event envelope:

```json
{
  "schemaVersion": "0.6.0",
  "eventId": "evt_...",
  "analysisId": "ana_...",
  "stateVersion": 4,
  "type": "recognition.completed",
  "occurredAt": "2026-06-28T10:00:00Z",
  "payload": {"gateStatus": "review_required"}
}
```

Events are hints. The client always re-fetches the current session and never derives authoritative state solely from event order.

## 5. Security and cache controls

- opaque IDs have at least 128 bits of entropy;
- analysis access token is separate from the ID and kept only in session storage;
- CORS is explicit;
- CSRF is mitigated by same-site cookies or bearer token plus origin checks;
- uploads are never served from the same executable path/domain without safe content headers;
- SVG uploads are unsupported;
- all analysis responses are `no-store`;
- request bodies and state payloads are excluded from access logs.
