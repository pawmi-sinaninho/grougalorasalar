# GROUGALORASALAR SOLVER — MASTER SPECIFICATION

**Version:** 0.9.0 (historical snapshot; superseded operationally by `MASTER_SPEC.md` v1.0.0)

## 100. Release-blocker repair: clean start and player workflow

The v0.9.0 release path is `docker compose up --build`, serving the player UI at `http://localhost:3000` and the ready API at `http://localhost:8000/api/v1/health/ready`. The Web image pins Node 24.17.0 by digest, installs npm 11.18.0, and uses `npm ci` exclusively.

The normal UI projects the controlled player, all typed pillars, doubtful pillars, and central-pattern cells onto the uploaded screenshot. Player and pattern correction are direct clicks. Action budget and each spell use explicit unknown/available/unavailable state. The solver button remains disabled until the five player-facing checks and detection review are complete. Internal status/rule codes are Debug-only.

The retained `REAL-P7-01` fixture proves player cell `(1,-1)`, 24 pillars, three dark and three light pattern cells, and the complete browser upload-to-recommendation flow. Fixture-proof solver semantics require a byte-identical retained fixture and exact match distance zero; no approximate or arbitrary upload gains that authority.
**Phase:** 7B-R — Boundary Refinement  
**Status:** REVIEW REQUIRED — 338-CELL WORKING MASK PROVISIONAL; 7 BOUNDARY CELLS UNRESOLVED  
**Language:** German working specification; player-facing UI planned for French first, then German/English  
**Core principle:** Screenshot interpretation and tactical solving are separate subsystems.

---

## 1. Product goal

A web application that accepts one screenshot per turn from the final tactical fight against Grougalorasalar and returns an explicit, executable action sequence for the current turn.

The answer must not be vague. The user should receive:

1. numbered spell casts in order;
2. the exact target pillar or target cell for each cast;
3. the expected final player cell;
4. whether Crocoburio should advance;
5. which spell charges should be restored;
6. a confidence score and any required manual correction;
7. an annotated copy of the screenshot.

The core solver is deterministic. Machine vision extracts the board state; a rules engine enumerates legal action sequences and ranks them.

---

## 2. Important screenshot interpretation

The attached reference screenshot contains three distinct combat entities:

- **Controlled player/avatar:** the small yellow-green crocodile-like unit standing on the main board.
- **Crocoburio progress runner:** the figure on the lower-left white progress track.
- **Grougalorasalar:** the black dragon on the lower-right dark progress track.

Therefore, the lower-left runner is not the controlled map piece. This distinction is mandatory for computer vision and game-state modelling.

---

## 3. Verified mechanics baseline

### 3.1 General rules

- The fight is tactical and does not use normal HP-loss gameplay.
- The controlled avatar has no normal movement points and moves through four special spells.
- The main board contains generated pillars.
- A reference glyph pattern appears near the board centre.
- The glyph pattern must be interpreted as relative offsets around the player's final position.
- Pillar positions and the centre glyph pattern change between turns.
- The player must finish on a different cell; remaining stationary is treated as failure for that resolution.
- A projected black glyph touching any pillar causes Grougalorasalar to advance.
- If no black projected glyph touches a pillar, Crocoburio advances.
- Projecting a white glyph onto a pillar recharges the spell represented by that pillar.
- If both a black and a white projected glyph touch pillars, the black collision has priority and Grougalorasalar advances.
- Grougalorasalar reaches the objective after eight adverse resolutions according to both major guides.

### 3.2 Movement spells

| Internal ID | French name | Colour | Cost | Target/range | Effect |
|---|---|---:|---:|---|---|
| `indecision` | Indécision | cyan | 1 AP | adjacent cell | Teleport to the targeted adjacent cell |
| `reflection` | Reflet | green | 1 AP | pillar at range 2 | Teleport symmetrically across the targeted pillar |
| `repulsion` | Rejet | yellow | 1 AP | pillar at range 1–2, line or diagonal | Move three cells away from the targeted pillar |
| `attraction` | Attrait | red | 1 AP | pillar at range 1–6, line only | Move three cells toward the targeted pillar |

### 3.3 Turn objective

The solver must produce a complete in-turn sequence, not merely one move. A turn can contain multiple one-AP movement spells. The end-of-turn position determines the projected glyph collisions and race progress.

---

## 4. Open verification items

These are not allowed to be silently guessed in code.

### V-001 — Crocoburio track length

- DofusPourLesNoobs states 14 cells.
- JeuxOnLine states 13 cells.
- The current Unity screenshot must be measured and validated from actual runs.

**Implementation rule:** track progress must be detected from the screenshot. Do not hard-code the win threshold until confirmed by replay evidence.

### V-002 — Exact spell-charge transition

The guides confirm that:

- spells can become unavailable;
- using the matching white-pillar colour restores that spell;
- gauges/cursors at the bottom represent spell availability.

Still to verify from current gameplay:

- exact initial charge count per spell;
- exact charge cost per cast;
- maximum charge per spell;
- whether multiple matching white pillars grant multiple charge units;
- whether a white centre glyph restores all spells or another defined subset;
- whether recharge resolves before or after the current turn ends.

### V-003 — Current multiplayer behaviour

A February 2026 official forum report states that multiple characters could join and that movement spells were shared across characters. This may be an unintended behaviour or a current rule change.

**V1 scope:** solo screenshot only. Multiplayer screenshots must be rejected with a clear message until independently modelled and tested.

### V-004 — Collision and path blocking

To verify from current gameplay:

- whether movement may pass through pillars;
- whether destination cells occupied by pillars are always invalid;
- whether push/pull movement truncates on obstacles;
- whether map-edge collisions truncate or invalidate movement;
- whether reflection destinations require a walkable cell only or additional line conditions.

### V-005 — Current screenshot/UI variants

Must be collected across:

- 1920×1080, 2560×1440 and 3840×2160;
- fullscreen and windowed;
- UI scaling variants;
- tactical mode/visual settings;
- French, German and English clients where icon positions or labels differ;
- current DOFUS Unity versions.

### V-006 — Action budget per turn

The four movement spells appear to cost one AP, but the total AP or cast budget available in this tactical fight is not yet reliably documented. The numbers shown beside combatants in the supplied screenshot correspond to combat order and must not be interpreted as AP.

**Product rule:** the pre-live solver must read or manually request the action budget. It may not infer a fixed value from ordinary DOFUS defaults.

### V-007 — Exact target geometry and line-of-sight

Still to verify:

- the range metric used by each spell;
- whether Reflet must be axis-aligned;
- whether Rejet permits both cardinal and diagonal alignment;
- whether line of sight applies;
- whether the targeted pillar must match the spell colour or whether colour only matters for recharge.

### V-008 — Direct central glyph effects and ordering

DofusPourLesNoobs states that ending on the physical central black glyph is adverse and ending on a physical central white glyph recharges spells by one. The exact scope, priority and timing are not directly observed in a current run.

### V-009 — No-black/no-white race outcome

DofusPourLesNoobs explicitly shows Crocoburio advancing when no projected glyph touches a pillar. JeuxOnLine describes Crocoburio progress primarily through white hits. This is treated as single-source supported until observed directly.

### V-010 — Turn-boundary resource timing

Still to verify:

- whether cast cost is committed immediately;
- whether white recharge can restore a spell used in the same turn;
- whether direct central-white recharge applies to all four spells;
- whether recharge is visible before or after race progress;
- whether any passive regeneration occurs at turn start.

---

## 5. Product scope

### 5.1 V1 included

- one screenshot for one solo turn;
- current fixed Grougalorasalar arena;
- automatic crop and board calibration;
- pillar detection and four-type classification;
- player-cell detection;
- central black/white glyph-offset detection;
- spell availability/charge detection;
- Crocoburio and dragon progress detection;
- deterministic action search;
- screenshot overlay with numbered actions;
- manual correction UI for all detected objects;
- confidence gating;
- French instructions;
- no account login required;
- no persistent screenshot storage by default.

### 5.2 V1 excluded

- direct game-memory reading;
- game automation or automated clicking;
- botting;
- live video capture;
- other DOFUS fights;
- multiplayer;
- mobile-native app;
- guaranteed solution when the screenshot omits the lower gauges or progress track;
- generative model making unverified tactical decisions.

---

## 6. End-to-end user flow

