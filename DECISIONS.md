# DECISIONS

## D-096 — The Web build is lockfile-only

Node 24.17.0 is fixed by image digest and npm 11.18.0 is asserted before `npm ci`. `npm install` is not a release build step.

## D-097 — An unresolved player has no fallback coordinate

Recognition failure stores `player.current = null`. No first arena cell or `(0,0)` placeholder may appear as a detection.

## D-098 — Standard and debug language are separate

Players see only detected, correction-needed, ready, and recommendation states. Rule codes, state versions, and recognition paths are rendered only after enabling Debug.

## D-099 — Pillar completeness requires visible review

Accepting detection proposals does not imply pillar-set completeness. The user must first see the complete overlay/list and explicitly confirm it.

## D-100 — Fixture-proof solving requires a byte-identical retained fixture

Review-mode fixture semantics are permitted only when the fixture ID is retained and match distance is exactly zero. Approximate matches and arbitrary uploads remain under the ordinary review profile.

## D-101 — Review commands are serialised by the UI

While a command is in flight, state-changing controls are disabled. This prevents concurrent commands from reusing a stale state version.

## D-102 — Browser E2E uses Playwright’s version-bound Chromium

The automated release proof uses Playwright 1.61.1 and its matching Chromium build. A system Edge installation is not part of the deterministic test contract.

## D-001 — Deterministic tactical authority

The final tactical decision is produced by a deterministic rules engine, not by an LLM.

## D-002 — Hybrid computer vision

Use canonical image registration and deterministic extraction first. Add a compact trained detector only for components that fail across real screenshots.

## D-003 — Manual correction is mandatory

Every detected field can be corrected. Low-confidence critical fields block solving.

## D-004 — Solo-first scope

The first public version supports one controlled player only. Multiplayer screenshots are rejected until shared-spell behaviour is modelled and verified.

## D-005 — Cumulative master file

Each phase updates one cumulative master specification and exports one complete versioned ZIP.

## D-006 — Rules before recognition

A formal and testable rules model must exist before automatic recognition is treated as authoritative.

## D-007 — No gameplay automation

The product annotates screenshots and recommends actions. It does not click, inject, read game memory or control the client.

## D-008 — Codex is a refinement stage, not the project foundation

Codex is not used during the current specification and first pre-live construction stages. It may only be introduced after a functioning pre-live repository exists with:

- a usable screenshot-to-answer flow;
- a test corpus;
- a known-defect backlog;
- reproducible local startup instructions;
- baseline test results.

Codex will then be used for review, refactoring, optimisation, additional tests and hardening.

## D-009 — Explicit rule authority

Every rule has one of five statuses:

- `verified_multi_source`;
- `verified_direct_observation`;
- `single_source_supported`;
- `hypothesis`;
- `unknown`.

Only the first two statuses may silently drive an authoritative recommendation. A single-source rule may be used only when the UI names the assumption and asks for confirmation.

## D-010 — Rule profiles isolate uncertainty

Unresolved behaviours are configuration values in a `RulesProfile`. They may not be hidden in movement code or solver heuristics.

## D-011 — No false precision

The solver must distinguish between:

- a state that is visually uncertain;
- a rule that is mechanically uncertain;
- a state with no safe solution;
- a technically invalid input.

These outcomes use different result statuses.

## D-012 — Arena model and screenshot transform are separate

The arena mask is stored in logical grid coordinates. Pixel transforms belong to screenshot calibration and must not alter game rules.

## D-013 — Source image facts come from file inspection

The retained reference image is 1951 × 1267. Documentation or UI display dimensions may not override the file header and checksum.

## D-014 — Fixed logical axis orientation

For the Grougalorasalar arena, `+x` points down-right and `+y` points down-left in the retained reference view.

## D-015 — Arena-cell authority is explicit

Arena cells are classified as observed, confirmed visible floor, boundary-unverified, occluded-unknown or permanently blocked. These classes control editor and solver gating.

## D-016 — No permanent blocker from ambiguous art

