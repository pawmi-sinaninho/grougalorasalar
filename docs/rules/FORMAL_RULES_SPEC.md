# FORMAL RULES SPECIFICATION

## 1. Scope

This document defines the logical combat model without claiming that every game mechanic is already verified. Exact unknowns are represented in `RulesProfile`.

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

Supported description: target one contact cell and teleport to it.

Candidate contract:

```text
target is orthogonally adjacent to source
candidate destination = target
```

Unresolved:

- whether diagonal contact is legal under the fight's range metric;
- whether line of sight is checked;
- whether a pillar-occupied target is rejected;
- whether the spell is restricted by visual facing.

The current product assumption is **not** allowed to silently choose among these.

### R-020 — Reflet

Supported description: target a pillar at exact range 2 and teleport symmetrically across it.

Base formula:

```text
source = P
target pillar = T
destination = 2*T - P
```

Unresolved:

- which range metric defines “2 PO”;
- whether the target must be axis-aligned;
- whether line of sight is required;
- path relevance;
- destination occupancy behaviour.

### R-030 — Rejet

Supported description: target a pillar at range 1–2 and move three cells away from it.

For an allowed alignment, let `u` be the unit vector from pillar to player:

```text
u = normalise_cardinal_or_diagonal(P - T)
destination = P + 3*u
```

Unresolved:

- permitted alignments;
- path blocking;
- map-edge truncation;
- collision with pillars;
- whether movement is displacement or teleportation.

### R-040 — Attrait

Supported description: target a pillar at range 1–6, normally in line, and move three cells toward it.

For an allowed alignment, let `u` be the unit vector from player to pillar:

```text
u = normalise_cardinal(P -> T)
raw_destination = P + 3*u
```

The raw formula is insufficient when the pillar is one or two cells away. `RulesProfile.movement.attraction.shortRangeBehaviour` must therefore be one of:

- `stop_adjacent_to_pillar`;
- `overshoot_pillar`;
- `action_invalid`;
- `unknown`.

## 5. Occupancy and paths

A destination is always checked against the arena mask. Pillar collision and intermediate-path behaviour remain profile-controlled until observed.

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
2. If the final cell equals the previous turn's cell, mark adverse stationary resolution.
3. Evaluate direct physical centre-glyph effects.
4. Evaluate projected black and white pillar collisions.
5. Any black adverse condition takes priority over positive white effects for race progress.
6. If no adverse condition exists, resolve Crocoburio progress according to the configured no-black rule.
7. Resolve recharge according to the configured timing.
8. Generate the next-turn resource state.

The solver trace must show which condition decided the outcome.

## 8. Resource model

Each spell has:

- `availability`: available, unavailable or unknown;
- optional numeric charge value;
- maximum charge, when known;
- cost per cast;
- recharge per matching white-pillar hit;
- recharge from a direct white centre glyph;
- recharge timing.

A boolean-only availability model may be used for the first pre-live version if numeric charge counts cannot be reliably read. Numeric values must never be fabricated from gauge position.

## 9. Search contract

The search enumerates sequences until:

- action budget is exhausted;
- no legal action exists;
- the user explicitly ends the turn.

Candidate ranking is lexicographic:

1. no adverse black or stationary outcome;
2. Crocoburio advances;
3. required low-resource spells are recharged;
4. next-turn resource resilience;
5. next-turn geometric mobility;
6. fewer casts;
7. higher confidence targets.

A candidate that depends on an unknown rule is not `solved`; it is `confirmation_required` or `blocked_unverified_rule`.

## 10. Solver output classes

- `solved`: all critical fields and mechanics are verified or directly confirmed.
- `confirmation_required`: a supported but not fully verified assumption needs user approval.
- `blocked_unverified_rule`: outcome changes depending on an unknown mechanic.
- `no_safe_solution`: all legal verified endings are adverse.
- `invalid_state`: the input is internally contradictory.