1. User opens the site.
2. User drags or pastes a screenshot.
3. Client validates file type, minimum dimensions and likely arena presence.
4. Backend normalises the screenshot to canonical arena coordinates.
5. Vision pipeline extracts a structured `DetectedTurnState`.
6. UI displays the detected board with editable overlays.
7. If any critical detection confidence is below threshold, the user corrects it.
8. The deterministic solver enumerates legal spell sequences for the current AP/charge state.
9. Candidate end states are evaluated against glyph/pillar collisions.
10. Best action sequence is returned.
11. UI shows numbered targets, final cell, expected progress and recharge effects.
12. User executes the sequence in DOFUS and submits the next-turn screenshot.

---

## 7. Canonical coordinate model

The arena is an isometric grid and must not be solved in raw pixels.

### 7.1 Coordinates

Use integer board coordinates `(q, r)` with a fixed canonical walkable-cell mask.

Pixel projection after normalisation:

```text
pixel_x = origin_x + q * basis_q_x + r * basis_r_x
pixel_y = origin_y + q * basis_q_y + r * basis_r_y
```

The exact origin, basis vectors and walkable mask are produced in Phase 1 from annotated reference images.

### 7.2 Board entities

- `player_cell`
- `pillars[]` with cell and spell type
- `glyph_pattern.black_offsets[]`
- `glyph_pattern.white_offsets[]`
- `spell_charges`
- `action_points`
- `crocoburio_progress`
- `dragon_progress`
- `turn_number` when detectable
- confidence per field

### 7.3 Glyph projection

For candidate final cell `P` and glyph offset `g`:

```text
projected_cell = P + g
```

Resolution:

```text
black_hit = any(projected black cell contains a pillar)
white_hits = all projected white cells that contain pillars
```

Priority:

1. if `black_hit`: adverse resolution;
2. otherwise: Crocoburio advances;
3. matching white hits restore their represented spells according to the verified charge rule.

---

## 8. Vision architecture

### 8.1 Principle

The recognition layer converts pixels into evidence-backed logical observations. It is not a tactical authority. A compact detector may propose values, but a versioned confidence policy and explicit solver gate decide whether those values are usable.

### 8.2 Pipeline

1. decode, orient and validate the image;
2. verify Grougalorasalar arena presence from geometry plus distributed landmarks;
3. estimate the logical-grid affine basis `pixel = origin + x*basisX + y*basisY`;
4. keep up to five transform hypotheses and reject unresolved ambiguity;
5. extract player, pillar instances and pillar types;
6. independently check pillar-set completeness over candidate cells;
7. classify physical black/white glyph cells and validate the projection anchor;
8. register lower UI regions separately from the board;
9. extract action budget, spell states and progress when visible;
10. emit field observations, component scores, alternatives and conflicts;
11. require the correction/confirmation UX whenever a critical gate is not passed;
12. export only confirmed logical values to `TurnState`.

### 8.3 Registration

The exported transform remains an affine logical-grid basis rather than an unconstrained homography. Accepted automatic registration requires at least six inliers in three board regions, median residual at most 0.06 cell, p95 at most 0.10 cell and confidence at least 0.97. Review is allowed up to p95 0.16 cell; worse inputs are rejected.

### 8.4 Model strategy

Start with deterministic registration, registered cell sampling and template/shape cross-checks. Add compact trained models only for components that fail across real screenshots. Board registration and UI-region registration are separate because UI scale can change independently.

### 8.5 Validation lock

Until the locked-corpus gate passes, `modelCalibrationStatus = unvalidated`. In that state, all automatically extracted solver-blocking fields require user confirmation regardless of numeric confidence.

The normative contracts are in `docs/vision/`, `schemas/recognition-result.schema.json`, `schemas/visual-observation.schema.json` and `data/vision/recognition-policy.v0.5.0.json`.

---
## 9. Solver architecture

### 9.1 State

```text
TurnState:
  board
  player_cell
  pillars
  glyph_pattern
  charges
  AP
  crocoburio_progress
  dragon_progress
  previous_player_cell or stationary constraint
```

### 9.2 Legal action generator

For each state:

- generate all legal `Indécision` destination cells;
- generate all targetable green pillars for `Reflet`;
- generate all targetable yellow pillars for `Rejet`;
- generate all targetable red pillars for `Attrait`;
- apply exact spell geometry and obstacle rules;
- decrement AP and the appropriate charge;
- repeat until zero AP or an explicit `end_turn`.

### 9.3 Search

Because the turn depth is small, exhaustive breadth-first or depth-first enumeration is preferable to probabilistic planning.

Each node is keyed by:

```text
(player_cell, AP_remaining, charge_vector, actions_used)
```

Deduplicate equivalent states while preserving the shortest or highest-resource path.

### 9.4 Candidate evaluation

Hard rejection:

- invalid destination;
- unavailable spell;
- unresolved rules ambiguity;
- ending on same cell;
- any projected black glyph on a pillar.

Lexicographic ranking:

1. safe resolution;
2. Crocoburio advance;
3. recharge spells currently nearest depletion;
4. maximise minimum remaining spell charge;
5. maximise number of distinct usable spells next turn;
6. maximise geometric mobility from the final cell;
7. minimise number of casts;
8. maximise vision confidence of all targeted objects.

The solver must be capable of returning multiple equally valid options, but the UI should present one recommended sequence and up to two alternatives.

### 9.5 Result explanation

Example structure:

```text
1. Attrait auf den markierten roten Pfeiler A.
2. Reflet auf den markierten grünen Pfeiler B.
3. Zug beenden.

Erwartung:
- Endfeld: q=…, r=…
- Kein schwarzes Muster trifft einen Pfeiler.
- Crocoburio +1.
- Reflet +1 Ladung.
- Konfidenz: 97 %.
```

The primary UI should show this graphically rather than relying on coordinates.

---

## 10. Confidence and fail-safe rules

Confidence is the weighted geometric mean of primary evidence, registration quality, snap margin, visibility and independent cross-check agreement. Hard caps prevent one strong score from hiding an unresolved conflict, out-of-distribution input, weak snap margin, occlusion or missing cross-check.

Confirmation is separate from confidence. A user correction changes gate state and audit provenance; it does not set detector confidence to 1.0.

Solver-blocking visual fields are:

- arena presence and registration;
- solo/multiplayer state;
- player cell;
- pillar-set completeness and every pillar cell/type;
- black and white glyph sets;
- projection anchor;
- action budget under Phase-3 precedence;
- spell state required by the selected resource mode.

Progress is terminal-only: unknown indices block an immediate win/loss claim but not necessarily per-turn race direction.

`TurnState.confidence.overall` is the minimum confirmed critical-field confidence. It cannot override a failed field gate. Automatic confirmation remains disabled until Phase-7 locked-corpus targets pass, including zero critical false-safe recommendations.

---
## 11. Technical stack recommendation

### Frontend

- Next.js with TypeScript
- React
- Canvas or SVG overlay
- Zod for client contracts
- Playwright for end-to-end tests

### Backend

- CPython 3.13.14
- FastAPI 0.138.1
- OpenCV
- NumPy
- Pydantic
- optional ONNX Runtime for compact detectors
- pytest and Hypothesis for solver tests

### Repository

```text
apps/web
services/vision-api
packages/contracts
packages/fixtures
docs
scripts
```

A pure Python solver is preferred initially so that image extraction, rules and replay tests share one runtime. A TypeScript port is optional after the rules are stable.

---

## 12. Phase plan

### Phase 0 — Discovery and baseline — COMPLETE

Deliverables:

- mechanics baseline;
- contradictions/open verification list;
- architecture decision;
- initial schemas;
- reference screenshot;
- delivery protocol.

### Phase 1 — Formal Domain Model & Verification Framework — COMPLETE

Deliverables:

- stable rule IDs and authority levels;
- formal movement and resolution contracts;
- explicit `RulesProfile` for unresolved mechanics;
- machine-readable rule catalogue;
- evidence capture protocol;
- schema version 0.2.0;
- revised pre-live delivery plan;
- Codex moved to a later refinement stage.

Gate: every known uncertainty is explicit, testable and prevented from silently producing an authoritative recommendation.

### Phase 2 — Arena Digital Twin & Manual State Editor Specification — COMPLETE AS DRAFT

Deliverables:

- canonical logical axes and origin;
- complete draft walkable-cell mask;
- permanent blocked and occluded cells;
- reference pattern anchor;
- screenshot crop and anchor specification;
- complete manual state-editor interaction;
- annotated arena diagrams;
- machine-readable arena model.

Gate: a human can reproduce any supplied screenshot as a valid logical turn state without automatic recognition.

### Phase 3 — Solver Behaviour & Test Oracle Specification — COMPLETE

Deliverables:

