# Frontend-only Local Debug Console Patch

Adds browser-side debug publishing for the frontend-only upload flow.

## What changes

When `NEXT_PUBLIC_SOLVER_MODE=frontend`, each screenshot upload now writes the local pipeline result and the mapped `AnalysisEnvelope` to:

- `window.__grougalLastFrontendResult`
- `window.__grougalLastFrontendEnvelope`
- the browser console via `console.info(...)`

This does not re-enable the backend and does not create Fetch/XHR requests.

## How to inspect

After pasting a screenshot, open DevTools Console and run:

```js
copy(JSON.stringify(window.__grougalLastFrontendEnvelope, null, 2))
```

or:

```js
copy(JSON.stringify(window.__grougalLastFrontendResult, null, 2))
```
