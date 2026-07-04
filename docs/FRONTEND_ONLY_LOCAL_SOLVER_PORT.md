# Frontend-only Local Solver Port

## Decision

The first real backend extraction is the deterministic tactical solver, not the visual detector.

This patch ports the solver core from the Python service into browser TypeScript under:

```text
apps/web/src/lib/frontend-solver/local-solver.ts
```

## Implemented locally

- 12 AP default budget.
- 1 AP per spell cast.
- 2 initial charges per spell, cap 4.
- Charge transition: `next = min(4, start - casts + matchingWhiteHits)`.
- Indécision: only four orthogonally adjacent free cells.
- Reflet: latest confirmed rule — only diagonal adjacent pillar target where `abs(dx)=1` and `abs(dy)=1`.
- Rejet: pillar target in cardinal/diagonal direction, distance 1–2; movement is measured from the player cell, with diagonal corner-block checks.
- Attrait: cardinal pillar target, range 1–6; clear path to pillar; pulls up to 3 cells and stops before the pillar.
- Pillars block movement and final cells except Reflet crossing its target pillar.
- Black outcomes are hard unsafe candidates.
- White hits recharge matching spell types and break ties only after fewer casts.
- Breadth-first deterministic search with capacity guard.

## Still not implemented

The screenshot detector still needs to produce a complete logical state:

```ts
solveLocalGiven({ arena, player, pillars, glyphs, resources })
```

Until the detector is ported, normal screenshots still return the frontend migration/pending status. That is expected.

## Why this order

Porting the visual detector before the tactical solver would only move screenshots into the browser while still lacking a local recommendation engine. This patch makes the browser capable of solving a recognised state first; the next patch wires screenshot recognition into that state shape.