- exact legal-action enumeration contract;
- state-transition traces;
- candidate ranking and tie-breaks;
- impossible and ambiguous state handling;
- fixture catalogue and expected outcomes;
- property-test specification.

Gate: each verified fixture has an unambiguous expected set of legal and safe outcomes.

### Phase 4 — Screenshot Recognition & Confidence UX Specification — COMPLETE

Deliverables:

- canonical image registration pipeline;
- pillar, player and glyph extraction design;
- spell-gauge and progress extraction design;
- confidence model;
- correction UX;
- dataset and evaluation protocol.

Gate: passed as a specification. Every critical field has extraction, cross-check, confidence, correction, solver effect and evaluation target. This does not claim measured detector accuracy.

### Phase 5 — Complete Pre-Live Technical & Visual Specification — COMPLETE

Deliverables:

- repository and service boundaries;
- API contracts;
- page and component inventory;
- French-first player copy;
- privacy and retention rules;
- deployment and acceptance-test plan.

### Phase 6 — First Pre-Live Implementation

Deliverables:

- functioning local or preview web application;
- screenshot upload;
- manual correction;
- deterministic solver trace;
- baseline recognition where feasible;
- structured fixtures and automated tests.

The implementation method remains independent from Codex.

### Phase 7 — Pre-Live Validation

Deliverables:

- locked validation corpus;
- measured detection and solver results;
- defect and ambiguity backlog;
- reproducible local startup;
- known-limitation report.

### Phase 8 — Codex Refinement

Codex receives an existing working repository, test corpus and defect backlog. Its scope is review, refactoring, optimisation, missing tests, robustness, security and final UX polish. It is not used to invent the combat model.

### Phase 9 — Closed Beta & Production Hardening

Deliverables:

- consent-based error reporting;
- security and file-handling audit;
- rate limiting and observability;
- deployment/runbook;
- production release gate.


## 13. Required evidence before authoritative solving can be enabled

At least one complete current-version recording or screenshot sequence from fight start to win, with:

- screenshot before every player turn;
- exact spell casts and targets;
- screenshot after every end-turn resolution;
- visible gauges and both progress tracks;
- at least one spell becoming unavailable;
- at least one matching white-pillar recharge;
- at least one intentionally adverse black collision if practical;
- original resolution retained.

Prefer two or more independent runs to expose random layouts and rule edge cases.

---

## 14. Delivery and versioning protocol

Every phase produces exactly two top-level deliverables:

1. `GROUGALORASALAR_SOLVER_MASTER_vX.Y.Z.md`
2. `GROUGALORASALAR_SOLVER_PHASE_N_vX.Y.Z.zip`

The ZIP must contain:

```text
MASTER_SPEC.md
CURRENT_STATUS.md
DECISIONS.md
NEXT_STEP.md
CHANGELOG.md
README.md
all current source code
all tests
all schemas
all non-proprietary fixtures
```

The master file is cumulative and is the single source of truth. It must never omit prior accepted decisions. Each new chat receives:

- the latest master MD as a project source;
- the latest ZIP as an attachment;
- new evidence/screenshots collected since the previous phase.

The new chat must read these before making changes.

---

## 15. Development operating model

### 15.1 Before a pre-live build

The project is developed through cumulative specifications and controlled artefacts inside ChatGPT. Each phase must preserve accepted decisions, isolate hypotheses and export a complete master MD plus phase ZIP.

### 15.2 Codex entry restriction

Codex must not be used as the foundation of the current project. It may only start after a functioning pre-live version exists with:

- documented local startup;
- screenshot-to-turn-state flow;
- manual correction;
- deterministic recommendation trace;
- at least 25 structured fixtures;
- automated baseline tests;
- current master specification;
- measured or reproducible defect backlog.

### 15.3 Codex refinement duties

Once the entry gate is satisfied, Codex may:

- inspect the complete repository;
- refactor without altering verified behaviour;
- add tests for every change;
- improve performance and maintainability;
- harden browser, resolution and UI-scale support;
- perform security and privacy checks;
- update all status documents and report exact test commands/results.

Codex may not silently convert hypotheses into rules or use an LLM as final tactical authority.


## 16. Phase 0 conclusion

The project is technically feasible.

The decisive insight is that this is not primarily a conversational-AI problem. It is:

1. a fixed-arena image registration problem;
2. a discrete state-extraction problem;
3. a small deterministic search problem;
4. a confidence-controlled correction UX problem.

The largest current risk is incomplete game-rule verification, especially spell-charge transitions and current-version edge cases. Phase 1 isolates those uncertainties; direct gameplay evidence must resolve them before automatic recommendations are treated as authoritative.

---

## 17. Phase 1 — Formal domain model

### 17.1 Coordinate convention

Use a logical square grid with integer cells `(x, y)`. The isometric screenshot is only a rendering. Tactical relations are defined in logical coordinates:

```text
orthogonal adjacency: |dx| + |dy| = 1
axis alignment: dx = 0 or dy = 0
diagonal alignment: |dx| = |dy|
```

Phase 2 fixes `+x` as down-right and `+y` as down-left for the retained reference screenshot. The numeric pixel transform remains provisional until multi-reference registration.

### 17.2 Core objects

- `ArenaModel`: walkable cells, permanent blockers, central-pattern anchor.
- `TurnState`: player, pillars, glyph offsets, resources, progress and confidence.
- `RulesProfile`: every mechanically relevant configuration, including unknowns.
- `Action`: source, spell, target, destination, cost and rejection reason.
- `ResolutionTrace`: projected cells, collisions, race decision, recharge and next state.
- `VerificationObservation`: before-state, action sequence, after-state and evidence review.

### 17.3 Rule authority

Every rule is labelled:

1. `verified_direct_observation`;
2. `verified_multi_source`;
3. `single_source_supported`;
4. `screenshot_observed`;
5. `hypothesis`;
6. `unknown`.

Critical rules in categories 4–6 cannot silently produce `solved`. Category 3 requires a named assumption and user confirmation unless a product owner explicitly promotes it based on evidence.

## 18. Formal movement contracts

### 18.1 Indécision

Candidate destination equals the targeted contact cell. Contact metric, occupancy and line-of-sight remain profile-controlled.

### 18.2 Reflet

For source `P` and target pillar `T`:

```text
destination = 2*T - P
```

Target range and alignment remain profile-controlled until current gameplay evidence exists.

### 18.3 Rejet

Let `u` be an allowed unit vector from the target pillar toward the player:

```text
destination = P + 3*u
```

Path blocking, edge behaviour and destination occupancy remain unresolved.

### 18.4 Attrait

Let `u` be the allowed unit vector from the player toward the target pillar:

```text
raw_destination = P + 3*u
```

When the pillar is fewer than three cells away, the game may stop adjacent, overshoot or reject the action. The profile must explicitly select one of these behaviours or remain unknown.

## 19. Resolution model

For final player cell `P` and glyph offset `g`:

```text
projected_cell = P + g
```

The trace evaluates:

1. invalid state or unresolved critical rule;
2. stationary result;
3. direct physical central glyph;
4. projected black collisions;
5. projected white collisions;
6. black-priority race outcome;
7. no-black race outcome according to profile;
8. recharge timing and next resource state.

The exact deciding condition must be visible to the player and in machine output.

## 20. Resource model

Each spell stores:

- availability: available, unavailable or unknown;
- optional numeric charge;
- cost per cast;
- maximum charge;
- matching-pillar recharge;
- direct-centre recharge;
- resolution timing.

The first pre-live version may use boolean availability when numeric gauge values cannot be proven. It may not fabricate charge numbers from approximate cursor position.

## 21. Safe solver statuses

- `solved`: visually and mechanically authoritative.
- `confirmation_required`: a supported assumption must be confirmed.
- `blocked_unverified_rule`: materially different outcomes depend on an unknown rule.
- `no_safe_solution`: all verified legal endings are adverse.
- `invalid_state`: contradictory or incomplete input.

## 22. Phase-1 schema evolution

Version 0.2.0 adds:

- `rulesProfileId` on turn states and recommendations;
- current and previous player cells;
- explicit multiplayer detection;
- confirmed/unknown availability states;
- separate visual and mechanical confidence;
- assumption lists and rule IDs;
- full action source/destination trace;
- structured verification observations.

## 23. Pre-live strategy

The first pre-live version is built before Codex is introduced. The project therefore separates:

- specification completeness;
- initial working implementation;
- measured validation;
- later Codex refinement.

This prevents Codex from optimising guessed rules or prematurely fixing unstable interfaces.

## 24. Phase 1 acceptance result

