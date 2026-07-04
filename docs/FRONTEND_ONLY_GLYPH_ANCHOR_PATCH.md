# Frontend-only Glyph Anchor Patch

This patch replaces the browser-local glyph phase detector.

## Why

The previous browser detector found the arena grid and the player, and detected roughly the expected pillar count, but rejected valid screenshots with:

```text
glyph_detection_low_confidence
```

The detector was too dependent on a centre-origin glyph scan. In-game, the tactical pattern used by the solver is relative to the player/final position, so the first browser-local hypothesis should be anchored on the detected player cell.

## Changes

- Detect the player before pillars.
- Filter/cap local pillar candidates.
- Detect glyph phase anchored at the detected player cell first.
- Keep arena-centre glyph scanning as fallback.
- Use both dark and bright low-saturation evidence instead of requiring black-only observations.
- Allow low-confidence glyphs to produce a provisional tactical state instead of immediately triggering `Capture incomplète`.
- Add debug fields:
  - `glyph_template`
  - `glyph_anchor_cell`
  - `glyph_scores`
  - `pillars_raw_detected`
  - `player_candidate_cells`

## Expected next result

The normal failure should no longer be `glyph_detection_low_confidence` for screenshots where grid/player/pillars are already detected.

If the solver still cannot recommend an action, the next debug reason should come from the local solver, not the image pipeline.