A hole, wall edge or foreground object in one screenshot is not enough to promote a logical cell to permanently blocked.

## D-017 — Projection anchor remains provisional

Logical `(0,0)` is the draft centre-pattern origin. `anchorConfirmed = false` blocks authoritative solving until independent evidence confirms it.

## D-018 — Manual editor changes are auditable

Object moves, reclassification, deletion and confirmations preserve stable IDs and are recorded in an undoable audit log.

## D-019 — Evidence export is allowed before solver readiness

An incomplete or assumption-dependent state may be saved as evidence, but it must not receive a tactical recommendation.

## D-020 — Reference encoding is an editor fixture

`data/arena/reference-turn.manual.json` proves the manual entry contract only. It is not a verified gameplay fixture or solver oracle.

## D-021 — Definite and conditional action graphs are separate

Unknown mechanics never create authoritative child states. Conditional actions are retained for diagnostics and completeness analysis only.

## D-022 — Rule dependency reachability controls blocking

An unknown blocks only when it can affect legality, destination, terminal outcome or the ordering of the best candidate. Irrelevant unknown fields do not blank the entire solve.

## D-023 — Availability-only state is a conservative under-approximation

A confirmed available spell permits one definite cast per sequence. Further casts are conditional until repeated-cast behaviour is verified.

## D-024 — Progress indices are not required for per-turn race direction

Unknown current track positions block terminal win/loss prediction, not the statement of which runner advances this turn.

## D-025 — Current pillars are not used as next-turn mobility forecast

Because pillar layouts change each turn, candidate ranking uses verified local terrain degree instead of hypothetical next-turn pillar actions.

## D-026 — User confirmation does not promote evidence authority

A recommendation depending on a single-source rule remains `confirmation_required` even after the user accepts the assumption.

## D-027 — Production and specification-test profiles are isolated

Synthetic explicit profiles may test formulas and ordering but cannot be loaded in production mode or treated as gameplay evidence.

## D-028 — Exact status completeness

`no_safe_solution` may be returned only after the definite candidate set is complete and no conditional safe candidate exists.

## D-029 — Canonical ordering is technical only

Spell/target enumeration and the final sequence-key tie-break guarantee repeatability; they do not encode tactical preference.


## D-030 — Board registration remains affine

The tactical transform is `pixel = origin + x*basisX + y*basisY`. An unconstrained homography may be diagnostic but may not be exported as the logical-grid authority.

## D-031 — Board and UI registration are separate

The arena board transform cannot be reused blindly for lower gauges and progress tracks because UI scaling and cropping may move independently.

## D-032 — Confidence and confirmation are independent

A manual confirmation changes field gate state and provenance. It never rewrites the detector confidence or model-calibration status.

## D-033 — Critical aggregate confidence uses the minimum

The overall visual confidence is the minimum confirmed solver-blocking field confidence. Averaging is forbidden because it can hide one unsafe field.

## D-034 — Automatic confirmation is validation-locked

While model calibration is unvalidated, every automatically extracted solver-blocking field requires user confirmation regardless of numeric score.

## D-035 — Pillar-set completeness is a separate field

Confirming each detected pillar does not prove that no pillar was missed. The system stores and gates on a separate completeness status.

## D-036 — Black and white glyph sets are confirmed separately

A single uncertain black cell can reverse race direction; an uncertain white cell can alter recharge and ranking. Both sets are solver-blocking under the Phase-3 preflight.

## D-037 — Detector proposals are immutable evidence

Manual correction creates an override linked to the original observation. It does not replace or delete the detector proposal.

## D-038 — Dataset splits are grouped by capture session

Screenshots from one run, device sequence or near-duplicate group may not cross training, validation and locked-test boundaries.

## D-039 — Gold visual labels require adjudication

The reference screenshot is a provisional single annotation. Only independently double-annotated and adjudicated records may enter the locked test set.

## D-040 — Accuracy and coverage are inseparable

Vision reporting must include auto-confirm coverage and rejection/review rates. Manually corrected or rejected cases are not counted as correct automatic detections.

## D-041 — Critical false-safe tolerance is zero

