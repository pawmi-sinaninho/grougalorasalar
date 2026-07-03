# GROUGALORASALAR SOLVER — Frontend-only Migration

## Decision

The official target architecture is now **frontend-only**:

```text
screenshot paste/upload
-> browser canvas/image pipeline
-> browser-local arena/cell/glyph/pillar/player detection
-> browser-local solver
-> result UI
```

The backend is no longer part of the product-critical path. It may remain temporarily as a compatibility fallback while the browser pipeline is being ported.

## Why this change exists

Current production behaviour is not acceptable for the intended end-user workflow:

- screenshots can take roughly 15–20 seconds to process in deployed backend mode;
- backend cold starts / free-tier CPU / upload roundtrips make latency unstable;
- "Capture incomplete" failures are too expensive because each retry costs another backend request;
- the product goal is: **Ctrl+V screenshot -> solution with minimal delay**.

## Non-negotiable UX target

```text
User pastes screenshot
-> UI remains responsive
-> local analysis starts immediately
-> solution or actionable warning is displayed
```

## Migration phases

### Phase 1 — Add frontend runtime shell

- Create a frontend pipeline contract.
- Add a Web Worker boundary for heavy work.
- Add timing and debug objects to every local run.
- Keep backend path available only as fallback.

### Phase 2 — Port deterministic solver logic

- Move action simulation, spell rules, charge handling and scoring to TypeScript.
- Add parity tests against existing known fixtures.
- Keep all confirmed mechanics in one shared rules module.

### Phase 3 — Port image extraction

Preferred route:

- avoid generic OCR/ML;
- use canvas + cached arena geometry + known cell centres;
- sample expected cell regions directly;
- detect glyphs/pillars/player with deterministic colour/shape heuristics where possible;
- keep confidence/warnings instead of hard rejecting minor uncertainty.

Heavy library route if needed:

- OpenCV.js or WASM module, loaded client-side;
- executed inside a Web Worker;
- lazy-loaded only when screenshot analysis starts.

### Phase 4 — Remove backend dependency from UI

- `NEXT_PUBLIC_SOLVER_MODE=frontend` becomes default.
- API calls are disabled by default.
- Backend deployment becomes optional or deleted.

## Runtime modes

```text
frontend = only browser-local processing
backend  = legacy API mode
hybrid   = try frontend first, backend only as explicit fallback
```

## Acceptance criteria

A migration step is not done unless:

- the UI can process a pasted screenshot without calling Render/backend;
- the browser main thread does not freeze during analysis;
- every local run returns timings;
- every uncertain capture returns structured warnings/debug info;
- known fixture screenshots produce the same or better decisions than backend mode.
