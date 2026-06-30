# ARCHITECTURE SUMMARY — v0.6.0

```text
Screenshot
   |
   v
Ingest + arena-presence gate
   |
   v
Board registration -----------------------------+
   |                                             |
   v                                             |
Visual observations + confidence + alternatives |
   |                                             |
   v                                             |
Correction / confirmation UX <------------------+
   |       |                                     |
   |       +--> immutable detector proposal      |
   |       +--> manual override audit            |
   v                                             |
Confirmed TurnState -----------------------------+
   |
   v
RulesProfile validation
   |
   v
Deterministic action enumeration
   |
   +--> blocked_unverified_rule
   +--> confirmation_required
   +--> no_safe_solution
   +--> solved
   |
   v
Annotated screenshot + executable action list
```

## Logical boundaries

### Web client

- upload or paste screenshot;
- show arena-presence and registration status;
- render the logical overlay;
- expose proposed values, alternatives and confidence;
- allow all field corrections;
- preserve recognition and manual audit;
- invoke the solver only after the visual gate passes.

### Vision service

- validate file and arena presence;
- estimate board transform and UI-region transforms;
- extract player, pillars, glyphs, resources and progress;
- emit `VisualObservation` records and conflicts;
- calculate confidence under the versioned policy;
- never decide tactics or silently promote unvalidated fields.

### Arena model

- logical axes and candidate cells;
- visual/evidence authority per cell;
- projection anchor status;
- stable map landmarks and calibration metadata;
- no combat-rule decisions.

### Correction service / editor

- imports a `RecognitionResult`;
- accepts, corrects or rejects individual observations;
- records set-completeness confirmation separately from object confirmation;
- exports a schema-valid `TurnState` and `ManualEditorSession`.

### Rules and solver service

- accepts logical state only;
- validates `TurnState` against `RulesProfile`;
- generates definite and conditional action graphs;
- returns exact statuses, ranking and trace;
- never receives pixel coordinates.

### Evidence and evaluation store

- stores consent-scoped screenshots or redacted derivatives;
- stores annotations, model/policy versions and split groups;
- prevents train/test leakage by capture session;
- reports accuracy, coverage, rejection and false-safe metrics separately.

## Non-negotiable separation

1. Pixel evidence cannot enter movement formulas.
2. Numeric confidence cannot override a failed critical-field gate.
3. User confirmation does not alter detector confidence.
4. A visual confirmation does not promote a mechanical rule.
5. An unvalidated model cannot auto-confirm solver-blocking fields.
6. Any state edit invalidates the previous recommendation.

## Phase-5 implementation boundary

The frozen repository/process/package ownership, lifecycle, API and deployment design are defined in `PRE_LIVE_TECHNICAL_BLUEPRINT.md`.

## Current implementation status

The repository is still a specification package. It contains schemas, policies, fixtures and validation scripts, not a production detector, editor or website. Phase 6 is the first implementation phase.
