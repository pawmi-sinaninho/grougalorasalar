# CONFIDENCE, CONFLICT & SOLVER-GATING MODEL — Phase 4

## 1. Principle

Confidence is a calibrated estimate of visual correctness, not a decorative score. Confirmation is a separate state. A user can confirm a low-confidence value; that action changes the gate state, not the detector confidence.

## 2. Component scores

Each visual observation contains five scores in `[0,1]`:

- `primary` — detector/classifier evidence;
- `registration` — transform reliability at the observed region;
- `snapMargin` — separation from the next logical-cell or class alternative;
- `visibility` — crop, occlusion and image-quality assessment;
- `crossCheck` — independent validation agreement.

The base confidence is the weighted geometric mean:

```text
Cbase = primary^0.35
      * registration^0.20
      * snapMargin^0.15
      * visibility^0.15
      * crossCheck^0.15
```

A missing cross-check receives score zero and invokes the single-source cap; it is not silently replaced by one.

## 3. Hard caps

After the base calculation, apply the lowest applicable cap:

| Condition | Maximum confidence |
|---|---:|
| unresolved method conflict | 0.39 |
| out-of-distribution input | 0.49 |
| cell snap margin below 0.15 cell | 0.69 |
| partial occlusion without temporal support | 0.74 |
| no independent cross-check | 0.79 |

The cap prevents a strong detector score from hiding a critical weakness.

## 4. Field thresholds

Normative thresholds live in `data/vision/recognition-policy.v0.5.0.json`. Black glyph, projection anchor and action budget use the strictest thresholds because one error can reverse or invalidate the recommendation.

Threshold outcomes:

- at or above auto-confirm threshold: eligible for automatic confirmation only after the locked-corpus gate passes;
- between review minimum and auto-confirm threshold: review required;
- below review minimum: missing/rejected and explicit correction required.

## 5. Calibration lock

Before Phase-7 validation, `modelCalibrationStatus = unvalidated`. In that state:

- no automatically extracted solver-blocking field is trusted silently;
- all such fields require user confirmation;
- confidence values are still displayed and recorded for evaluation;
- manually encoded fixtures remain valid evidence but not model-accuracy proof.

This avoids circular validation in which the detector approves its own output.

## 6. Conflict classes

### Structural conflicts

Examples:

- player and pillar on one cell;
- duplicate pillars;
- one glyph cell classified black and white;
- transform maps a confirmed object outside all permitted arena cells.

Effect: blocker until corrected.

### Method conflicts

Examples:

- pillar colour classifier says red while icon template says green;
- two registration hypotheses are nearly tied;
- player detector and unit-base detector snap to different cells.

Effect: confidence cap 0.39 and review.

### Temporal conflicts

Examples:

- progress appears to move backwards;
- a prior persistent spell slot identity swaps position unexpectedly.

Effect: review warning unless the current screenshot alone is structurally impossible. Temporal evidence never overrides a clear current screenshot.

### Model-policy conflicts

A field may exceed its numeric threshold while auto-confirmation is disabled. The gate remains review-required with `MODEL-001`.

## 7. Aggregate confidence

`TurnState.confidence.overall` is the minimum of confirmed solver-blocking field confidences, not an arithmetic mean. Missing critical fields set the overall value to zero.

This value is useful for ranking otherwise equal candidates but cannot override a failed gate.

## 8. Solver gate

`ready_for_solver` requires:

- confirmed arena presence and registration;
- confirmed solo state;
- confirmed player cell;
- confirmed complete pillar set and each pillar type/cell;
- confirmed black set, white set and projection anchor;
- resolved action budget under Phase-3 precedence;
- spell state sufficient for the active resource mode;
- no open blocker conflict.

Progress is terminal-only: missing progress does not block movement advice but changes the terminal fight state to unknown.

## 9. False-safe definition

A **critical false-safe** occurs when the system reaches `ready_for_solver` and returns a recommendation while any wrong visual field changes:

- legal action availability;
- destination;
- black/white collision result;
- recharge/ranking winner;
- claimed immediate win/loss.

The locked-corpus tolerance is zero. A correct recommendation produced from a wrong state is still counted as false-safe because it is not reproducible or trustworthy.
