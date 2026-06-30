# END-OF-TURN RESOLUTION ORDER

## Proposed state machine

```text
TURN_INPUT
  -> validate state
  -> validate rule profile
  -> apply action sequence
  -> determine final cell
  -> stationary check
  -> direct centre-glyph check
  -> project reference glyph offsets
  -> collect black collisions
  -> collect white collisions
  -> determine race outcome
  -> apply recharge timing
  -> produce next-turn resource state
```

## Known priority

When projected black and white glyphs both touch pillars, Grougalorasalar advances. This is explicitly stated by JeuxOnLine and is compatible with DofusPourLesNoobs.

## Direct centre glyphs

DofusPourLesNoobs states:

- finishing on the physical central black glyph advances the dragon;
- finishing on a physical central white glyph recharges the spells by one.

Still to verify:

- whether central black overrides projected white recharge completely or only race progress;
- whether central white restores all four spells or each active cursor;
- whether central white also advances Crocoburio when no black condition exists;
- whether recharge occurs before or after spell depletion is committed.

## No-collision case

DofusPourLesNoobs explicitly shows Crocoburio advancing when neither black nor white projected glyph touches a pillar. JeuxOnLine phrases the rule around white hits and is less explicit. The current status is `single_source_supported`, not multi-source verified.

## Stationary case

Both guides warn that remaining in place advances Grougalorasalar. The exact comparison point must be verified:

- same cell as turn start;
- same cell as previous resolution;
- no spell cast;
- or any combination.
