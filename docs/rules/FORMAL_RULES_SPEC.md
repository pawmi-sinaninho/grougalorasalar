# FORMAL RULES SPECIFICATION

## 1. Scope

This document defines the binding `dofuspourlesnoobs-observed-v1.0.0` combat model. Older conflicting hypotheses are superseded.

## 2. Coordinate system

Use a square logical grid with integer coordinates `(x, y)`.

### Relations

```text
orthogonally_adjacent(a, b): |dx| + |dy| = 1
same_axis(a, b): dx = 0 or dy = 0
diagonal_aligned(a, b): |dx| = |dy|
manhattan_range(a, b): |dx| + |dy|
chebyshev_range(a, b): max(|dx|, |dy|)
```

The screen is isometric, but tactical geometry remains a square grid. Phase 2 will lock the correspondence between logical axes and screenshot directions.

## 3. Core entities

### ArenaModel

- `arenaModelId`
- `walkableCells`
- `permanentBlockedCells`
- `projectionAnchorCell`
- optional screenshot-calibration metadata stored separately

### TurnState

- current player cell;
- previous player cell;
- pillar list with logical cells and spell types;
- black and white glyph offsets;
- action-point or cast-budget state;
- per-spell resource state;
- Crocoburio and dragon progress;
- multiplayer detection flag;
- field-level confidence and confirmation state.

### RulesProfile

Contains every mechanic that can change legality or outcome. A profile has an authority status and may contain unknown values.

## 4. Spells

All four movement spells are treated as state transitions. Each action records source, target, destination, resource cost and rejection reason.

### R-010 — Indécision

Contract:

```text
target is orthogonally adjacent to source
candidate destination = target
```

The target must be inside the arena and free. Diagonal, pillar-occupied and obstacle cells are illegal.

### R-020 — Reflet

Target an any-colour pillar on the exact Manhattan-distance-2 ring and move symmetrically across it. The eight possible relative target cells are `(±2,0)`, `(0,±2)` and `(±1,±1)`.

Base formula:

```text
source = P
target pillar = T
destination = 2*T - P
```

The movement may not cross another pillar or obstacle. The destination must be free and inside the arena.

### R-030 — Rejet

Supported description: target an any-colour pillar at aligned range 1–2 on one of the eight cardinal or diagonal rays; finish at radius three from a cardinal target or radius two from a diagonal target.

For an allowed alignment, let `u` be the unit vector from pillar to player:

```text
u = normalise_cardinal_or_diagonal(P - T)
destination = P + 3*u
```

Cardinal and diagonal alignment are legal. Rejet's `3/2` value is measured from the target pillar to the destination, not added to the player's source cell. For target distance `d`, displacement is `3-d` cardinal cells or `2-d` diagonal cells in the direction away from the pillar. Every traversed cell must be free and inside the arena. A blocker or arena edge makes the cast illegal; Rejet never truncates.

### R-040 — Attrait

Target an any-colour pillar at range 1–6 on one of the four cardinal lines and move up to three cells toward it. Diagonal targets are illegal.

For an allowed alignment, let `u` be the unit vector from player to pillar:

```text
u = normalise_cardinal(P -> T)
raw_destination = P + 3*u
```

When the pillar is closer than three steps, stop on the free cell immediately before it. The complete target ray must be clear: another pillar or obstacle anywhere between player and target makes the cast illegal, even beyond the three-cell movement destination.

## 5. Occupancy and paths

A destination is always checked against the arena mask and must be free. Pillars and permanent obstacles block intermediate movement; movement spells do not truncate before a blocker or edge.

Typed rejection reasons include:

- `target_out_of_range`;
- `target_wrong_alignment`;
- `target_not_pillar`;
- `target_wrong_pillar_type`;
- `spell_unavailable`;
- `insufficient_action_budget`;
- `destination_off_map`;
- `destination_blocked`;
- `path_blocked`;
- `required_rule_unknown`.

## 6. Glyph projection

For final player cell `P` and offset `g=(dx,dy)`:

```text
projected_cell(P, g) = (P.x + g.dx, P.y + g.dy)
```

A projected cell collides with a pillar when a pillar occupies the same logical cell.

```text
black_hits = pillars ∩ projected_black_cells
white_hits = pillars ∩ projected_white_cells
```

A white hit recharges the spell represented by the struck pillar, subject to the resource profile.

## 7. End-of-turn resolution

The following precedence is safe and supported enough to specify, but individual entries still carry authority levels:

1. Reject an invalid or unresolved state before tactical evaluation.
2. Evaluate direct physical centre-glyph effects at the final cell.
3. Evaluate black and white offsets relative to the final player position.
4. Any projected black collision takes priority for race progress.
5. If no projected black collision exists, Crocoburio advances.
6. Resolve every matching white recharge after cast depletion, including during a black-priority result.
7. Cap every spell at four charges.
8. Generate the next-turn resource state.

The solver trace must show which condition decided the outcome.

## 8. Resource model

Every turn starts with 12 AP and every cast immediately costs 1 AP. Every spell starts combat with 2 charges, costs 1 charge per cast and has maximum 4. A spell at 0 is unusable. End-of-turn state is:

```text
nextCharges = min(4, chargesAtTurnStart - castsThisTurn + matchingWhiteHits)
```

Charges may never become negative during the action sequence. Automatic vision may report positive availability without fabricating an exact positive count when the gauge is not numerically calibrated.

## 9. Search contract

The search enumerates sequences until:

- action budget is exhausted;
- no legal action exists;
- the user explicitly ends the turn.

Candidate ranking is lexicographic:

1. require at least one movement and reject every projected/direct black outcome;
2. minimize casts and therefore charges spent this round;
3. among equally short sequences, maximize the minimum and total next-turn charges;
4. prefer Crocoburio progress over a neutral safe ending;
5. prefer next-turn geometric mobility;
6. use the canonical sequence as deterministic tie-break.

Touching a white glyph is optional. A moved ending touching neither black nor white remains legal and can win when it uses fewer charges.

A candidate that depends on an unknown rule is not `solved`; it is `confirmation_required` or `blocked_unverified_rule`.

## 10. Solver output classes

- `solved`: all critical fields and mechanics are verified or directly confirmed.
- `confirmation_required`: a supported but not fully verified assumption needs user approval.
- `blocked_unverified_rule`: outcome changes depending on an unknown mechanic.
- `no_safe_solution`: all legal verified endings are adverse.
- `invalid_state`: the input is internally contradictory.
