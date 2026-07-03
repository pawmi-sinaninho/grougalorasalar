# Grougalorasalar Solver — v1.0.0

French-first, deterministic screenshot-to-turn assistant for the fixed Grougalorasalar arena.

## End-user flow

1. Open `http://localhost:3000`.
2. In Dofus, open the top-right `...` menu and choose `Masquer tous les modules` before starting the fight.
3. Choose the Dofus window once, click `Capturer ce tour` at the start of every turn, execute the numbered recommendation, finish the round, and capture the next turn.

The standard route uses the browser window-capture workflow and asks for no AP, charge, pillar, glyph, confirmation, or solve-button input. It shows numbered target markers, movement, final cell, black/white hits, progression, and next-round charges. Diagnostic controls exist only at `/?debug=1`.

## Start

Requirements: Docker Desktop with the Docker Engine running.

```bash
docker compose up --build
```

API readiness: `http://localhost:8000/api/v1/health/ready`. Stop with `docker compose down`.

## Tests

```bash
python -m pytest -q
cd apps/web
npm ci --ignore-scripts
npm run typecheck
npm run build
npm run test:e2e
```

The release regression and exact screenshot matrix are in `VALIDATION/zero-input-release-report.md` and `.json`.

## Honest validation boundary

- The four retained real start screenshots all produce an executable provisional recommendation with zero interaction and exact player/pillar/black/white sets.
- Those four screenshots belong to one capture session; this is regression evidence, not independent beta validation.
- Only four of the requested eight start screenshots are present.
- The original individual glyph-template PNG bytes referenced by hash are absent. The runtime therefore uses cached structural patches derived from retained reference imagery plus neutral-background comparison.
- Seven arena-boundary cells and independent locked-corpus validation remain open.

Read `CURRENT_STATUS.md`, `KNOWN_LIMITATIONS.md`, `DEFECT_BACKLOG.md`, and `NEXT_STEP.md` before calling the build release-ready.
