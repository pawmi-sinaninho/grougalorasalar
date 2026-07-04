# Frontend-only Patch B hardening

This patch rewrites the browser-local vision boundary in a build-safe way.

It is intentionally defensive:

- `pipeline.ts` now always returns a complete `FrontendSolveResult`.
- failed vision results include `source: "frontend"`, `status: "rejected"`, `actions: []`, warnings, debug and timings.
- `solveLocalGiven(...)` is never called with `undefined`.
- `browser-vision.ts` uses explicit early returns for missing player/glyph/pillars so TypeScript can narrow nullable values.
- `types.ts` allows string debug reasons during migration, so detector-specific reason codes do not break builds.

The normal user flow remains backend-free.