Any solver-ready recommendation produced from a wrong visual field that can affect legality, destination, collision, ranking or terminal claim is a critical false-safe, even when the final action happens to be correct.

## D-042 — Progress remains terminal-only

Unknown race indices may limit immediate win/loss claims but do not automatically block a per-turn statement of which runner advances.

## D-043 — Two-process pre-live topology

Phase 6 uses Next.js plus one FastAPI process. Vision and solver are separate in-process Python packages behind schema-tested boundaries; distributed workers are deferred until measurements justify them.

## D-044 — Manual deterministic flow precedes recognition

The first usable vertical slice is built from fixture/upload through manual correction to deterministic recommendation. Recognition may improve entry speed but cannot be a prerequisite for validating the product core.

## D-045 — Runtime baseline is frozen, dependencies are lockfile-exact

Node 24 LTS, CPython 3.13.14, Next.js 16.x and FastAPI 0.138.1 are the Phase-6 baseline. Exact application/transitive versions and image digests are fixed by reviewed lockfiles/manifests.

## D-046 — Domain schemas remain immutable at 0.5.0

Phase 5 adds orchestration contracts at 0.6.0 without rewriting unchanged Phase-3/4 domain payload versions. Compatibility is explicit rather than achieved by cosmetic version replacement.

## D-047 — Command-based editor mutation

All manual corrections are API commands with stable IDs, expected state version and audit. Direct partial replacement of TurnState is forbidden.

## D-048 — Optimistic concurrency and recommendation invalidation

Every analysis mutation increments `stateVersion`. Stale writes fail, and any state edit after solving invalidates the recommendation and action overlay atomically.

## D-049 — Technical capacity is not a tactical outcome

Timeout, node, memory or queue limits produce a capacity result/error. They can never be labelled `no_safe_solution` or return a partial action sequence.

## D-050 — Desktop correction boundary is honest

Precision correction is supported from 768 px upward, with the complete layout at 1180 px. Smaller screens may upload/read results but are explicitly blocked from imprecise editing.

## D-051 — Original visual language, screenshot-only game imagery

Product chrome uses original neutral workbench styling and symbols. Game assets are not copied into interface decoration; user-provided screenshots remain the only normal game imagery.

## D-052 — French is canonical; all shipping locales are complete

French copy defines product terminology. German and English must contain every shipping key. Runtime machine translation and raw-key display are forbidden.

## D-053 — Ephemeral-only is the default storage mode

Analyses expire after 60 idle minutes and six hours maximum, are excluded from backups and are immediately deletable. Quality-improvement evidence requires separate unchecked consent.

## D-054 — Fixture mode is absent from production routing

Development fixture endpoints are not merely hidden; they are not registered in preview/production, and startup fails if fixture mode is requested there.

## D-055 — Preview remains single-replica until jobs are durable

Horizontal API scaling is forbidden while analysis jobs and session state are process-local. A queue/store split requires its own tested architecture decision.

## D-056 — Phase 6 ships a manual-first executable product

The implementation gate is satisfied by an end-to-end manual correction and deterministic solve path. General recognition is not allowed to block product validation or to masquerade as complete.

## D-057 — Reference recognition is proposal loading, not detection proof

A 1951 × 1267 screenshot may load the retained manual encoding only as unconfirmed proposals. The behaviour validates integration and cannot be reported as detector accuracy.

## D-058 — Unknown screenshots remain valid manual analyses

A supported image that does not match the retained reference produces a blank logical state requiring manual registration/correction rather than a guessed board.

## D-059 — Access tokens are bearer secrets stored only as digests

The raw analysis token is returned to the client once. Only its SHA-256 digest is persisted, and protected session/assets require constant-time token verification.

## D-060 — Runtime data integrity is a readiness condition

Readiness hashes critical schemas, arena/rule data and policy files. A manifest mismatch prevents the service from being considered ready.

## D-061 — Historical fixture defects are preserved and disclosed

The implementation does not silently rewrite Phase-3 oracle data. Focus-scoped or malformed assertions are tested semantically and listed in the defect backlog until a versioned erratum exists.