Phase 1 is complete as a specification because:

- the early Codex dependency has been removed;
- every critical unknown is explicit;
- movement and resolution have formal contracts;
- evidence can be captured in a repeatable format;
- the solver has defined fail-safe statuses;
- the next phase can digitise the arena without inventing combat mechanics.

Phase 1 does **not** claim that the fight is fully mechanically verified.

## 25. Immediate next phase

Phase 2 creates the arena digital twin and manual state-editor specification. Its completed draft is documented below. No automatic screenshot recognition and no Codex work begins in Phase 2.

---

## 26. Phase 2 — source-image correction

Direct file inspection establishes that `assets/reference/user_reference.png` is **1951 × 1267 pixels**, not `1527 × 991`.

The retained source image is identified by SHA-256:

```text
2756a38a4451117001dedeab2e4da14423d4aa50978bc4549c9ff0cb1340f976
```

This correction is a verified artefact fact. It does not change any gameplay rule.

## 27. Fixed logical axes and draft transform

The Phase-2 coordinate convention is:

- origin logical cell: `(0,0)`;
- `+x`: down-right on the screenshot;
- `+y`: down-left on the screenshot.

For the retained reference image only:

```text
origin_pixel = (964.895, 441.7425)
basis_x      = ( 66.75, 33.375)
basis_y      = (-66.75, 33.375)
```

Projection:

```text
pixel_x = 964.895  + 66.75*x - 66.75*y
pixel_y = 441.7425 + 33.375*x + 33.375*y
```

The estimated residual is approximately 2.5 pixels on the retained screenshot.

This is a single-reference calibration. It must not be reused for another resolution, UI scale or crop without registration.

## 28. Arena-model authority classes

The arena model uses five mutually exclusive cell classes:

1. `walkable_observed`;
2. `walkable_confirmed`;
3. `boundary_unverified`;
4. `occluded_unknown`;
5. `permanent_blocked`.

Their meaning is visual/evidential, not mechanical.

### 28.1 Draft counts

The v0.3.0 model contains 338 candidate cells:

- 193 `walkable_confirmed`;
- 34 `walkable_observed`;
- 37 `boundary_unverified`;
- 74 `occluded_unknown`;
- 0 `permanent_blocked`.

No interior cell is promoted to permanently blocked from one screenshot. Apparent holes or edge architecture remain outside the confirmed mask or explicitly uncertain.

### 28.2 Solver gating

- `walkable_confirmed` and `walkable_observed` may be simulated;
- `boundary_unverified` requires confirmation;
- `occluded_unknown` blocks authoritative solving;
- `permanent_blocked` and outside cells are invalid.

## 29. Central projection anchor

The physical centre-pattern origin is represented by logical cell `(0,0)`.

Authority: **draft from map-centre alignment and guide evidence**.

The manual editor stores:

- the physical source cells;
- the relative black/white offsets;
- `anchorConfirmed`.

Changing the anchor recomputes offsets while preserving physical source cells.

An unconfirmed anchor prevents `solved`.

## 30. Reference screenshot manual encoding

The retained screenshot is manually encoded as:

```text
player = (7,-1)

black offsets:
  (-1,-1)
  ( 1,-1)
  ( 1, 1)

white offsets:
  (0,-3)
  (0, 2)
  (2,-1)
```

Twenty-seven visible pillars are stored in `data/arena/reference-turn.manual.json`.

Resources, action budget and both progress indices remain unknown. Therefore the fixture is a manual-editor acceptance case, not a tactical solver oracle.

## 31. Manual state-editor workflow

The required editor stages are:

1. source and calibration;
2. board objects;
3. glyph pattern;
4. spell resources and action budget;
5. progress tracks;
6. review and export.

### 31.1 Board tools

- set or move the single player;
- add a pillar with one of four spell types;
- move or recolour a pillar while preserving its ID;
- erase;
- confirm placement on an uncertain arena cell.

### 31.2 Glyph tools

- paint black;
- paint white;
- erase;
- move the provisional anchor;
- show physical cells and computed offsets simultaneously.

### 31.3 Resource tools

Each spell stores availability, optional numeric value, confidence and confirmation. The action budget remains unknown unless directly entered or observed.

### 31.4 Progress tools

Each runner stores an optional index, confidence and confirmation. The Crocoburio maximum is not enforced while V-001 is open.

### 31.5 Audit

Every add, move, remove, reclassify and confirmation is undoable and recorded in a `ManualEditorSession`.

## 32. Validation classes

Editor validation separates:

- image/calibration failure;
- arena-cell uncertainty;
- duplicate occupancy;
- glyph contradiction;
- projection-anchor uncertainty;
- resource incompleteness;
- progress incompleteness;
- multiplayer rejection;
- unknown mechanical rules.

A state may be saved as evidence even when it cannot be solved.

The complete catalogue is in `docs/editor/ARENA_VALIDATION_CATALOG.md`.

## 33. Phase-2 schemas

Version 0.3.0 adds:

- `arena-model.schema.json`;
- `manual-editor-session.schema.json`;
- `anchorCell` and `anchorConfirmed` to `TurnState.glyphPattern`;
- a machine-readable draft arena model;
- a manual reference-turn fixture;
- calibration anchors and cell-classification CSV.

Existing rules, recommendation and observation contracts are version-bumped without changing their Phase-1 semantics.

## 34. Phase-2 acceptance result

Phase 2 is complete as a specification and draft arena model because:

- logical axes are fixed;
- a reproducible single-reference transform exists;
- every candidate cell is classified;
- uncertain and occluded cells are not promoted to fact;
- the supplied screenshot is reconstructable as a structured state;
- the editor workflow, audit model and validation catalogue are complete;
- all machine-readable artefacts validate.

Phase 2 does **not** claim:

- a final edge mask;
- a verified projection anchor;
- universal screenshot calibration;
- verified movement destinations;
- a working editor implementation;
- a tactical recommendation.

## 35. Phase-2 handoff result

Phase 2 handed the project to **Phase 3 — Solver Behaviour & Test Oracle Specification**. That handoff is now completed by sections 36–45 below. Unknown movement and resource mechanics remain profile-controlled.

## 36. Phase 3 — solver input and preflight

The solver consumes only logical data: `TurnState`, `ArenaModel`, `RulesProfile`, rule catalogue and solve request. It never reads pixels.

Preflight distinguishes structural invalidity from missing mechanical knowledge. Duplicate occupancy, multiplayer and contradictory budgets are `invalid_state`; unknown budget, anchor or required mechanics are `blocked_unverified_rule`.

Action-budget source precedence is current confirmed turn state, then profile default. A conflict is invalid. Movement cost must be a positive integer.

## 37. Definite and conditional action graphs

The authoritative search graph contains only actions whose legality, destination and resource transition are fixed. Actions affected by an unknown mechanic or uncertain arena cell are stored in a separate conditional graph with exact rule dependencies.

Every reachable definite node yields an explicit end-turn candidate. Equivalent nodes are deduplicated by player cell, remaining budget, resource state and availability-only cast counts. The lexicographically smallest sequence key is retained.

This design prevents an unresolved path rule from contaminating otherwise verified candidates while still proving whether a hidden safe branch may exist.

## 38. Exact action enumeration

Canonical spell order is Indécision, Reflet, Rejet, Attrait. Targets are ordered by logical cell and pillar ID.

- Indécision enumerates the exact neighbour set selected by `contactMetric`; destination equals target.
- Reflet uses `destination = 2*T - P`. Range metric, alignment, target-pillar type, line of sight and path relevance are explicit.
- Rejet normalises a configured cardinal or diagonal vector from pillar to player and uses `destination = P + distance*u`.
- Attrait normalises the vector from player to pillar and uses `raw destination = P + distance*u`; short-range behaviour is explicit.

Path, edge and occupied-destination behaviour are never inferred from generic DOFUS rules.

## 39. Resource semantics

In numeric mode, action budget and charge cost are committed immediately and may not become negative.

In availability-only mode, a confirmed available spell permits one definite cast per sequence. A repeated cast is conditional on R-048. This is a conservative enumeration boundary, not a claim about actual depletion.

Recharge is resolved only after end turn. Unknown stacking blocks only when multiple white hits of the same spell type occur. Recharge during an adverse resolution is controlled by an explicit profile value.

## 40. Resolution trace

Every candidate emits an ordered trace:

1. preflight and enumeration;
2. cast and charge cost;
3. movement formula, path and destination;
4. end turn;
5. stationary and direct-centre checks;
6. glyph projection and collision collection;
7. race resolution;
8. recharge and next resource state;
9. ranking and final status.

