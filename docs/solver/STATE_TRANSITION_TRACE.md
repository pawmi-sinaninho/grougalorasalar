# STATE TRANSITION AND TRACE CONTRACT

## Event order

Each candidate trace uses monotonically increasing event indices and this order:

1. `preflight`;
2. `root_enumeration`;
3. for each cast: `cast_cost`, `charge_cost`, `movement_formula`, `path_resolution`, `destination_validation`;
4. `end_turn`;
5. `stationary_check`;
6. `center_check`;
7. `glyph_projection`;
8. `collision_collection`;
9. `race_resolution`;
10. `recharge_resolution`;
11. `next_state`;
12. `candidate_ranking`;
13. `final_status`.

Every event names the rule IDs that justify it. Empty `ruleIds` is allowed only for product-level bookkeeping.

## State mutation rules

- Source cell for action `n+1` equals resolved destination of action `n`.
- Action budget and numeric charge cost are committed before movement resolution.
- A definitely invalid action produces no child state.
- A conditional action produces a diagnostic branch, not an authoritative child.
- Glyph collision is evaluated only once, after explicit end turn.
- Recharge never enables another cast in the already-ended turn.

## Projection

For final cell `P` and offset `g`:

```text
projected = P + g
```

Black and white collisions are arrays of stable pillar IDs sorted ascending. Duplicate offsets are invalid input.

## Race outcome

An adverse condition is any configured stationary penalty, central-black penalty or projected-black collision. When black priority is true, any adverse condition decides race direction before white-only outcomes.

If both direct black and direct white physical cells contain the final cell, the state is invalid because a physical cell cannot be both colours.

## Recharge

Matching white-pillar recharge is grouped by `spellType`. When stacking is false, each spell receives at most one recharge unit. When stacking is true, every matching hit contributes. Unknown stacking is blocking only when two or more hits of the same spell type occur.

`rechargeWhenAdverse` determines whether positive resource effects survive an adverse race resolution.

## Next state

The trace reports the post-turn resource state. It does not fabricate the next turn's pillars, glyph pattern or player screenshot.
