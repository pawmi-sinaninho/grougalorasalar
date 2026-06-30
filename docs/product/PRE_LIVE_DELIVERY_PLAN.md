# PRE-LIVE DELIVERY PLAN

## Operating model

The project is developed in structured phases inside ChatGPT until a functional pre-live version exists. Codex is reserved for later refinement.

## Phase sequence

### Phase 0 — Discovery baseline — complete

Mechanics, architecture, scope and uncertainties.

### Phase 1 — Formal domain model and verification framework — complete

Rule vocabulary, evidence statuses, safe uncertainty handling, schemas and delivery strategy.

### Phase 2 — Arena digital twin and manual editor specification — complete as draft

Fixed logical axes, draft arena mask, manual reference encoding and human state-entry workflow.

### Phase 3 — Solver behaviour and test-oracle specification — complete

Complete legal-action generation, ranking, traces, impossible states and fixture design.

### Phase 4 — Screenshot recognition and confidence UX specification — complete

Canonical transform, object extraction, correction flow, dataset and metrics.

### Phase 5 — Full pre-live technical and visual specification

Repository, API, pages, components, copy, privacy, deployment and acceptance tests.

### Phase 6 — First pre-live implementation

Build a functioning local or preview deployment with manual correction and at least a baseline detector. The implementation method remains independent from Codex.

### Phase 7 — Pre-live validation

Community or controlled tests, replay corpus, defect classification, measured accuracy and known limitations.

### Phase 8 — Codex refinement

Codex receives the working repository plus test corpus and defect backlog. Tasks include:

- codebase audit;
- refactoring;
- performance optimisation;
- missing tests;
- browser and resolution robustness;
- security and privacy review;
- final UX polish.

### Phase 9 — Closed beta and production hardening

Deployment, observability, rate limiting, support workflow and release gate.

## Codex entry gate

Codex may not start until all are true:

- the app starts locally using documented commands;
- one screenshot can be entered and converted to a turn state;
- manual correction works;
- the deterministic solver returns a trace;
- at least 25 structured fixtures exist;
- automated tests run;
- known rules are separated from assumptions;
- a defect backlog exists;
- a current master specification is included.

## Why this order matters

Starting Codex earlier would optimise an unstable rules model and increase rework. The later entry point gives it concrete code, measurable failures and objective acceptance tests.

## Phase-3 refinement

The first executable solver must implement the canonical action signatures, status policy and ranking policy from v0.5.0 before recognition work is connected. Conditional branches must remain inspectable in developer mode.



## Phase-4 refinement

The first implementation must keep automatic confirmation disabled. It may use deterministic/template baselines and manual correction, but every solver-blocking field must pass the Phase-4 gate. Board and UI registration are separate, and pillar-set completeness must be represented explicitly.
