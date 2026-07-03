# CHANGELOG

## 1.0.5 - Target-relative Rejet radius

- Corrected Rejet's `3/2` geometry from source-relative displacement to final distance from the targeted pillar.
- Added the reported adjacent yellow-pillar regression: one Rejet use plus the outer white glyph at radius three leaves yellow charges unchanged (`2 - 1 + 1 = 2`).
- Distinguished a legal zero-displacement cast from the actual displacement required before ending a round.

## 1.0.4 - Charge-conserving safe turns

- Enforced at least one movement spell per round; standing still is never a terminal candidate.
- Made projected black-pillar collisions and direct black effects hard exclusions instead of adverse fallback recommendations.
- Ranked black-safe turns by fewest casts first; white glyphs and next-turn charge resilience only break ties between equally short sequences.
- Kept moved endings without any glyph collision legal.
- Added a 14-round strategy regression proving one mandatory safe cast per round without negative or over-cap charges.

## 1.0.3 - Exact Rejet movement

- Made Rejet illegal when any pillar, obstacle or arena edge blocks its complete movement path.
- Split Rejet's final target-relative radius into three cardinal cells and two diagonal cells.
- Clarified charge output as current charges versus the projected next-turn charges after casts and glyph recharges.
- Added a 14-round model check covering every reachable charge value, caps, zero charges and single-commit round transitions.

## 1.0.2 - Black-driven glyph phases

- Selected the legal glyph phase from the more reliable black glyph observations.
- Derived the exact white-glyph positions from that phase instead of promoting noisy white-looking floor patches.
- Added a regression proving that ten spurious white candidates cannot expand the phase-defined set of eight white glyphs.

## 1.0.0 — Zero-input end-user flow

- Decoupled solver readiness and tactical authority from fixture matching.
- Added the seven product solution statuses and preserved concrete actions for provisional results.
- Combined screenshot recognition, deterministic solving, fight transition staging, and overlay rendering in the upload response.
- Added 12-AP and numeric charge defaults/continuation without player input.
- Replaced the standard review workbench with a paste-first numbered recommendation and solution overlay; diagnostics moved to `/?debug=1`.
- Added neutral-background, LAB/saturation, gradient, structural reference-patch, occlusion, and global-phase glyph evidence.
- Added independent per-cell pillar-completeness cross-check metadata.
- Added bounded glyph hypotheses and tactical-invariance classification.
- Added exact dominance pruning to the production solver path while retaining full diagnostic enumeration in fixture/property mode.
- Added exact four-start gold annotations and zero-input JSON/Markdown reports.
- Confirmed R-028 as direct observation, matching the accepted multi-cast mechanics and tests.
- Validation remains single-session regression, not independent beta evidence; four requested starts and the original individual glyph PNG bytes are absent.

## 1.0.1 — Stateful fight and glyph stabilisation

- Corrected the mislabeled blue-use training frame from round 1 to round 2 and recorded the eight-round sequence with original hashes, dimensions, casts and player continuity.
- Fixed the production contract at one screenshot at the start of each round; paired end frames remain training-only evidence.
- Added stateful fight resources: round 1 starts at two charges, solver output stages next charges, and the following screenshot commits them only after player-position reconciliation.
- Added the observed round-8 transition from `2/3/2/2` through one Attrait cast and one yellow white hit to `2/3/3/1`.
- Replaced fixture annotation overrides with a two-stage production classifier: user-calibrated black/white cell appearance first, four-phase geometry second.
- Kept full-resolution normalised uploads for recognition; the lossy 1280px preview no longer makes nested arena screenshots fail registration.
- Added real-pixel, sparse-reference and nested-page upload regressions, including one-visible-black plus one-visible-white phase recovery.
- Verified identical complete glyph sets in each start/end pair across all eight supplied rounds and the reported 26-pillar screenshot.
- Kept pillar completeness review-gated because three start frames still miss one strongly illuminated edge pillar compared with their training end frame.

## 1.0.0 — Verified gameplay-rule repair

- Replaced the hypothesis profile with the binding DofusPourLesNoobs/observed profile: 12 AP, 1 AP/cast, 2 initial charges, maximum 4 and immediate 1-charge cost.
- Implemented stacked end-of-turn matching recharge with the normative formula and same-turn zero-to-available recovery.
- Locked Indécision to four free orthogonal neighbours and rejected all diagonals.
- Implemented any-colour exact-range-2 Reflet, blocker-aware movement, truncating Rejet and stop-before-pillar Attrait.
- Fixed player-facing names to Indécision, Reflet, Rejet and Attrait.
- Retained the supplied spell-bar image byte-for-byte and added automatic availability regression recognition.
- Changed the normal web flow to Ctrl+V and automatic calculation; manual controls are Debug-only.
- Updated the rule catalogue, decisions, status and automated Unit/Property/Solver/Vision coverage.

## 0.9.0 — Clean-start and player-flow release repair