## D-062 — Whole-result fixture equality requires global assertion scope

Exact status/ranking equality is enforced only when a fixture specifies the complete legal graph and global product result. Candidate-focused fixtures verify their named branch, dependency or terminal outcome.

## D-063 — Minimal UI shortcuts cannot become domain defaults

The current three-action button is a browser convenience only. The solver/API retain unknown action budget until explicit entry; Phase 7 must replace the shortcut with a proper unknown/numeric control.

## D-064 — Annotated output is derived and revocable

The annotated PNG is regenerated from the confirmed state and recommendation, protected by the analysis token and deleted with the session. It is never retained as training evidence by default.

## D-065 — Clean Compose execution is a Phase-7 gate

Because Docker was unavailable in the Phase-6 build environment, packaged Dockerfiles and Compose do not count as runtime proof. A clean-machine run is mandatory before validation closes.

## D-066 — Performance samples are engineering evidence, not production claims

Shared-container p95 measurements may show budget compliance for the current build but cannot represent detector accuracy, production latency or user-perceived browser performance.

## D-067 — Codex remains deferred through Phase 7

Codex may begin refinement only after reproducible startup, gameplay/visual evidence, at least 25 fixtures, automated baseline tests and a measured defect backlog are all packaged.


## D-068 — Resolution and language are not detector partitions

The arena is registered from distributed geometry/landmarks and mapped to logical cells. Separate models or screenshot libraries per resolution or French/German/English client are forbidden unless future measured evidence proves a UI-specific field requires them.

## D-069 — v0.8.0 uses a hybrid browser/server fast path

The browser owns immediate preview, decode/downscale and visible progress. Cached OpenCV registration and registered cell classification remain the single recognition authority in FastAPI until a browser implementation proves identical logical output and false-safe behaviour.

## D-070 — The critical path contains no OCR or generative model

OCR, LLM calls and heavyweight object detection are excluded from normal screenshot analysis. Text labels such as “Fin de tour” and spell names are not tactical inputs.

## D-071 — Templates and landmarks are process-cached

Reference features, candidate cells, fixture fingerprints and classification constants load once per API process. Reloading them for each screenshot is a performance defect.

## D-072 — The four new screenshots are one real capture-session group

The files are stored unchanged as `REAL-P7-01` through `REAL-P7-04`, share capture session `user-real-capture-session-2026-06-28` and may not be split across future train/validation partitions.

## D-073 — Equal raster dimensions do not prove absence of upstream scaling

All four new files are distinct 2048 × 1151 PNGs without embedded source-resolution metadata. Possible upload/client scaling is documented as unknown and is not treated as an artefact defect.

## D-074 — Visual annotation may be partial; unknown is normative

Player and visible pillars are annotated. Glyph cells, action budget, spell state and progress are classified only when visually clear. Ambiguous fields remain unknown rather than being inferred from one frame.

## D-075 — The solver receives no pixels or registration transform

Registration matrices and pixel timings remain recognition metadata outside `TurnState`. The deterministic solver receives logical cells, resources and rule/profile data only.

## D-076 — Registered overlays use the image-space affine basis

Annotated output for a non-reference screenshot projects logical cells through the detected image-space origin and basis. Scaling the old reference pixel transform by total image dimensions is no longer accepted.

## D-077 — Performance budgets are engineering targets

The v0.8.0 targets are: visible feedback ≤100 ms, browser decode/working copy p95 ≤150 ms, registration p95 ≤400 ms, baseline recognition p95 ≤900 ms, solver p95 ≤50 ms, local screenshot-to-result p95 ≤1.2 s, server fallback p95 ≤2.5 s and hard timeout 5 s. A value is not a release claim until measured on supported hardware.

## D-078 — Registered fixture signatures are proposals, not authority

A uniquely matched fixture may provide versioned glyph proposals for synthetic robustness tests and demos. It cannot auto-confirm fields, prove general recognition or bypass `MODEL-001`.

