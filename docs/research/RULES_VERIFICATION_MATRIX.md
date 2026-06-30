# RULES VERIFICATION MATRIX

## Status codes

- **VM** — verified by multiple independent written sources
- **VD** — verified by direct current-version observation
- **SS** — supported by one source
- **OB** — observed in supplied screenshot
- **HY** — hypothesis
- **UN** — unknown

| Rule ID | Rule | Status | Current evidence | Needed to close |
|---|---|---:|---|---|
| R-001 | Fight is a race, not normal HP damage | VM | Both guides | Current run sanity check |
| R-002 | Controlled avatar has no normal PM | VM | Both guides | None for specification |
| R-003 | Four special movement spells exist | VM + OB | Both guides + screenshot colours | Current tooltip screenshots |
| R-004 | Pillars regenerate/change each turn | VM | Both guides | Before/after screenshots |
| R-005 | Central glyph pattern changes each turn | VM | Both guides | Before/after screenshots |
| R-006 | Pattern is projected relative to final player cell | VM | Both guides | Current replay |
| R-007 | Projected black on any pillar is adverse | VM | Both guides | Current replay |
| R-008 | Black has priority over simultaneous white hit | SS | JeuxOnLine explicit | Direct replay |
| R-009 | White hit recharges matching pillar spell | VM | Both guides | Exact charge delta |
| R-010 | Indécision targets contact cell and teleports | VM | Both guides | Contact metric and occupancy |
| R-011 | Reflet targets pillar at exact range 2 | SS | DofusPourLesNoobs explicit | Tooltip/current cast |
| R-012 | Reflet destination is symmetric across pillar | VM | Both guides | Edge/occupancy cases |
| R-013 | Rejet targets pillar at range 1–2 | SS | DofusPourLesNoobs explicit | Tooltip/current cast |
| R-014 | Rejet moves player 3 cells away | VM | Both guides | Blocking/truncation |
| R-015 | Attrait targets pillar at range 1–6 | SS | DofusPourLesNoobs explicit | Tooltip/current cast |
| R-016 | Attrait moves player 3 cells toward pillar | VM | Both guides | Short-range behaviour |
| R-017 | Attrait is line-only | SS | Guide wording/baseline | Current tooltip/cast |
| R-018 | Player may not finish on same cell | VM | Both guides | Exact comparison semantics |
| R-019 | No black and no white collision advances Crocoburio | SS | DofusPourLesNoobs example | Direct replay |
| R-020 | Physical central black cell is adverse | SS | DofusPourLesNoobs note | Direct replay |
| R-021 | Physical central white cell recharges spells by 1 | SS | DofusPourLesNoobs note | Scope and timing |
| R-022 | Dragon loses race after 8 advances | VM | Both guides | Visual track index check |
| R-023 | Crocoburio needs 13 cells | SS | JeuxOnLine | Current full run |
| R-024 | Crocoburio needs 14 cells | SS | DofusPourLesNoobs | Current full run |
| R-025 | Spell gauges can make spells unavailable | VM + OB | Both guides + screenshot | Exact thresholds |
| R-026 | Each cast consumes one AP | SS | Phase-0 guide interpretation | Current tooltips/log |
| R-027 | Total action budget per turn | UN | No reliable evidence | Visible AP and action log |
| R-028 | Multiple casts per turn are possible | SS | Guide wording/gauge design | Current recording |
| R-029 | Numeric initial/max charge per spell | UN | None | Full run from start |
| R-030 | One white pillar equals one charge | HY | Plausible wording | Before/after gauge |
| R-031 | Multiple white pillars stack recharge | HY | Guide recommends one or more | Controlled observation |
| R-032 | Recharge applies after end-turn resolution | SS | “for a next turn” wording | Gauge frame timing |
| R-033 | Movement passes through pillars | UN | None | Targeted edge case |
| R-034 | Occupied destinations are invalid | UN | Generic expectation only | Targeted edge case |
| R-035 | Displacement truncates at edge/obstacle | UN | None | Targeted edge case |
| R-036 | Multiplayer shares spell state | SS | 2026 forum report | Independent current tests |
| R-037 | Supplied screenshot contains four lower gauges | OB | Screenshot | None |
| R-038 | Lower-left runner is Crocoburio, not player | VM + OB | Guide + screenshot | None |

## Phase-1 conclusion

No rule required for ordinary glyph evaluation is completely absent, but movement legality and resource transitions still contain enough uncertainty to block a trustworthy automated solver. These unknowns are now isolated and testable rather than hidden.