- Reproduced and removed the nondeterministic Web `npm install` build path.
- Pinned Node 24.17.0 by OCI digest and npm 11.18.0; switched dependency installation to lockfile-only `npm ci`.
- Excluded Git, runtime data, archives, caches, virtual environments, `node_modules`, and test output from Docker context.
- Removed the improvised `Dockerfile.bak` and added Web health checking.
- Removed synthetic fallback player coordinates; unresolved detection now stays unresolved.
- Added screenshot overlays for the player, every typed pillar, doubtful pillars, and all central-pattern cells.
- Replaced player/pattern coordinate entry with direct screenshot clicks.
- Added explicit action-budget and three-state spell controls with visible confirmation.
- Hid internal codes in standard mode and added a separate Debug view.
- Added the five-item readiness checklist and hard solver-button gating.
- Added API regression coverage and a complete real-fixture Playwright upload-to-recommendation test.
- Verified 36 API tests, Compose health, two browser tests, shutdown, and restart.

## 0.9.0 — Boundary Refinement Addendum

- Split the stable interior grid from a separate per-cell boundary-validation layer.
- Removed the blanket `confidence=1.0` promotion of `boundaryUnverified` cells.
- Rechecked all 50 boundary cells against visible empty-map surface, hidden-cell provenance and parity/geometric consistency.
- Retained 338 coordinates only as a provisional working mask.
- Classified 43 boundary cells as confirmed, 0 as accepted inference and 7 as unresolved.
- Added per-cell expected/plausible centres, pixel/cell deviation, regional line-fit provenance and review reasons.
- Added cyan/red/lime/orange/magenta debug overlays plus eight named edge zoom crops.
- Added `VALIDATION/edge-review-report.json` and a non-empty seven-cell review list.
- Changed runtime loading so unresolved boundary cells are not silently exposed as walkable.
- Updated schemas, deterministic generation and validation gates for the two-evidence rule.

## 0.9.0 — Phase 7B

- Promoted the fixed arena footprint from a 338-cell draft candidate envelope to a canonical user-verified coordinate mask.
- Retained the empty arena image and user hidden-cell annotation as versioned evidence.
- Confirmed 338 unique cells through direct count, `x + y` rows and `x - y` rows.
- Derived 50 boundary cells, 104 exposed boundary edges and zero interior holes.
- Fixed logical floor parity as `(x + y) mod 2` and added complete neighbour-invariant tests.
- Added stable IDs, reference centres, exact polygons, reciprocal neighbours, authority and provenance for every cell.
- Added deterministic JSON, CSV, SVG and PNG arena generation; removed image generation from the geometry path.
- Added versioned canonical cells/boundary JSON Schemas and published them through the v0.9.0 contract manifest.
- Added public screenshot-to-arena registration functions and migrated runtime cell loading to the canonical mask.
- Generated validation overlays for the canonical reference, empty arena, hidden-cell annotation and four real combat screenshots.
- Bounded OpenCV to four threads; measured registration/projection/sampling p95 at 169.442/0.047/0.096 ms in the shared warm container.
- Kept gameplay rules, projection anchor, `MODEL-001`, locked-corpus validation and automatic confirmation gates open.

## 0.8.0 — Phase 7A

- Retained four new real combat screenshots byte-for-byte as versioned fixtures.
- Documented dimensions, hashes, provenance, arena/UI regions and unknown upload-scaling status.
- Added conservative logical player, pillar, glyph, resource and progress annotations.
- Implemented cached ORB/RANSAC arena registration and canonical affine warp.
- Implemented known-cell pillar classification and controlled-player detection.
- Added registered fixture signatures for review-only glyph proposals and synthetic robustness tests.
- Added browser-local preview plus Web Worker decode/downscale/progress states.
- Added registered overlay projection for arbitrary supported source resolutions.
- Added per-stage ingest, recognition and solver instrumentation.
- Replaced the fixed action-budget value with an explicit unknown/numeric control.
- Added tests for all five real screenshots, three target resolutions, JPEG, borders, crops, worker syntax, OCR exclusion, solver pixel isolation and fallback safety.
- Increased Python suite to 19 passing tests; TypeScript/build/npm audit pass.
- Measured warm-cache registration p95 298.714 ms, baseline recognition p95 757.498 ms, server screenshot-to-state p95 1,479.611 ms and solver p95 3.220 ms on shared container hardware.
- Kept `MODEL-001`, manual correction and all unresolved mechanics gates active.
- Handed the project to Phase 7B evidence, browser E2E and locked-corpus validation.

## 0.7.0 — Phase 6

- Added executable Next.js/FastAPI repository and Docker Compose packaging.
- Implemented token-protected ephemeral analysis sessions with optimistic concurrency and idempotency.
- Implemented secure image normalisation, thumbnailing and protected assets.
- Implemented deterministic solver, conditional graph, capacity separation and annotated output.
- Executed all 26 Phase-3 fixtures with explicit oracle-scope handling.
- Implemented command-based manual correction, audit, undo/redo and recommendation invalidation.
- Added French-first minimal upload/review/solve web workbench.
- Added conservative reference-proposal baseline and blank manual fallback.
- Kept automatic critical confirmation disabled under `MODEL-001`.
- Added runtime manifest, generated contract inventory, SPDX SBOM and performance report.
- Added 7 passing Python tests, passing TypeScript/build checks and zero-vulnerability npm audit.
- Added implementation report, runbook, known limitations and Phase-7 defect backlog.
- Handed the project to Phase 7 — Pre-Live Validation.

