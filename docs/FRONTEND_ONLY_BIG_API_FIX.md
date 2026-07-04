# Frontend-only Big API Fix

This patch replaces `apps/web/lib/api.ts` with a clean compatibility boundary.

## Purpose

The previous incremental patches left invalid TypeScript in the API bridge, including `async async function` and unsafe field reads.

This fix does one controlled rewrite of the web API boundary:

- keeps the existing `app/page.tsx` contract stable;
- preserves `createAnalysis`, `uploadImage`, `command`, `solve`, `deleteAnalysis`, and `fetchAssetUrl` exports;
- bypasses backend calls when `NEXT_PUBLIC_SOLVER_MODE=frontend`;
- calls `solveScreenshotRuntime(..., { mode: 'frontend', worker: { useWorker: false }, allowBackendFallback: false })` for uploads;
- returns a valid `AnalysisEnvelope` even while the local detector/solver pipeline is still pending;
- removes unsafe direct accesses like `result.reason`, `result.confidence`, `result.debug`, and `result.warnings` where they previously broke the build;
- removes duplicate `async async` syntax.

## Expected build result

`npm run build` should pass this API-boundary migration stage. The UI may still show a frontend pipeline pending/incomplete message until the detector and solver stages are ported.