Each event names its rule IDs. Collision arrays use stable pillar IDs sorted ascending.

## 41. Status precedence

- `invalid_state`: contradictory or malformed state/profile.
- `blocked_unverified_rule`: an unknown or hypothesis can change legality, destination, outcome or best-candidate ordering.
- `no_safe_solution`: the complete definite graph contains only adverse terminals and no conditional safe branch exists.
- `confirmation_required`: the complete best result depends only on single-source rules or a manually confirmed boundary.
- `solved`: every relevant mechanical and visual dependency is authoritative.

User acceptance of a single-source assumption does not promote its evidence status; the output remains `confirmation_required`.

## 42. Deterministic ranking

The normative policy is lexicographic:

1. race safety;
2. terminal Crocoburio win/nonterminal/unknown/dragon win;
3. post-turn resource resilience using max-min ordering;
4. verified orthogonal local terrain degree;
5. fewer casts;
6. higher minimum critical-input confidence;
7. canonical sequence key using typed action tuples, not raw string order.

Current pillar layout is not used to predict next-turn mobility because pillars change each turn.

## 43. Progress handling

Current track indices are not required to report which runner advances this turn. They are required to determine whether that advance immediately wins or loses the fight. Unknown progress therefore yields `terminalFightState = unknown` without automatically blocking the tactical movement recommendation.

## 44. Phase-3 machine-readable artefacts

Version 0.4.0 adds:

- expanded `rules-profile.schema.json`;
- `legal-action.schema.json`;
- `resolution-trace.schema.json`;
- `solver-request.schema.json`;
- `solver-fixture-catalog.schema.json`;
- ranking, status and rule-dependency policy JSON;
- 26 structured fixtures;
- 30 property-test requirements.

Synthetic explicit profiles are specification tests only and cannot be loaded in production.

## 45. Phase-3 acceptance result

Phase 3 is complete as an implementation-neutral solver and oracle specification because:

- every spell has exact enumeration order and formulas;
- unknown mechanics are explicit profile branches;
- definite and conditional states cannot be confused;
- status and ranking are deterministic;
- fixture equality is defined through canonical signatures and ordered sequences;
- the Phase-2 reference screenshot correctly remains blocked rather than receiving fabricated advice.

Phase 3 does **not** claim live-game verification or provide a production solver implementation.

## 46. Phase-3 handoff result

Phase 3 handed the project to **Phase 4 — Screenshot Recognition & Confidence UX Specification**. That handoff is now completed by sections 47–56 below. The solver contract remains unchanged in meaning; visual provenance and gates are now explicit in `TurnState` v0.5.0.

## 47. Phase 4 — ingest and arena-presence gate

Supported pre-live inputs are PNG, JPEG and WebP from 1280×720 up to 33.2 megapixels. EXIF orientation is normalised. The main board, controlled player and central pattern must be present; missing lower UI may continue only through manual entry.

Arena presence combines isometric geometry with stable landmarks distributed across at least three regions. A floor colour or one template can never identify the fight alone. False arena acceptance has a locked-corpus target of zero.

## 48. Registration contract

Registration estimates `origin`, `basisX` and `basisY` for the logical-grid affine transform. It keeps alternative hypotheses and requires explicit separation from the second-best transform.

Accepted automatic registration requires:

- at least six inliers;
- at least three spatial regions;
- median residual ≤ 0.06 cell;
- p95 residual ≤ 0.10 cell;
- confidence ≥ 0.97;
- no near-tied hypothesis.

Review is permitted up to p95 0.16 cell. Manual correction uses origin, `+x`, `+y` and two extra residual checks.

## 49. Visual observation contract

Each field proposal is a `VisualObservation` with:

- stable observation ID and field path;
- proposed value and alternatives;
- criticality;
- five component scores;
- final confidence;
- extraction methods and versions;
- independent cross-checks;
- reason codes and source region;
- decision state and manual-override flags.

The original detector proposal remains immutable after correction.

## 50. Field extraction and completeness

- Player detection uses board-avatar evidence plus unit-base/cell snap and must not confuse the lower Crocoburio runner.
- Pillars use common pedestal detection, logical-cell snap, icon-plus-colour type classification and an independent cell-wise completeness scan. Pillar count is never fixed to 27.
- Glyph detection classifies physical centre cells as black, white, neutral or unknown. Black and white sets are confirmed independently.
- The projection anchor is arena metadata and remains blocked while its live-game authority is provisional.
- Action budget is read only from the actual UI or an authoritative profile; ordinary DOFUS defaults are forbidden.
- Spell slots bind by icon identity and expose availability/value separately.
- Progress uses runner-to-track-cell snap and is terminal-only.

## 51. Confidence and conflict model

Base confidence is:

```text
primary^0.35 * registration^0.20 * snapMargin^0.15
* visibility^0.15 * crossCheck^0.15
```

Hard caps apply:

- unresolved method conflict: 0.39;
- out-of-distribution input: 0.49;
- snap margin below 0.15 cell: 0.69;
- partial occlusion without temporal support: 0.74;
- no independent cross-check: 0.79.

Aggregate confidence is the minimum confirmed solver-blocking field confidence, never an average.

## 52. Validation lock and solver gate

Automatic confirmation is disabled while the model is unvalidated. A numeric score alone cannot make a field authoritative.

`ready_for_solver` requires confirmed arena, transform, solo state, player, complete pillar set, pillar cells/types, black/white sets, anchor, action budget, required spell state and no blocker conflict.

User confirmation changes the visual gate only. It does not promote mechanical evidence or rewrite detector confidence.

## 53. Correction UX

The review UI orders unresolved items by tactical impact and provides field-specific interactions:

- three-anchor registration;
- player-cell selection;
- pillar add/move/delete/reclassify plus separate set-completeness confirmation;
- black/white/erase glyph painting;
- explicit action-budget and spell-state input;
- optional progress-cell selection.

Any post-solve edit invalidates the prior recommendation.

## 54. Dataset and annotation protocol

Screenshots are grouped by capture session to prevent train/test leakage. Gold records require independent double annotation of solver-blocking fields and adjudication. The reference screenshot is still provisional single annotation and not an accuracy benchmark.

Coverage must be reported across resolution, window mode, UI scale, language, client version, compression and occlusion. Training, retention and public-display consent are separate. Unknown remains a valid label.

## 55. Evaluation and false-safe gate

The evaluation contract includes component, exact-state and end-to-end metrics. Accuracy is always reported with auto-confirm coverage and rejection rate.

Auto-confirmation cannot start before the locked set contains at least 150 adjudicated screenshots from at least 15 independent capture sessions and all field targets pass. Critical false-safe recommendation tolerance is zero.

The 20 visual contract fixtures test ingest, registration, object/glyph/resource/progress ambiguity and policy gating. They are specification fixtures, not measured model results.

## 56. Phase-4 acceptance result and immediate next phase

Phase 4 is complete as an implementation-neutral recognition, confidence, correction and evaluation contract because every critical visual field has:

- a primary extraction method;
- an independent cross-check where feasible;
- a confidence formula and threshold;
- a correction interaction;
- an explicit solver-gating consequence;
- a labelled data format and metric.

Phase 4 does **not** contain a detector implementation or accuracy result. Automatic critical-field confirmation remains disabled.

**Immediate next phase: Phase 5 — Complete Pre-Live Technical & Visual Specification.**

Phase 5 must freeze repository ownership, API contracts, page/component behaviour, French-first copy, privacy, deployment, observability and implementation acceptance tests so Phase 6 can build the first functioning pre-live application without architectural gaps.

## 57. Phase 5 — frozen pre-live architecture

Phase 5 freezes a two-process implementation topology:

- a Next.js web process owns upload, review, correction and result presentation;
- a FastAPI process owns HTTP/session orchestration and imports vision and solver as separate Python packages.

The first pre-live build deliberately avoids a distributed worker system. Vision and solver remain strict module boundaries with schema-tested interfaces. This reduces operational failure points while preserving the rule that pixels never enter tactical formulas.

The repository, ownership and dependency direction are normative in `docs/architecture/PRE_LIVE_TECHNICAL_BLUEPRINT.md` and `data/architecture/package-ownership.v0.6.0.json`.

## 58. Runtime and contract freeze

Phase-6 baseline:

- Node.js 24 LTS, development image 24.17.0;
- Next.js 16.x App Router, React 19.x and TypeScript 5.x;
- CPython 3.13.14;
- FastAPI 0.138.1 with Pydantic 2.x;
- Docker Compose as the cross-platform acceptance path;
- JSON Schema draft 2020-12 as cross-runtime authority.