## 0.6.0 — Phase 5

- Froze two-process pre-live repository, package ownership and runtime baseline.
- Added analysis lifecycle, optimistic concurrency, idempotency and capacity semantics.
- Added exact HTTP endpoint, editor-command, event and error contracts.
- Added complete route/component/state/breakpoint/keyboard inventory.
- Added original overlay grammar and annotated-output rules.
- Added French-first production copy with German/English parity policy.
- Added ephemeral retention, optional evidence consent and deletion contract.
- Added reproducible local/container commands and production-impossible fixture mode.
- Added complete test matrix, security scenarios and performance budgets.
- Added preview deployment, observability, rate-limit and recovery design.
- Added dependency-ordered 19-item Phase-6 implementation backlog.
- Added five Phase-5 schemas, examples and machine-readable catalogues.
- Added Phase-5 cumulative validator and Phase-6 chat brief.


## 0.5.0 — Phase 4

- Added screenshot ingest and arena-presence rejection contract.
- Added affine logical-grid registration with explicit residual and ambiguity gates.
- Split board registration from lower-UI registration.
- Added player, pillar, pillar-completeness, glyph, action-budget, spell and progress extraction contracts.
- Added `VisualObservation`, `RecognitionResult` and annotation schemas.
- Extended `TurnState` with calibration, arena-presence, multiplayer, pillar-set, glyph, budget and visual-provenance fields.
- Added weighted confidence formula, hard caps and conflict classes.
- Added automatic-confirmation validation lock.
- Added exact visual field-to-solver gating map.
- Added confidence/correction UX and multilingual failure-copy catalogue.
- Added privacy, consent, annotation, split and leakage-prevention protocol.
- Added locked-corpus evaluation targets and zero-tolerance critical false-safe definition.
- Added 20 visual contract fixtures and Phase-4 regression validation.
- Added Phase-5 technical/visual specification brief.

## 0.4.0 — Phase 3

- Added exact solver preflight and action-budget source precedence.
- Added deterministic enumeration contracts for Indécision, Reflet, Rejet and Attrait.
- Added explicit target-pillar type, range metric, alignment, line-of-sight, path, edge and occupancy switches.
- Added availability-only and numeric resource semantics.
- Added separate definite and conditional action graphs.
- Added normative transition-trace event order.
- Added exact status precedence and dependency-reachability rules.
- Added lexicographic candidate ranking and canonical sequence keys.
- Replaced unstable pillar-based future mobility with verified local terrain degree.
- Added rule IDs R-039 through R-054 for previously hidden uncertainties.
- Added legal-action, resolution-trace, solver-request and solver-fixture schemas.
- Added machine-readable ranking, status and dependency policies.
- Added 26 structured contract fixtures and 30 property-test requirements.
- Added Phase-4 recognition/confidence brief.

## 0.3.0 — Phase 2

- Corrected the retained screenshot dimensions from 1527 × 991 to 1951 × 1267.
- Fixed logical axis orientation and added the provisional single-reference transform.
- Added a 338-cell draft arena model with five cell-authority classes.
- Added explicit occlusion regions and conservative boundary handling.
- Added no permanent blocked cells without direct proof.
- Added a provisional projection anchor and solver gate.
- Manually encoded the reference screenshot with 27 pillars, player and glyph cells.
- Added manual state-editor interaction and audit specification.
- Added validation/error catalogue.
- Added `arena-model.schema.json`.
- Added `manual-editor-session.schema.json`.
- Added `anchorCell` and `anchorConfirmed` to the turn-state schema.
- Added calibration anchors, cell-classification CSV and annotated diagrams.
- Added Phase-3 solver/test-oracle brief.

## 0.2.0 — Phase 1

- Replaced the Phase-1 Codex workflow with a ChatGPT-led pre-live delivery strategy.
- Added formal domain terminology and coordinate conventions.
- Added rule authority levels and solver gating policy.
- Added rule catalogue with stable rule IDs.
- Expanded the open verification register from V-001–V-005 to V-001–V-010.
- Added formal movement contracts and unresolved-geometry variants.
- Added end-of-turn resolution ordering specification.
- Added gameplay evidence capture protocol.
- Added `rules-profile.schema.json`.
- Added `verification-observation.schema.json`.
- Upgraded turn-state and recommendation schemas to 0.2.0.
- Added pre-live delivery stages and a strict Codex entry gate.

## 0.1.0 — Phase 0

- Created project baseline.
- Added verified mechanics summary.
- Added open verification register V-001 through V-005.
- Added CV architecture.
- Added deterministic solver architecture.
- Added confidence and fail-safe policy.
- Added phase roadmap and delivery protocol.
- Added initial JSON schemas.
