# Frontend-only createAnalysis type/runtime fix

## Problem

The frontend-only API boundary patch made `createAnalysis(...)` return an `AnalysisEnvelope` in frontend mode.
`apps/web/app/page.tsx` expects the create endpoint shape:

```ts
{
  session: { analysisId, stateVersion, state, gate },
  accessToken: string
}
```

That caused the Vercel/Next TypeScript error:

```text
Property 'accessToken' does not exist on type 'AnalysisEnvelope | ...'
```

## Fix

`frontendOnlyCreateAnalysis(...)` now returns the same create-session shape as the backend create endpoint.
The local `AnalysisEnvelope` is still stored internally for the later upload/solve bridge.

## Expected verification

```powershell
cd apps/web
npm run build
```
