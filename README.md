# Grougalorasalar Solver — v0.9.0

French-first screenshot review and deterministic turn solver for the fixed Grougalorasalar arena.

## Start

Requirements: Docker Desktop with the Docker Engine running.

```bash
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000). API readiness is available at [http://localhost:8000/api/v1/health/ready](http://localhost:8000/api/v1/health/ready).

No dependency installation or source-file editing is required for this start path. Stop with `docker compose down`.

## Player workflow

1. Upload a complete combat screenshot.
2. Inspect the player, pillar, and central-pattern overlays.
3. Correct the player or pattern by clicking the screenshot if needed.
4. Review the complete pillar list.
5. Select action budget and the four spell states.
6. Confirm the detected state and calculate the turn.

Developer codes are hidden in normal mode and available only through Debug.

## Automated tests

```bash
docker run --rm grougadofus-api:latest python -m pytest -q
cd apps/web
npm ci --ignore-scripts
npx playwright install chromium
npm run typecheck
npm run test:e2e
```

The browser test uses the retained real fixture at `packages/fixtures/real/phase7/round-01.png` and exercises upload, recognition, confirmation, and recommendation.

## Safety limits

- Critical detections require player review.
- Exact retained fixtures may use fixture-proof semantics only for their byte-identical hashes in review mode.
- Arbitrary or approximate screenshots never receive fixture-only solver authority.
- Seven boundary cells remain unresolved, so the 338-cell footprint is not claimed as fully position-verified.
- Locked-corpus detector accuracy and current gameplay-rule verification remain open.

Read `CURRENT_STATUS.md`, `TEST_REPORT.md`, `DEFECT_BACKLOG.md`, and `NEXT_STEP.md` for the release state.
