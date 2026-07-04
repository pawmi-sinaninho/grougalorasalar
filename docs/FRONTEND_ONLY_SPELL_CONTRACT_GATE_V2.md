# Frontend-only spell contract gate v2

This is a more tolerant replacement for the previous hardfix.

It enforces the spell mechanics inside `applyMovementConstraints` and avoids failing when
`localSolverResultToFrontendResult` has a different action mapping shape.

Core contract:

- Indécision targets one orthogonal free adjacent cell.
- Reflet targets only a diagonal adjacent pillar (`abs(dx)=1 && abs(dy)=1`).
- Rejet targets a pillar in straight/diagonal range 1-2 and moves away from it up to 3 cells.
- Attrait targets a linear pillar in range 1-6 and pulls toward it up to 3 cells, stopping before it.

The returned internal action is normalised so pillar-target spells carry `targetKind: "pillar"`.


Output patch note: skipped: no explicit targetKind assignment; internal action is normalised