Exact application dependencies and container digests are committed in the first reviewed Phase-6 lockfiles. Existing domain schemas remain version 0.5.0 because Phase 5 does not mutate their meaning. New lifecycle/API/overlay contracts use 0.6.0.

## 59. Analysis-session lifecycle

The API owns one monotonic `stateVersion` lifecycle from creation through upload, recognition, review, solving, expiry and deletion. Every write command carries the expected state version. Corrections after a solve invalidate recommendation and action overlay atomically.

Technical capacity outcomes are separate from tactical outcomes. A timeout or node cap can never be returned as `no_safe_solution`.

The orchestration schema is `schemas/analysis-session.schema.json`.

## 60. HTTP and editor-command contracts

The frozen `/api/v1` surface includes:

- liveness, readiness and runtime metadata;
- analysis creation, protected upload and current-state retrieval;
- protected normalised/thumbnail/annotated assets;
- command-based manual correction;
- deterministic solve;
- overlay retrieval;
- idempotent deletion;
- fixture/diagnostic endpoints that do not exist in production.

Editor state changes occur only through auditable commands. Optimistic concurrency and idempotency protect against duplicate or stale browser actions. API technical failures use the stable `ApiError` envelope; recognition and solver statuses remain domain results.

## 61. Complete UI-state inventory

V1 contains no login, profile, dashboard or screenshot history. Public routes are landing, method and privacy. One token-protected analysis workspace covers upload through result.

Desktop is the complete correction surface. Tablet stacks the same tools. Mobile supports upload/status/result reading but explicitly blocks precision correction below 768 px rather than claiming unreliable support.

Every workspace state, component and keyboard action is assigned in `docs/frontend/PAGE_COMPONENT_STATE_INVENTORY.md`.

## 62. Visual overlay language

The screenshot is the dominant work surface. SVG overlays use logical coordinates and one shared image transform.

Normative markers include:

- player diamond;
- numbered pillar circles with spell letter;
- patterned black and white glyph cells;
- explicit review/conflict/manual-override badges;
- numbered action targets and segmented movement arrows;
- final-cell ring, unsafe-hit cross and recharge plus.

Colour is never the sole signal. Motion is limited to short informational transitions and respects reduced-motion settings. The product chrome uses original neutral workbench styling and does not copy game fonts or decorative panels.

## 63. French-first content contract

French is canonical; German and English are complete maintained translations. Runtime machine translation is forbidden. Missing production keys fall back to French without exposing raw keys.

Copy names the exact field, rule or remedy and avoids vague “AI” wording. Spell names remain French in all locales. Player instructions use visible targets and cases rather than raw logical coordinates.

## 64. Privacy, retention and deletion

Default mode is ephemeral only:

- idle TTL 60 minutes;
- hard maximum six hours;
- no backup of ephemeral volume;
- immediate user deletion;
- no evidence/training copy.

Quality-improvement evidence requires separate unchecked consent. Image bytes, filenames, hashes, OCR text, full states and access tokens are forbidden in logs. Deletion revokes access, removes every asset/state and prevents late-running work from persisting a result.

## 65. Local development and fixture mode

The normative startup is:

```text
docker compose up --build
```

The repository must also expose stable root commands for checks, E2E tests and fixture loading. Fixture mode includes all 26 solver fixtures, all 20 visual fixtures, reference editor data, forced lifecycle states and diagnostics. It cannot be enabled in preview/production or write evidence.

## 66. Test and performance gate

Phase 6 must implement schema, unit, property, fixture, integration, browser, visual, accessibility, privacy, security and performance layers.

Key engineering budgets include:

- first visible feedback after upload/paste <= 100 ms;
- browser image decode and working-copy creation p95 <= 150 ms;
- arena registration p95 <= 400 ms;
- complete baseline recognition p95 <= 900 ms;
- deterministic solver p95 <= 50 ms;
- local screenshot-to-result p95 <= 1.2 seconds;
- server-supported fallback p95 <= 2.5 seconds;
- hard timeout 5 seconds;
- editor command API p95 <= 150 ms;
- delete endpoint p95 <= 500 ms and filesystem cleanup <= 10 seconds;
- maximum 100,000 solver nodes unless reviewed evidence changes the bound.

These are acceptance budgets, not claims of measured performance.

## 67. Deployment and observability

Preview uses one web container and one API replica with private ephemeral storage. Horizontal API scaling is forbidden until a durable distributed job/session design exists.

Readiness verifies contracts, arena/rules data, models/templates and storage. Structured telemetry is bounded and excludes image/state payloads. Manifest mismatch, disabled deletion or unsafe fixture mode prevents startup.

## 68. Phase-5 acceptance result and immediate next phase

Phase 5 is complete because every user-visible state and every service transition now has:

- one owner;
- one contract;
- one failure behaviour;
- one privacy rule;
- one testable acceptance criterion.

The dependency-ordered Phase-6 backlog intentionally delivers the deterministic manual flow before baseline recognition. This prevents recognition quality from blocking the first usable pre-live build.

Phase 5 does **not** contain the production application, a trained detector, measured accuracy or live verification of open mechanics. Automatic critical-field confirmation remains disabled.

**Immediate next phase: Phase 6 — First Pre-Live Implementation.**

## 69. Phase 6 — executable repository

Phase 6 converts the cumulative specification into a functioning repository. The retained topology is implemented as:

- `apps/web`: Next.js 16 and React 19 player/review workbench;
- `services/api`: FastAPI session and HTTP orchestration;
- `python/grougal_solver`: deterministic tactical package boundary;
- `python/grougal_vision`: recognition package boundary;
- `packages/contracts`: generated cross-runtime schema inventory;
- `runtime/sessions`: private ephemeral analysis storage.

The implementation remains manual-first. The tactical solver consumes logical state only; uploaded pixels never enter movement or collision formulas.

## 70. Working analysis lifecycle

The implemented lifecycle supports:

1. token-protected analysis creation;
2. PNG/JPEG/WebP upload and safe image re-encoding;
3. normalised and thumbnail asset creation;
4. unconfirmed recognition proposals or a blank manual state;
5. versioned, idempotent editor commands;
6. solver preflight and deterministic search;
7. ordered recommendation and annotated PNG generation;
8. stale-write rejection;
9. immediate recursive deletion.

Sessions use a 60-minute idle expiry and six-hour hard expiry. The access token is returned once and only its SHA-256 digest is persisted.

## 71. Deterministic solver implementation

The Python implementation covers structural preflight, movement enumeration, resource commitment, definite/conditional graphs, end-turn collision resolution, capacity protection and deterministic ranking.

All 26 Phase-3 fixtures are exercised. Historical fixture assertions are interpreted according to their actual scope: listed roots, conditional dependencies, terminal outcomes and ordered candidate sequences. Exact whole-result status equality is applied only to fixtures whose catalogue data is globally unambiguous.

A technical timeout or node cap raises a capacity error and can never become `no_safe_solution`.

## 72. Editor, API and annotated output

The API implements the frozen `/api/v1` analysis, upload, command, solve, asset and deletion surfaces. Every state mutation increments `stateVersion`; duplicated command IDs are idempotent and stale versions fail with a stable conflict code.

The web workbench exposes the complete minimal vertical slice through French-first form controls. It can confirm proposals, set the player, add pillars, paint relative glyph offsets, set the action budget and spell availability, solve and display annotated output.

The underlying editor command layer also implements move, remove, reclassify, erase, undo and redo. Direct isometric canvas editing and complete browser exposure of every command remain Phase-7 UX work.

## 73. Recognition baseline and MODEL-001

The first recognition implementation is deliberately conservative:

- the retained 1951 × 1267 reference image loads its known Phase-2 manual encoding as unconfirmed proposals;
- other supported screenshots produce a valid blank manual state with registration required;
- `modelCalibrationStatus` remains `unvalidated`;
- `automaticCriticalConfirmation` is always `false`.

This baseline validates the integration boundary and correction flow. It is not a general detector and carries no accuracy claim.

## 74. Frontend and localisation state

The Next.js production build provides a single-page upload/review/solve workbench. French is the active player-facing locale and spell names remain canonical.

The complete French/German/English copy catalogue from Phase 5 is retained, but runtime locale switching and full browser wiring for German/English remain open. Mobile result reading is structurally possible; precision correction has not yet passed browser acceptance testing.

## 75. Privacy and operational implementation

The implemented default is ephemeral-only:

