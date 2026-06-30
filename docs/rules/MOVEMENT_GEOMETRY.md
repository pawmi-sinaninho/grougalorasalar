# MOVEMENT GEOMETRY

## Purpose

Define implementation-neutral formulas and list exactly what still needs gameplay evidence.

## Direction vectors

Use these candidate unit directions:

```text
cardinal = {(1,0), (-1,0), (0,1), (0,-1)}
diagonal = {(1,1), (1,-1), (-1,1), (-1,-1)}
```

The final allowed direction set for each spell is a rules-profile value.

## Indécision

```text
D = target cell
```

Minimum observation required:

- one successful orthogonal cast;
- one attempted diagonal-contact cast;
- one attempted cast onto an occupied pillar cell.

## Reflet

```text
D.x = 2*T.x - P.x
D.y = 2*T.y - P.y
```

Minimum observation required:

- one axis-aligned successful cast;
- one non-axis range-2 attempt;
- one reflection whose destination is near the edge;
- one reflection whose destination would contain a pillar, if the generated board permits it.

## Rejet

```text
D = P + 3*u
```

Minimum observation required:

- pillar at distance 1;
- pillar at distance 2;
- obstacle on intermediate cell;
- blocked destination;
- board-edge interaction.

## Attrait

```text
raw D = P + 3*u toward pillar
```

Minimum observation required:

- pillar at distances 1, 2, 3, 4, 5 and 6 where possible;
- a blocked intermediate cell;
- target not in line;
- board-edge interaction.

## Path interpretation modes

Every displacement spell must explicitly select one mode:

- `teleport_ignore_intermediate`;
- `move_fail_if_path_blocked`;
- `move_truncate_before_blocker`;
- `unknown`.

No implementation may infer this from generic DOFUS behaviour without direct evidence from this fight.
