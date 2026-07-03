# Frontend Solver Scaffold

This folder is the migration boundary for the frontend-only solver.

## Current state

The scaffold is installed, but the real detection and solver stages still need to be wired.

## Intended import

```ts
import { solveScreenshot } from "@/lib/frontend-solver";
```

## Required next wiring

1. Replace the current API-submit path in the screenshot UI with `solveScreenshot(...)` when `NEXT_PUBLIC_SOLVER_MODE=frontend`.
2. Port or wrap existing solver mechanics in TypeScript.
3. Port arena/grid/glyph/pillar/player extraction to canvas/Web Worker code.
4. Keep backend only as explicit fallback while parity tests are being built.
