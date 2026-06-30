# Browser-first Fast-Path Decision — v0.8.0

## Decision

The pre-live architecture is **hybrid**:

1. **browser-local immediate path** for preview, image decoding, bounded working-copy creation and visible progress;
2. **cached server fast path** for affine arena registration and registered logical-cell classification;
3. **manual targeted correction** when registration, completeness or field confidence is unresolved.

A heavy detector, OCR service or generative model is not present in the critical path.

## Why not a fully browser-side detector in v0.8.0

The repository already has an authoritative Python solver and FastAPI lifecycle. Replacing the proven OpenCV ORB/connected-component implementation with OpenCV-WASM would add a large browser payload, startup compilation and another numerical implementation before accuracy equivalence is measured. That would increase first-use latency and create two registration authorities.

The current server fast path has cached features/templates and measured warm-cache server screenshot-to-state p95 of **1,479.611 ms** on shared container hardware. This is below the 2.5-second server-fallback engineering target. The browser still gives real local feedback immediately and does not wait for the API before showing the screenshot.

## Repository ownership

| Capability | Runtime | Repository location | v0.8.0 decision |
|---|---|---|---|
| immediate preview | browser main thread | `apps/web/app/page.tsx` | local |
| decode/downscale working copy | Web Worker | `apps/web/public/workers/analysis-worker.js` | local |
| arena registration | cached OpenCV service | `services/api/grougal_solver/fast_recognition.py` | server fast path |
| canonical warp | cached OpenCV service | same | server fast path |
| known-cell sampling | cached OpenCV service | same | server fast path |
| pillar classification | cached OpenCV service | same | server fast path |
| player-base detection | cached OpenCV service | same | server fast path |
| exact fixture signature | cached OpenCV service | same | server fast path |
| glyph proposals | versioned fixture annotation | `data/vision/real-screenshot-fixtures.v0.8.0.json` | review-only |
| deterministic solver | Python domain package | `services/api/grougal_solver/solver.py` | server authoritative |
| overlay | browser preview + server annotated PNG | `page.tsx`, `overlay.py` | hybrid |
| correction | browser commands/API state | `page.tsx`, `editor.py` | hybrid |

## Browser-safe without accuracy loss

The following can run locally because they do not alter tactical meaning:

- file preview;
- `createImageBitmap` decoding;
- bounded downscaling to a working image;
- progress timing;
- rendering already-returned logical observations;
- invalidating stale result visuals after an edit.

The following remain server-side in v0.8.0 because numerical equivalence has not been demonstrated for a browser implementation:

- ORB feature extraction/matching;
- RANSAC affine registration;
- canonical cell sampling;
- connected-component pillar classification;
- the authoritative deterministic solver.

## Promotion path to a fully local detector

A future browser detector may replace the server fast path only if the same locked corpus proves:

1. identical logical `TurnState` output;
2. no increase in false-safe recommendations;
3. p95 local screenshot-to-result at or below 1.2 seconds on supported hardware;
4. no per-upload model/template reload;
5. an acceptable initial JavaScript/WASM payload and cold-start time.

Until then, the hybrid path is the lowest-risk implementation that meets the fast-response objective without duplicating the recognition authority.
