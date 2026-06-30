# PRE-LIVE TECHNICAL BLUEPRINT — Phase 5

## 1. Purpose

Freeze the implementation boundary for the first functioning local/preview build. This document assigns one owner to every state transition while preserving the prior separation between pixel evidence, manual correction, mechanics and tactical solving.

## 2. Runtime baseline

Verified on 2026-06-28 and frozen for Phase 6:

| Layer | Baseline | Freeze rule |
|---|---|---|
| Web runtime | Node.js 24 LTS; development image `24.17.0` | exact Docker digest and `package-lock.json` committed in Phase 6 |
| Web framework | Next.js 16.x App Router, React 19.x, TypeScript 5.x | exact package versions come from the first reviewed lockfile |
| Python runtime | CPython `3.13.14` | exact patch version in `.python-version` and Docker image |
| API framework | FastAPI `0.138.1`, Pydantic 2.x, Uvicorn | exact transitive set in a hash-locked requirements file |
| Computer vision | OpenCV Python 4.x and NumPy 2.x | install only from reviewed binary wheels; exact versions locked |
| Local orchestration | Docker Compose specification | `docker compose`, never legacy `docker-compose` |
| Contracts | JSON Schema draft 2020-12 | schema files remain the cross-runtime authority |

The existing Phase-3 and Phase-4 domain schemas remain at schema version `0.5.0` because Phase 5 does not alter their payload meaning. New orchestration contracts use `0.6.0`.

## 3. Repository layout

```text
apps/
  web/                         Next.js UI and browser-side canvas/SVG rendering
services/
  api/                         FastAPI HTTP boundary and analysis-session orchestration
packages/
  contracts/                   immutable JSON Schemas, generated TS/Python bindings
  ui/                          reusable accessible UI primitives and visual tokens
  fixtures/                    copied/validated solver and visual fixtures
python/
  grougal_domain/              shared Pydantic/domain adapters; no pixels
  grougal_solver/              deterministic Phase-3 implementation
  grougal_vision/              ingest, registration and extraction pipeline
  grougal_storage/             ephemeral-session and consented-evidence adapters
scripts/                       validation, fixture loading, manifest and deletion checks
tests/
  contract/ unit/ property/ integration/ e2e/ visual/ privacy/ performance/
docs/ data/ schemas/ examples/ assets/
compose.yaml
package.json
package-lock.json
pyproject.toml
requirements.lock
```

## 4. Ownership map

| Concern | Sole owner | Forbidden responsibility |
|---|---|---|
| File validation, EXIF normalisation, decompression limits | `grougal_vision.ingest` | tactical or rule decisions |
| Board/UI registration and observations | `grougal_vision` | auto-promoting unvalidated fields |
| Session state machine and API errors | `services/api` | changing detector confidence or rules |
| Manual edits, confirmations, undo/redo | `apps/web` command UI plus API command handler | direct database mutation outside commands |
| Arena mask and projection metadata | `packages/contracts` + versioned `data/arena` | screenshot-specific transforms |
| Rules profile and deterministic search | `grougal_solver` | reading image bytes or pixel positions |
| Overlay layout document | `services/api` projection adapter | recomputing tactical decisions |
| Translations | `data/content` loaded by `apps/web` | runtime machine translation |
| Retention/deletion | `grougal_storage` | using consent as a tactical field |
| Metrics/logging | API middleware and explicit adapters | image bytes, raw OCR text or full state payloads in logs |

## 5. Deployment units

Phase 6 contains two processes, not a microservice mesh:

1. `web`: Next.js server on port 3000;
2. `api`: FastAPI process on port 8000, importing the vision and solver Python packages in-process.

The in-process Python package boundary is mandatory and testable. Vision may emit only `RecognitionResult`; solver may accept only schema-valid logical objects. A future worker/queue split is allowed only after Phase-7 measurements show a throughput or isolation need.

## 6. Analysis lifecycle

```text
created
  -> uploading
  -> ingesting
  -> recognition_running
  -> review_required | rejected | failed
review_required
  -> review_required after each command
  -> ready_for_solver only when visual gate passes
ready_for_solver
  -> solving
  -> solved | confirmation_required | blocked_unverified_rule
     | no_safe_solution | invalid_state | capacity_exceeded
any non-terminal state
  -> deleted | expired
```

Rules:

- lifecycle transitions occur only through the API service;
- every transition has a `stateVersion` monotonic integer;
- write commands require `expectedStateVersion` to prevent lost updates;
- a correction after solving invalidates recommendation and overlay atomically;
- `failed` is technical; solver statuses are not converted into HTTP 500 errors;
- `capacity_exceeded` is a technical search guard, never `no_safe_solution`.

## 7. Dependency direction

```text
web -> generated TypeScript contracts -> HTTP API
api -> generated Python contracts
api -> vision / solver / storage interfaces
vision -> arena data + observation schemas
solver -> arena data + rules + solver schemas
vision -X-> solver internals
solver -X-> image storage
storage -X-> tactical logic
```

Circular imports and direct web access to Python fixture files are forbidden.

## 8. Configuration

All configuration is explicit and validated at startup:

- `GS_ENV=development|test|preview|production`;
- `GS_FIXTURE_MODE=0|1`;
- `GS_SESSION_TTL_MINUTES=60`;
- `GS_MAX_UPLOAD_BYTES=26214400`;
- `GS_MAX_DECODED_PIXELS=33200000`;
- `GS_MAX_CONCURRENT_ANALYSES=3` per client key in preview;
- `GS_SOLVER_MAX_NODES=100000`;
- `GS_SOLVER_TIMEOUT_MS=2000`;
- `GS_EVIDENCE_STORE_ENABLED=0|1`;
- `GS_ALLOWED_ORIGINS` explicit outside local development.

Production startup fails when fixture mode is enabled, secrets are defaults, schema manifests mismatch, or automatic confirmation is enabled without a signed Phase-7 validation record.

## 9. Source basis

- Node.js official release table: Node 24 is LTS and 24.17.0 was the current LTS download on 2026-06-28.
- Next.js official version-16 documentation: Node >=20.9 and TypeScript >=5.1.
- Python official releases: Python 3.13.14 was a current stable Windows-capable release on 2026-06-28.
- FastAPI official release notes: 0.138.1 released 2026-06-25.
- Docker official Compose documentation: use the current `docker compose` plugin/specification.
