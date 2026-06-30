# Phase 6 — Implementation Report

**Release:** 0.7.0  
**Date:** 2026-06-28  
**Result:** First pre-live implementation completed with a working manual deterministic vertical slice.

## 1. Implemented repository

The Phase-5 blueprint is now represented by an executable repository:

- `apps/web`: Next.js 16/React 19 review workbench;
- `services/api`: FastAPI analysis/session API;
- `python/grougal_solver`: explicit package boundary for deterministic solving;
- `python/grougal_vision`: explicit package boundary for recognition;
- `packages/contracts`: generated cross-runtime schema inventory;
- `runtime/sessions`: private ephemeral analysis storage;
- `scripts`: contract, runtime-manifest, SBOM and validation tooling.

The backend owns orchestration. Pixels are normalised by the ingest/recognition side and converted to logical state before they reach tactical enumeration.

## 2. Working vertical slice

The tested flow is:

1. create a token-protected analysis;
2. upload PNG/JPEG/WebP;
3. normalise the image and create a thumbnail;
4. produce unconfirmed logical proposals or an empty manual state;
5. correct/confirm player, pillar set, glyphs, action budget, spell states and anchor through versioned commands;
6. run the deterministic solver;
7. return an ordered recommendation and an annotated PNG;
8. reject stale state mutations;
9. delete the complete analysis directory.

The retained 1951 × 1267 reference image loads its Phase-2 manual encoding as proposals. The proposals remain `review_required`; their confidence values do not bypass `MODEL-001`.

## 3. Solver implementation

The Python solver implements:

- structural preflight;
- profile-controlled movement geometry;
- definite and conditional legal-action graphs;
- immediate resource cost and end-turn recharge handling;
- projected glyph/pillar collision tracing;
- stationary/direct-centre/race resolution;
- capacity protection at 100,000 nodes;
- deterministic ranking and canonical sequence keys;
- domain statuses distinct from technical capacity errors.

All 26 Phase-3 fixtures are executed. Their expected legal roots, conditional dependencies, terminal outcomes and listed recommendation sequences are checked. A subset with globally unambiguous status assertions is checked exactly.

## 4. Session and API implementation

Implemented `/api/v1` capabilities include:

- live/readiness/runtime metadata;
- analysis creation and token issuance;
- protected upload and retrieval;
- command-based editor mutations;
- optimistic state-version concurrency;
- command/idempotency deduplication;
- deterministic solve;
- protected normalised, thumbnail and annotated assets;
- idempotent deletion;
- development-only fixture and diagnostic routes.

The API stores only a SHA-256 token digest. Analysis responses and logs do not expose the digest or raw token. Protected responses use `no-store` and security headers.

## 5. Manual editor implementation

The current web workbench supports the complete logical flow through form controls:

- accept all current proposals as manually confirmed;
- confirm projection anchor and pillar-set completeness;
- enter action budget and spell availability;
- change the player cell;
- add pillars;
- paint black/white relative glyph offsets;
- solve and display ordered actions plus annotated output.

The API command layer additionally supports move/remove/reclassify, erase, undo and redo operations. Direct canvas manipulation and every field-specific control remain Phase-7 usability work.

## 6. Recognition baseline

This release intentionally does not claim a general detector:

- exact retained-reference dimensions: load the known manually encoded state as unconfirmed proposals;
- every other supported image: create a valid blank manual state and mark registration as required;
- automatic critical confirmation: always false;
- calibration status: `unvalidated`.

This is a safe baseline, not an accuracy result.

## 7. Frontend implementation

The Next.js production build contains a French-first single-page workbench. It exposes the tested upload/review/solve path and clearly states that critical detections are never automatically confirmed.

A dependency-free HTML fallback is served by FastAPI at `/` for API-only local inspection. It is not a replacement for the Next.js workbench.

## 8. Privacy implementation

Implemented controls:

- 60-minute idle expiry;
- six-hour hard expiry;
- private per-analysis directory;
- random bearer token with stored digest only;
- immediate recursive deletion;
- no screenshot history;
- no evidence/training copy in the default flow;
- filename excluded from persisted session state;
- image/state payloads absent from structured application output.

A process-local cleanup method exists. A production scheduler and crash/race validation remain hardening tasks.

## 9. Test results

Executed in this build environment:

- Python automated tests: **7 passed**;
- Phase-1–5 cumulative specification validation: passed after version-compatible update;
- TypeScript type check: passed;
- Next.js production build: passed;
- npm audit: **0 known vulnerabilities** after the locked PostCSS override;
- isolated Python `pip check`: no broken requirements;
- Phase-6 runtime/manifest/performance validator: passed.

Docker was not installed in the execution environment. Therefore `docker compose up --build` is specified and packaged, but the container startup itself was not executed here.

## 10. Measured engineering samples

Shared-container samples, not production benchmarks:

| Operation | p95 |
|---|---:|
| Solver fixture | 1.060 ms |
| Reference-image normalisation | 5,111.342 ms |
| Baseline recognition proposal | 1.322 ms |
| Session mutation | 5.487 ms |
| Session deletion | 0.567 ms |

The sampled operations fit the Phase-5 engineering budgets. Browser network time, container cold start, accessibility performance and production hardware are not represented.

## 11. Phase-6 conclusion

Phase 6 passes as the first pre-live implementation because the manual screenshot-to-recommendation lifecycle is executable, deterministic, testable and deletable without relying on unvalidated recognition.

It does not pass as an authoritative live solver. Phase 7 must obtain gameplay evidence, run a locked validation corpus, test the Docker/browser path and convert remaining UX/API shortcuts into measured release behaviour.