## D-079 — Corrections invalidate results immediately

Every editor command clears the recommendation, marks it invalidated and removes the previous annotated result from the browser. The user must solve again after any correction.

## D-080 — Numeric action budget replaces the fixed shortcut

The browser now starts with an unknown action budget and accepts an explicit integer 0–12. No default value is inserted from ordinary DOFUS combat assumptions.

## D-081 — Canonical arena geometry is coordinate data, not an image

`data/arena/grougalorasalar.cells.json` is the sole geometry authority. SVG and PNG files are generated review/debug derivatives. Image generation may never create or modify the runtime cell footprint.

## D-082 — The fixed combat arena contains 338 playable cells

The canonical coordinate list contains 338 unique cells. Direct coordinate count, `x + y` row totals and `x - y` row totals all reproduce 338. A future change requires new versioned gameplay or map evidence and a migration report.

## D-083 — Outermost user-marked cells are included

A boundary annotation point identifies the centre of an included playable cell, not the first excluded position. Such edge cells may contain a player, target or pillar and must be sampled by recognition.

## D-084 — Hidden boundary cells retain human provenance

Cells previously occluded by HUD, architecture, rocks or foreground tracks are promoted through the user's hidden-cell annotation plus grid and parity cross-checks. Their provenance remains explicit even though the resulting footprint is canonical.

## D-085 — Logical parity is `(x + y) mod 2`

Parity zero is stored as `light`, parity one as `dark`. Every orthogonal logical neighbour must flip parity. Screenshot brightness is a validation signal only and cannot overwrite logical parity.

## D-086 — Stable IDs are secondary to logical coordinates

Cell IDs are assigned deterministically by `y`, then `x`, for storage and UI references. Solver rules, movement and projection continue to use logical `(x, y)` coordinates.

## D-087 — Runtime registration projects all 338 cells; automatic object classification remains visibility-gated

After registration, every canonical cell centre and polygon is projectable. Cells explicitly occluded by architecture or foreground remain solver-visible as unknown/manual evidence rather than being automatically classified from unrelated track or HUD colours. This prevents false pillar/player detections while preserving the complete geometry.

## D-088 — Registration is a public geometry-only contract

`register_screenshot_to_arena` and `registerScreenshotToArena` expose screenshot-to-canonical affine registration. Their output remains recognition metadata and is never inserted into tactical `TurnState`.

## D-089 — OpenCV uses a bounded four-thread registration pool

The runtime caps OpenCV at four threads because automatic thread selection produced slower and less stable shared-container timings. This is an engineering implementation decision subject to supported-hardware benchmarking.

## D-090 — Arena-footprint authority does not verify gameplay edge behaviour

The 338-cell footprint proves which cells belong to the fixed map presentation. It does not resolve movement truncation, path blocking, spell-specific target legality or projection-anchor semantics. Those remain governed by V-004, V-007 and related rule gates.

## D-091 — Interior geometry and boundary authority are separate layers

The stable affine interior grid remains valid, but membership and authority of each outer cell are evaluated independently. A smooth global envelope cannot establish a boundary cell.

## D-092 — A confirmed boundary cell requires two accepted criteria

The accepted criteria are user boundary annotation, user hidden-cell annotation, visible empty-map surface and parity/geometric consistency. Fewer than two criteria force `confidence = low`, `sourceAuthority = unresolved` and visible review marking.

## D-093 — Missing annotation bytes do not count as per-cell evidence

The semantic meaning of the earlier green annotation remains documented, but its unavailable byte-original cannot confirm any particular cell. Architecture and rock edges remain secondary context only.

## D-094 — The 338-cell count is provisional during boundary review

The count still reproduces structurally, but count equality does not prove position correctness. Seven unresolved cells keep the footprint status at `boundary_refinement_review_required`; runtime must not silently expose them as walkable.

## D-095 — Position review uses local regional grid-line fits

Each boundary cell records expected and plausible empty-map centres, pixel and cell distance, fit region and a `0.12`-cell outlier threshold. This metric supports review but does not replace the two-evidence authority gate.
