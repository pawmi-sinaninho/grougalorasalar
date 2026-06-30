# PHASE 6 IMPLEMENTATION BACKLOG — Dependency Ordered

## Execution rule

Implement in the listed dependency waves. A wave closes only when its acceptance criteria and tests pass. Baseline recognition is deliberately after the manual deterministic vertical slice.

## Wave A — Repository and contracts

### P6-001 Repository scaffold

Create the frozen layout, Docker Compose, runtime guards, root commands and CI skeleton.

Acceptance:

- `docker compose up --build` starts web/API;
- `/health/ready` verifies current manifests;
- wrong Node/Python version fails clearly;
- no domain logic duplicated in app bootstrap.

### P6-002 Contract toolchain

Load all JSON Schemas, generate TypeScript/Pydantic bindings, publish schema manifest and implement drift checks.

Acceptance:

- every example validates;
- generated files are reproducible;
- Phase-3/4 validators remain green;
- OpenAPI references the same enum/status values.

## Wave B — Deterministic core

### P6-003 Arena and rules loaders

Typed immutable loaders for arena model, rule catalogue, profile and policies.

Acceptance:

- checksum/version mismatch blocks readiness;
- production cannot load specification-test profiles.

### P6-004 Solver implementation

Implement preflight, enumeration, transition, ranking, traces and capacity guards from Phase 3.

Acceptance:

- all 26 fixtures match exact canonical expectations;
- all property requirements implemented;
- timeout/node cap returns capacity, not no-safe.

## Wave C — Session API and storage

### P6-005 Analysis-session state machine

Implement lifecycle, optimistic concurrency, idempotency and access tokens.

Acceptance:

- invalid transitions rejected atomically;
- state version monotonic;
- duplicated idempotent requests return same result.

### P6-006 Ephemeral storage and deletion

Implement assets/state TTL, immediate deletion, cleanup and consent isolation.

Acceptance:

- privacy tests prove no backup/log copy;
- deletion during running work prevents late persistence;
- expired sessions fully disappear.

### P6-007 Secure upload and normalisation

Implement allowlist decoding, EXIF handling, dimension/decompression guards and safe assets.

Acceptance:

- malformed, animated, SVG, MIME-mismatch and oversized inputs rejected;
- original removed after normalisation under default mode.

## Wave D — Manual-first vertical slice

### P6-008 Overlay renderer and workbench

Implement screenshot viewport, logical grid and visual-state markers from the overlay contract.

Acceptance:

- alignment stable across zoom/DPR;
- keyboard focus and non-colour signals pass tests.

### P6-009 Manual editor command system

Implement all commands, invariants, audit, undo/redo and validation summary.

Acceptance:

- reference screenshot can be reconstructed;
- object IDs stable through moves/reclassification;
- post-solve edits invalidate old result.

### P6-010 Solve API and recommendation UI

Connect confirmed TurnState to solver and render action sequence, expected outcome, assumptions and alternatives.

Acceptance:

- full fixture→review→solve→overlay flow works;
- progress unknown removes terminal claim;
- domain blockers are not technical errors.

## Wave E — Baseline recognition

### P6-011 Ingest and registration

Implement arena presence, affine candidates, residual scoring and manual-anchor fallback.

Acceptance:

- all Phase-4 visual contract fixtures reach expected gates;
- no automatic critical confirmation while unvalidated.

### P6-012 Board extraction baseline

Implement player, pillar instance/type, completeness and glyph extraction with observation provenance.

Acceptance:

- every field has alternatives, cross-check and reason codes;
- missing/ambiguous data routes to correction rather than defaults.

### P6-013 Resource and progress extraction baseline

Implement UI-region registration, action budget, spell states and optional progress extraction.

Acceptance:

- missing lower UI supports explicit manual entry;
- progress remains terminal-only;
- slot identity does not depend solely on horizontal order.

### P6-014 Confidence and gate integration

Implement component formula, caps, conflicts, confirmation semantics and aggregate minimum.

Acceptance:

- policy JSON controls thresholds;
- confirmation never mutates confidence;
- `MODEL-001` remains active before Phase 7.

## Wave F — Product completion

### P6-015 French-first copy and locale parity

Implement all shipping keys in FR/DE/EN with placeholder tests.

### P6-016 Accessibility and responsive boundaries

Implement keyboard workflow, screen-reader labels, reduced motion and mobile read-only boundary.

### P6-017 Fixture/diagnostic mode

Implement fixture browser, traces, forced states and root fixture command; impossible in production.

### P6-018 Test, performance and security gate

Complete contract/unit/property/integration/E2E/visual/privacy/security/performance suites and reports.

### P6-019 Preview packaging and runbook

Produce immutable containers, SBOM, manifests, startup/rollback/deletion runbook and known-limitations report.

## Phase-6 exit gate

Phase 6 is complete only when:

- a fresh machine starts the application reproducibly;
- a user can upload a screenshot, manually correct every field, invoke the deterministic solver and receive an annotated exact sequence;
- baseline recognition proposes values but cannot silently confirm critical fields;
- all existing and new validators pass;
- deletion and TTL are demonstrated;
- measured test/performance report and defect backlog exist;
- Codex has still not been used as the foundation.
