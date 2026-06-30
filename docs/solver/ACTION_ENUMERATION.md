# ACTION ENUMERATION CONTRACT

## Canonical order

Root and child actions are generated in this order:

1. `indecision`;
2. `reflection`;
3. `repulsion`;
4. `attraction`.

Within a spell, targets are sorted by `(x ascending, y ascending, pillar ID ascending)`. Enumeration order never substitutes for candidate ranking.

Canonical movement signature:

```text
<spell>@<target-kind>:<x>,<y>:<pillar-id-or-dash>
```

Ordering is not raw string sorting. The comparator uses typed tuples `(spell ordinal, target-kind ordinal, x integer, y integer, pillar ID)` so multi-digit and negative coordinates remain deterministic.

## Shared target checks

For every movement action:

1. spell resource and action budget;
2. target kind;
3. target-pillar type rule when applicable;
4. range metric and alignment;
5. line of sight;
6. raw destination formula;
7. path and edge resolution;
8. destination arena class and occupancy.

A missing rule at steps 3–8 creates a conditional action, not a guessed definite action.

## Indécision

For source `P`:

- `orthogonal`: targets `P + (1,0)`, `P + (-1,0)`, `P + (0,1)`, `P + (0,-1)`;
- `chebyshev`: the four orthogonal plus four diagonal neighbours;
- destination equals target.

A pillar-occupied target follows `destinationOccupancy`. Unknown occupancy behaviour depends on R-053/R-034.

## Reflet

For each eligible target pillar `T`:

```text
destination = 2*T - P
```

Range is calculated by the selected exact metric:

- `manhattan = |dx| + |dy|`;
- `chebyshev = max(|dx|, |dy|)`;
- `aligned_steps = |dx|` for axis alignment or `|dx|` when `|dx|=|dy|`;
- `unknown` produces a conditional target.

`alignment` is evaluated separately from range. The target must satisfy both.

## Rejet

A pillar is directionally eligible only when the source-to-pillar vector matches a configured alignment. Let `u` point from pillar to player:

```text
destination = P + distance*u
```

Cardinal `u` has one component ±1 and one zero. Diagonal `u` has both components ±1. Non-normalisable vectors are invalid, not rounded.

## Attrait

For an eligible pillar, let `u` point from player to pillar:

```text
raw destination = P + distance*u
```

When target distance is shorter than movement distance:

- `stop_adjacent_to_pillar`: use `T-u`; if this equals source, the movement is stationary;
- `overshoot_pillar`: use the raw destination;
- `action_invalid`: reject;
- `unknown`: conditional.

## Path and edge

Intermediate cells are the ordered cells after source and before destination along `u`.

- `teleport_ignore_intermediate`: do not test intermediate cells;
- `fail_if_blocked`: any configured blocker rejects the action;
- `truncate_before_blocker`: destination becomes the last valid cell before the first blocker;
- `unknown`: conditional.

For an off-map destination:

- `invalid`: reject;
- `truncate_to_last_walkable`: walk the ordered path and choose the final definite walkable cell;
- `unknown`: conditional.

Truncation that leaves the player on the source cell is a legal cast only when the profile explicitly permits the action; its terminal result is then evaluated by the stationary rule.