- no account or screenshot history;
- private per-analysis filesystem directory;
- token-protected assets and state;
- `Cache-Control: no-store` for analysis routes;
- persisted filename exclusion;
- immediate recursive deletion;
- no default evidence/training copy.

Readiness validates critical data files and their runtime hashes. Fixture mode fails startup in preview/production. The local filesystem store enforces the Phase-5 single-replica restriction.

## 76. Phase-6 test and performance result

The implementation was checked with:

- 7 passing Python automated tests;
- cumulative Phase-1–5 schema/specification validation;
- passing TypeScript type check;
- passing Next.js production build;
- zero known npm vulnerabilities after the locked PostCSS override;
- isolated Python dependency integrity check;
- Phase-6 runtime/manifest/performance validation.

Measured shared-container p95 samples were 1.060 ms for solver fixtures, 5,111.342 ms for reference-image normalisation, 1.322 ms for baseline recognition proposal generation, 5.487 ms for session mutation and 0.567 ms for deletion.

Docker was unavailable in the build environment. The packaged Compose path therefore remains unexecuted and must be reproduced during Phase 7. These measurements are engineering samples, not production or detector-quality claims.

## 77. Known implementation limits

Authoritative automatic solving remains blocked by:

- unresolved current-version mechanics V-001 through V-010;
- the provisional projection anchor;
- absence of locked-corpus validation for the new general registration/player/pillar baseline;
- absence of the locked adjudicated corpus;
- missing live-fight replay verification;
- incomplete direct-click editor and browser E2E/accessibility coverage.

Phase 6 exposed an action-budget shortcut of three actions. Phase 7A removes it: the current browser control starts unknown and accepts an explicit integer only. The API/domain state still remains unknown until supplied.

The normative limitation and defect registers are `docs/implementation/KNOWN_LIMITATIONS.md` and `DEFECT_BACKLOG.md`.

## 78. Phase-6 acceptance result and immediate next phase

Phase 6 is complete as the first pre-live implementation because a fresh repository can execute the manual upload-to-recommendation lifecycle, generate an annotated result, enforce state/version boundaries and delete every session byte. The core product no longer depends on a future detector to be testable.

Phase 6 does **not** authorize unattended screenshot recommendations, claim gameplay completeness or satisfy the locked validation gate.

**Immediate next phase: Phase 7 — Pre-Live Validation.**

Phase 7 must first reproduce the Docker/browser path, correct the fixture-oracle scope defects, collect current gameplay evidence and establish the locked screenshot corpus. Codex remains deferred until the Phase-7 entry gate in section 15.2 is satisfied.



## 79. Phase 7A — real screenshot fixture integration

Four additional current-style screenshots are retained unchanged as:

- `REAL-P7-01`;
- `REAL-P7-02`;
- `REAL-P7-03`;
- `REAL-P7-04`.

Each fixture records source path, original uploaded name, byte size, SHA-256, 2048 × 1151 raster dimensions, provenance, consent status, arena/UI regions, an offline registration annotation and conservative logical annotations. All four hashes are distinct. No embedded metadata proves the pre-upload desktop resolution, so possible upstream scaling is `unknown` and is not treated as an error.

The fixtures belong to one capture-session group. They must not be split across future training and validation sets.

## 80. Conservative annotations

For all four new screenshots, the controlled player and visible pillar cells/types are represented in logical coordinates. Glyph cells are classified only when visually clear; ambiguous or occluded cells are stored as unknown candidates.

The screenshots do not authoritatively determine:

- action budget;
- numeric spell charges;
- exact spell availability transitions;
- Crocoburio progress index;
- Grougalorasalar progress index;
- any open movement or resolution mechanic.

Those values therefore remain unknown under V-001, V-002 and V-006. A single screenshot never promotes a gameplay hypothesis.

## 81. Hybrid browser/server decision

The v0.8.0 executable path is hybrid.

The browser owns:

- immediate local preview;
- `createImageBitmap` decoding;
- bounded working-copy creation in a Web Worker;
- visible stage timing;
- progressive display of returned logical observations;
- immediate invalidation of stale result imagery after correction.

The API owns:

- cached ORB feature registration;
- RANSAC affine estimation;
- canonical warp;
- known-cell sampling;
- pillar and player classification;
- fixture-signature proposal lookup;
- the authoritative deterministic solver;
- protected annotated output.

A browser-local registration/classification port may replace the server path only after it proves logical equality, false-safe equivalence, acceptable cold payload and the 1.2-second local target on supported hardware.

## 82. Fast registration implementation

The registration engine loads reference ORB keypoints/descriptors once per API process. Each screenshot is downscaled to a working width between 960 and 1280 pixels. Distributed feature matches are filtered by a ratio test and fitted with a partial affine transform using RANSAC.

The executable baseline rejects registration when:

- fewer than 60 good matches exist;
- fewer than 40 inliers remain;
- inliers occupy fewer than three spatial regions;
- p95 residual exceeds 0.16 logical cell;
- a competing affine hypothesis is too close;
- scale is outside 0.45–1.60;
- absolute rotation exceeds 3 degrees.

The retained Phase-4 release thresholds remain stricter. Therefore a numerically accepted transform still produces review-required observations under `MODEL-001`.

## 83. Canonical cell classification

After registration, the screenshot is warped to the retained 1951 × 1267 canonical frame. Classification inspects only the known candidate cells and canonical board crop.

Pillars are extracted from the common pedestal/icon position using four calibrated colour/shape bands. Component centroids are converted to logical coordinates and rejected above 0.25-cell snap residual. Competing colour proposals on one cell are resolved by residual and expected component area. Pillar-set completeness still requires explicit confirmation.

The controlled player is found only on main-board candidate cells by scoring the blue unit-base patch around each logical cell centre. This prevents confusion with the lower Crocoburio runner.

## 84. Fixture-backed glyph proposals

A registered canonical image may be compared with cached fixture fingerprints. A unique match can load the versioned conservative glyph annotation for that known round. This supports demos and synthetic invariance tests.

Fixture matching is not a general glyph detector, does not auto-confirm any field and cannot be used as locked-corpus accuracy evidence. Unknown screenshots with unresolved glyphs enter targeted correction.

## 85. Performance targets and measurements

The current engineering targets are:

- visible feedback ≤ 100 ms;
- browser decode and working copy p95 ≤ 150 ms;
- registration p95 ≤ 400 ms;
- baseline recognition p95 ≤ 900 ms;
- deterministic solver p95 ≤ 50 ms;
- local screenshot-to-result p95 ≤ 1.2 seconds;
- server fallback p95 ≤ 2.5 seconds;
- hard timeout 5 seconds.

Warm-cache shared-container measurements in `reports/performance-phase7a.json` are:

- registration p95 298.714 ms;
- baseline recognition p95 757.498 ms;
- server screenshot-to-state p95 1,479.611 ms;
- solver p95 3.220 ms.

Browser-local decode, visible-feedback and full local timing are not yet measured. Cold engine initialisation is process startup work and is not repeated for each screenshot. These results are engineering samples, not production claims.

## 86. UI reaction and correction behaviour

The screenshot is displayed from a local object URL before network completion. A Web Worker reports decode, working-copy and preprocessing stages without blocking the page. If total analysis exceeds 1.2 seconds, the current concrete stage remains visible.

Recognised player, pillar count, glyph proposal count and active path are displayed progressively after the API response. Unresolved gates open the correction panel directly; no artificial loading page is inserted.

Any correction increments `stateVersion`, removes the prior recommendation, sets `recommendationInvalidated` and clears the previous annotated URL. Manual correction remains available but is not an obligatory extra step after the future automatic-confirmation gate is legitimately passed.

The former fixed action-budget button is removed. The current control starts unknown and accepts only an explicit integer from 0 to 12.

## 87. Phase 7A automated result

The current suite contains 19 passing Python tests and verifies:

- all five real screenshots enter the pipeline;
- all four new screenshots produce the annotated player and pillar set;
- 1920 × 1080, 2560 × 1440 and 3840 × 2160 variants preserve logical output;
- JPEG compression, small borders and small crops preserve the selected robustness fixture;
- non-arena input falls back safely;
- OCR is not invoked;
- templates are not reloaded per screenshot;
- registration/pixel data stay outside the solver state;
- uncertain observations cannot become safe recommendations;
- the Web Worker protocol is valid JavaScript.

TypeScript type checking and the Next.js production build pass. npm reports zero known vulnerabilities. Synthetic transforms are robustness tests only and do not replace independent beta evidence.

## 88. Phase 7A acceptance and immediate next phase

Phase 7A is complete because:

