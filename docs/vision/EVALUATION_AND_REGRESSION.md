# VISION EVALUATION & REGRESSION SPECIFICATION — Phase 4

## 1. Evaluation levels

### Component level

Measure registration, player, pillars, glyphs, resources and progress independently.

### State level

Measure exact match of the complete solver-critical visual state.

### End-to-end level

Run the recognised state through the deterministic solver and count critical false-safe recommendations.

A component can have high average accuracy while still failing the end-to-end safety gate.

## 2. Required metrics

Normative targets are stored in `data/vision/evaluation-targets.v0.5.0.json`.

Minimum report:

- arena false-accept rate;
- registration residual distribution and rejection rate;
- player exact-cell accuracy;
- pillar set exact match, cell precision/recall and type accuracy;
- black and white glyph exact-set accuracy;
- action-budget and spell-state exact accuracy on auto-confirmed subsets;
- progress index accuracy;
- confidence calibration error;
- review recall for ambiguous critical cases;
- critical false-safe count;
- auto-confirm coverage.

## 3. Slicing

Every metric is sliced by:

- resolution family;
- window mode;
- UI scale;
- language;
- client version;
- compression;
- occlusion status;
- model and policy version.

No overall metric may hide a failing supported slice.

## 4. Auto-confirmation entry gate

Automatic confirmation remains disabled until all are true:

- at least 150 adjudicated locked-test screenshots;
- at least 15 independent capture sessions;
- at least 20 screenshots for each claimed supported resolution family;
- zero arena false accepts on the locked negative corpus;
- zero critical false-safe recommendations;
- all field-specific targets pass;
- confidence calibration target passes;
- review recall for ambiguous critical cases is 100%.

Failure disables auto-confirmation for the failing field or slice, not necessarily the entire manual-review workflow.

## 5. Regression suite

Each code or model change runs:

1. schema and policy validation;
2. the 20 visual contract fixtures;
3. Phase-2 arena regression;
4. Phase-3 solver regression;
5. frozen component-image fixtures where consent permits;
6. locked-corpus evaluation in a protected pipeline;
7. end-to-end solver comparison.

A change is rejected when it:

- increases critical false-safe count above zero;
- lowers an accepted slice below target;
- changes a gold logical state without an approved annotation correction;
- changes solver output for an unchanged logical state;
- increases coverage by bypassing review gates.

## 6. Error taxonomy

Each defect receives one primary class:

- ingest false accept/reject;
- registration drift or wrong hypothesis;
- missed/extra player;
- missed/extra pillar;
- pillar-cell error;
- pillar-type error;
- black-glyph error;
- white-glyph error;
- resource error;
- progress error;
- confidence miscalibration;
- UX correction failure;
- solver integration error.

The defect log records whether the error was caught by review. Errors caught before solving are safety successes but still accuracy defects.

## 7. Reporting rule

Accuracy and coverage are always reported together. A detector that auto-confirms only easy cases may be safe but low-coverage; this is acceptable for pre-live. It is not acceptable to call rejected or manually corrected cases “correct automatic detections.”
