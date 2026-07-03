# Frontend-only API Boundary Patch

## What changed

This patch intercepts the existing `apps/web/lib/api.ts` boundary.

When `NEXT_PUBLIC_SOLVER_MODE=frontend`, the old UI functions stop calling the backend:

- `createAnalysis(...)` creates a browser-local analysis envelope.
- `uploadImage(...)` sends the pasted/uploaded `File`/`Blob` to `solveScreenshotRuntime(...)`.
- `solve(...)` returns the last browser-local result.
- `command(...)` is bridged as a safe no-op until a local correction reducer is ported.
- `deleteAnalysis(...)` clears the browser-local analysis map.

## Why this layer exists

The deep wiring scan identified `apps/web/app/page.tsx` as the strongest UI candidate and `apps/web/lib/api.ts` as the backend boundary. Patching the API boundary first is safer than rewriting the whole page component.

## Current limitation

This patch removes the backend from the normal route only at the web boundary. It does **not** magically port the detector/solver. The local runtime still returns its current result. If the pipeline still says `not_implemented`, the next patch must port the first real browser stage.

## Expected verification

Run:

```powershell
git diff -- apps/web/lib/api.ts docs/FRONTEND_ONLY_API_BOUNDARY_PATCH.md apps/web/.env.local
cd apps/web
npm run lint
npm run build
```

Then open the website, paste a screenshot and check the browser Network tab:

- no request should go to Render/backend during the normal upload path;
- the UI should return quickly;
- if the local pipeline is not ported yet, the result should explicitly say that instead of hanging for 15–20 seconds.
