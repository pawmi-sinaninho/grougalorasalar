# VISUAL OBSERVATION EXTRACTION CONTRACT — Phase 4

## 1. Boundary

The recognition layer produces observations and a draft `TurnState`. It never decides which action is tactically best. Every observation carries provenance, confidence, alternatives and a correction route.

## 2. Common extraction sequence

For every field:

1. produce one or more candidates;
2. map pixel candidates to logical cells where applicable;
3. run at least one independent cross-check where feasible;
4. calculate field confidence;
5. detect conflicts;
6. apply the field-specific gate;
7. expose the value and alternatives to the correction UI.

A detector probability is not itself the final confidence.

## 3. Controlled player

### Primary method

Compact instance detector or template bank over the registered board, followed by logical-cell snap.

### Cross-checks

- unit-base or selection-cell geometry;
- expected sprite footprint above the snapped cell;
- exactly one controlled board avatar;
- distinction from the Crocoburio runner on the lower track.

### Conflict rules

- two near-equal cells → review;
- player on a pillar cell → blocker conflict;
- no player → review, not default placement;
- multiple controlled board avatars → multiplayer rejection.

## 4. Pillars

Pillar extraction has two separate obligations:

1. detect every pillar instance and cell;
2. prove that the set is likely complete.

### Primary instance method

Detect the common pedestal/base shape, then snap each base centre to a logical cell.

### Spell-type classification

Classify the top icon patch as:

- `indecision` / cyan;
- `reflection` / green;
- `repulsion` / yellow;
- `attraction` / red.

Colour alone is insufficient. The icon shape/template must provide an independent signal to reduce errors caused by lighting, compression or colour profiles.

### Completeness cross-check

Run a cell-wise occupancy scan over every visible candidate cell. Any high pillar-likeness cell not matched to an instance lowers `pillarSet.confidence` and sets `completenessStatus = possibly_incomplete`.

### Invariants

- no duplicate pillar cell;
- no pillar on the player cell;
- stable IDs after manual move or recolour;
- out-of-mask detections require boundary confirmation;
- count is not hard-coded to 27.

## 5. Central glyph pattern

The physical central pattern is classified cell-by-cell after registration.

### Classes

- black;
- white;
- neutral floor;
- occluded/unknown.

### Primary method

Registered cell-patch classifier using luminance, local contrast and tile-edge evidence.

### Cross-checks

- direct comparison with a neutral-floor model;
- mutual exclusion of black and white;
- physical cell to logical-offset round trip;
- consistency with the configured projection anchor.

Black and white sets receive separate confidence and confirmation. A single uncertain black cell blocks solving because it can reverse the race result. An uncertain white cell also blocks the authoritative Phase-3 solver because it can change recharge and candidate ranking.

## 6. Projection anchor

The anchor is arena metadata, not inferred anew from the current glyph pattern. Recognition validates that the registered anchor lands on the expected central region. Until independent live evidence promotes the anchor, `anchorConfirmed = false` remains a solver blocker regardless of visual score.

## 7. Multiplayer state

The detector counts controlled board avatars, not initiative portraits or progress runners. Any credible second controlled board avatar rejects V1 solving. Ambiguous multiplayer state requires manual confirmation.

## 8. Action budget

Preferred extraction order:

1. locate the action-budget UI using a UI-specific transform;
2. read the displayed value using glyph-template matching or constrained OCR;
3. cross-check against visible cast slots or another independent UI cue when available.

Ordinary DOFUS AP defaults are forbidden as a fallback. If the value is not visible, the UI requests manual entry or uses an authoritative `RulesProfile` value under Phase-3 precedence.

## 9. Spell state

For each of the four spell slots, extract:

- icon identity;
- availability (`available`, `unavailable`, `unknown`);
- numeric value when shown;
- confidence and visibility.

Primary signals may include icon desaturation, gauge fill/cursor geometry and numeric text. The four slots are bound by icon identity rather than fixed horizontal order alone.

A partially occluded slot remains unknown. The system must not copy the state from another spell or a prior screenshot without showing that temporal inference explicitly.

## 10. Progress tracks

Track extraction is separate for Crocoburio and Grougalorasalar:

1. locate the coloured track;
2. detect the runner sprite/base;
3. snap to a visible track cell;
4. store index and confidence.

Progress may use previous-turn monotonicity as a cross-check, never as the sole source. Unknown progress allows a per-turn race-direction statement but prevents a definite immediate-win or immediate-loss claim.

## 11. Turn number

Turn number is advisory. OCR failure does not block solving. It may be used for session ordering and evidence review only.

## 12. Output mapping

All observations are stored as `VisualObservation` records. The draft `TurnState` stores confirmed values plus aggregate visual provenance. Manual changes create new audit entries and mark the corresponding observation as overridden; they do not delete the original proposal.
