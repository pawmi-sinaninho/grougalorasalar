# CONFIDENCE & CORRECTION UX — Phase 4

## 1. Goal

Convert uncertain detections into a verified logical state with the fewest necessary user actions, while making every safety-relevant ambiguity visible.

## 2. Screen order

### A. Upload result

Show one of:

- arena recognised;
- manual alignment required;
- screenshot rejected with one concrete remedy.

Do not show a tactical recommendation at this stage.

### B. Board review

Render the registered logical grid over the screenshot with:

- player marker;
- numbered pillar markers coloured by spell type;
- black and white glyph cells;
- uncertainty badges only on affected items.

### C. Resources and progress

Show four spell states, action budget and both progress tracks. Missing optional progress is visually separated from solver-blocking resource gaps.

### D. Final verification

List only unresolved items first, ordered by tactical impact:

1. black glyph;
2. player and registration;
3. missing/extra pillars;
4. pillar types;
5. action budget and spell states;
6. white glyph;
7. progress.

## 3. Visual states

- **confirmed** — solid marker with check;
- **review required** — amber outline and question badge;
- **conflict** — red split marker showing alternatives;
- **missing/not visible** — empty placeholder with direct input control;
- **manual override** — confirmed marker plus audit icon.

Colour is never the only signal.

## 4. Correction interactions

### Registration

Drag origin, `+x`, `+y`, then verify two residual points.

### Player

Click the correct logical cell. The UI shows the current and next-best candidate before replacement.

### Pillars

- click empty cell to add;
- drag marker to move;
- select one of four types to reclassify;
- delete extra pillar;
- “set complete” confirmation is separate from confirming individual pillars.

### Glyph pattern

Use black, white and erase tools on the physical centre cells. Black and white cannot overlap. Changing the anchor previews recomputed offsets before commit.

### Resources

Select availability or enter numeric value per spell. Action budget is an explicit integer/unknown control.

### Progress

Select a track cell or leave unknown. The UI explains that unknown progress affects terminal claims, not necessarily movement advice.

## 5. Confirmation semantics

A generic “looks good” button is insufficient for critical ambiguities. Confirmation records:

- field path;
- proposed value;
- confidence at confirmation time;
- alternatives shown;
- user action;
- timestamp in implementation;
- detector/policy version.

Bulk confirmation is allowed only for fields already above their review threshold and without conflicts. Black glyph cells, pillar-set completeness and registration may not be bulk-confirmed while the model is unvalidated.

## 6. Solver button states

- `Analyse prüfen` — unresolved visual fields;
- `Regeln ungeklärt` — visual state complete but Phase-3 mechanic blocks;
- `Zug berechnen` — solver gate ready;
- `Screenshot unbrauchbar` — rejected input.

The button label states the next real action rather than displaying a disabled generic CTA.

## 7. Annotated recommendation handoff

After solving, the visual overlay uses only the confirmed transform and state. If progress is unknown, the result must say that the recommended movement is computed but an immediate win/loss cannot be confirmed.

Any post-solve state edit invalidates the recommendation and requires recomputation.

## 8. Accessibility and speed

- full keyboard access for cell tools;
- zoom does not change logical coordinates;
- all uncertainty states have text labels;
- mobile review may be supported later, but V1 authoring assumes desktop precision;
- undo/redo covers recognition acceptance and every manual correction.