1. all four new screenshots are reproducible immutable fixtures;
2. each screenshot passes the new affine registration and known-cell pipeline;
3. resolution changes do not use hard-coded source pixels;
4. the solver receives logical data only;
5. the UI gives immediate local preview and real progress states;
6. every processing stage is timed;
7. automated real/synthetic/fallback tests execute;
8. previous Python tests remain passing;
9. no open fight rule or ambiguous UI value is invented;
10. status, decision, limitation, test and handoff documents are updated.

Phase 7A does **not** close full Phase 7. Automatic critical confirmation, authoritative gameplay recommendations and the Codex entry gate remain blocked.

**Immediate next phase: Phase 7B — Evidence, Browser E2E and Locked-Corpus Validation.**

## 89. Phase 7B — canonical arena evidence

Phase 7B adds two new evidence artefacts:

- an empty Grougalorasalar arena image without player, pillars or combat UI obstruction over the main board;
- a user-edited combat screenshot that manually restores outer cells hidden by foreground architecture and camera occlusion.

The user's earlier green-boundary annotation establishes one binding semantic rule: each green point marked the centre of the outermost included combat cell. The marked cell itself belongs to the arena and may contain a player, target or pillar.

The original byte file of that green annotation was not available in the active Phase-7B runtime. The explicit rule is retained as provenance rather than being silently discarded. The empty image, hidden-cell overlay, retained reference and four real combat screenshots provide the reproducible image set.

## 90. Canonical fixed footprint

The Grougalorasalar combat arena currently uses **338 unique integer cells as a provisional working set**. Boundary positions are not fully verified.

The coordinate set is the integer solution of:

```text
-12 <= x <= 13
-12 <= y <= 13
-11 <= x + y <= 13
-13 <= x - y <= 13
```

The enumerated file `data/arena/grougalorasalar.cells.json` is the source of truth. The inequalities are a compact reproduction and validation rule, not a substitute for the versioned cell list.

The footprint contains:

- 338 playable cells;
- 50 boundary cells;
- 104 exposed boundary edges;
- zero interior holes;
- zero asserted permanent blocked cells inside the footprint.

The former draft classes are superseded for arena-membership decisions. Their evidence history is retained per cell as provenance.

## 91. Independent cell-count proof

The final total is generated and tested three ways:

1. direct number of unique `(x, y)` coordinates: 338;
2. grouping by `x + y`: 25 rows alternating 14 and 13 cells, total 338;
3. grouping by `x - y`: 27 rows alternating 13 and 12 cells, total 338.

Any future mask change must make all three methods agree and must publish the changed coordinates and evidence. The number 338 is no longer a hard-coded visual guess.

## 92. Canonical parity contract

Floor parity is coordinate-derived:

```text
parity = (x + y) mod 2
```

- parity 0: light;
- parity 1: dark.

Every orthogonal logical neighbour must have the opposite parity. The empty arena image independently supports the assignment with median LAB-L values of 208.0 for zero parity and 182.5 for one parity, a 25.5-unit median separation.

Visible colour remains a cross-check because lighting, texture, objects and occlusion can alter screenshot pixels. It cannot override the logical parity formula.

## 93. Per-cell machine contract

Every canonical cell stores:

- deterministic numeric ID and stable string ID;
- logical `(x, y)`;
- parity;
- source authority and confidence;
- boundary flag and occlusion class;
- canonical reference-pixel centre;
- exact four-point isometric polygon;
- reciprocal orthogonal neighbours;
- provenance and superseded draft class.

IDs are sorted by `y`, then `x`. Tactical formulas use logical coordinates rather than sequential IDs.

## 94. Deterministic arena artefacts

Primary data and validation contracts:

```text
schemas/canonical-arena-cells.schema.json
schemas/canonical-arena-boundary.schema.json
data/arena/grougalorasalar.cells.json
data/arena/grougalorasalar.cells.csv
data/arena/grougalorasalar.boundary.json
data/arena/grougalorasalar.registration.json
data/arena/grougalorasalar.landmarks.json
```

Generated assets:

```text
assets/arena/grougalorasalar-mask.svg
assets/arena/grougalorasalar-mask.png
assets/arena/grougalorasalar-cell-centers.png
assets/arena/grougalorasalar-cell-polygons.png
assets/arena/grougalorasalar-debug-overlay.png
assets/arena/grougalorasalar-boundary-debug.png
assets/arena/validation/*.overlay.png
```

The JSON cell list is authoritative. Every SVG and PNG is regenerated by `scripts/build_canonical_arena.py`. Generative image tools are excluded from arena geometry creation.

## 95. Screenshot registration contract

The runtime exposes:

```python
register_screenshot_to_arena(image, project_root) -> RegistrationResult
registerScreenshotToArena(image, project_root) -> RegistrationResult
```

The fast path:

1. decodes the screenshot;
2. creates a bounded working copy;
3. extracts distributed ORB landmarks;
4. estimates the affine arena transform with RANSAC;
5. derives image-space origin and logical basis vectors;
6. projects all 338 canonical centres and polygons;
7. measures residuals and spatial coverage;
8. rejects or requests review when ambiguity remains.

Registration metadata remains outside `TurnState`. The solver receives no pixels or transforms.

## 96. Cross-image geometry result

Debug overlays are generated for:

- the retained canonical combat reference;
- the empty arena image;
- the user hidden-cell annotation;
- the four Phase-7 real combat screenshots.

All non-identity sources register below the 0.10-cell p95 geometry threshold. The empty arena p95 residual is 0.055749 cell; the hidden-cell annotation p95 residual is 0.054083 cell.

These results validate fixed-grid geometry across the current evidence set. They are not object-detector accuracy or independent locked-corpus results.

## 97. Phase-7B performance result

OpenCV registration is bounded to four threads after automatic thread selection proved slower and less stable on shared/container hardware.

Warm shared-container p95:

- arena registration: 169.442 ms;
- projection of all 338 centres: 0.047 ms;
- basic cell sampling: 0.096 ms;
- registration plus projection and sampling: 169.691 ms.

All isolated Phase-7B geometry targets pass in this environment. Supported-browser, production and clean-machine performance remain unverified.

## 98. Historical Phase-7B acceptance record — superseded

The following was the Phase-7B acceptance record before boundary refinement. It is retained for chronology and is superseded by Section 99:

1. one unambiguous 338-cell source-of-truth list exists;
2. every cell has stable logical coordinates and generated geometry;
3. three independent count methods agree;
4. every logical neighbour pair passes the parity invariant;
5. the user's outer-cell inclusion rule is applied;
6. hidden cells are promoted with explicit user provenance;
7. no cell remains `unresolved` in the footprint;
8. SVG and PNG files are reproducible from JSON;
9. the mask registers to all available real/reference screenshots;
10. runtime recognition uses all 338 cells while the solver remains pixel-free;
11. automated structural, registration and performance tests are provided;
12. cumulative status, decisions, changelog and handoff documents are updated.

Phase 7B does **not** close full Phase 7. It does not verify spell-specific edge behaviour, the projection anchor, V-001 through V-010, detector accuracy, browser E2E, clean Compose startup or the locked validation corpus.

**Immediate next phase: Phase 7C — Browser E2E, Gameplay Evidence and Locked-Corpus Validation.**

## 99. Boundary Refinement Addendum

The earlier 338-cell count is retained, but it is no longer treated as position proof. The interior lattice remains stable; every one of the 50 boundary cells now carries a separate authority and position record.

- confirmation requires at least two of: `user_boundary_annotation`, `user_hidden_cell_annotation`, `visible_empty_map`, `parity_geometric_consistency`;
- the missing byte-original green annotation is not counted per cell;
- architecture and rock edges are secondary evidence only;
- no symmetry, smoothing or aesthetic completion is allowed;
- 43 boundary cells are confirmed, 0 are accepted as purely inferred and 7 remain unresolved;
- unresolved cells: `C009`, `C016`, `C025`, `C064`, `C081`, `C168`, `C193`;
- all boundary cells have a regional visible-grid centre-distance record; no measured deviation exceeds `0.12` cell;
- the non-empty evidence review list forbids any 100% correctness claim;
- runtime registration may project all 338 candidates, but the solver-facing walkable set excludes unresolved boundary cells.

The controlling artefacts are `data/arena/grougalorasalar.cells.json`, `data/arena/grougalorasalar.boundary.json` and `VALIDATION/edge-review-report.json`.

Boundary acceptance is open. The immediate next step is the seven-cell evidence review defined in `NEXT_STEP.md`, not Phase 7C.
