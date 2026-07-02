# CURRENT STATUS

**Version:** 1.0.0
**Date:** 2026-07-02
**Branch:** `codex/zero-input-enduser-flow`
**Status:** FUNCTIONAL ZERO-INPUT REGRESSION; NOT INDEPENDENTLY RELEASE-VALIDATED

## Implemented

- A paste uploads the original lossless screenshot, performs registration, player/pillar/glyph recognition, deterministic solving, overlay rendering, and returns one consistent response.
- Fixture identity is diagnostic only. `matchedFixtureId = null` no longer blocks solver readiness or provisional recommendations.
- Product states are distinct: `solved`, `provisional_solution`, `ambiguous_input`, `no_safe_solution`, `invalid_screenshot`, `blocked_missing_data`, and `capacity_error`.
- New fights start with 12 AP and `2/2/2/2` charges; following rounds reuse the staged `nextSpellState` only after the detected player matches the expected final cell.
- The normal route contains no manual controls, confidence list, timings, version label, pillar IDs, raw coordinates, or solve button. Debug controls remain at `/?debug=1`.
- The result shows numbered spell targets, movement, final-cell marker, hits, recharge, progress direction, next charges, and up to two alternatives.
- Glyph detection combines neutral-cell comparison, LAB and saturation deltas, gradient structure, cached reference-patch similarity, occlusion masking, and global four-phase scoring.
- Pillar components are cross-checked by an independent neutral-background per-cell structure scan.
- Production search uses exact Pareto dominance to discard states that cannot beat an otherwise identical position with more AP/charges. Fixture/property mode still enumerates the full diagnostic graph.

## Measured retained-corpus result

`VALIDATION/zero-input-release-report.json` records:

- 4/4 exact players;
- 4/4 exact pillar sets and types;
- 4/4 exact black and white glyph sets;
- 4/4 executable `provisional_solution` responses;
- 0 manual interactions and 0 observed false-safe regressions;
- pipeline p50 1320.436 ms, p95/max 1397.795 ms in the final recorded local run.

This is one fight/capture session. It is not an independent accuracy claim.

## Remaining release blockers

- Four expected real round-start screenshots and the original individual black/white glyph PNG bytes are absent from the repository.
- Full multi-round browser proof cannot use the retained sequence as an oracle because the recorded human end positions differ from the new solver's recommended final positions; continuity correctly rejects such a mismatch.
- Independent locked-corpus/beta validation, negative-image breadth, visual/accessibility regression, and seven arena-boundary cells remain open.
- Docker/browser verification must be reported from the current environment; no unexecuted check is considered passed.
