# Frontend-only async/await typefix

## Problem

The frontend-only API bridge introduced an `await solveScreenshotRuntime(...)` call inside a function that was not declared `async`.

Next/Turbopack therefore failed with:

```text
await isn't allowed in non-async function
```

## Fix

This patch scans `apps/web/lib/api.ts` and makes any normal function declaration that contains `await` explicitly `async`.

It also includes targeted fixes for the frontend-only helpers, especially:

```ts
frontendOnlyUploadImage(...)
```

## Verification

```powershell
cd apps/web
npm run build
```
