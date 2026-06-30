# CURRENT STATUS

**Version:** 0.9.0  
**Date:** 2026-06-30  
**Phase:** Release-blocker repair and player workflow  
**Status:** COMPOSE START AND REAL-FIXTURE BROWSER FLOW PASS

## Player workflow

- The retained real screenshot `round-01.png` detects the controlled player at logical cell `(1,-1)`; an unresolved player remains `null` and can no longer leak as a synthetic `0,0` result.
- The player is drawn directly on the screenshot with a cyan cell and red centre marker.
- All 24 detected pillars are shown with ID and spell type; confidence below `0.80` is highlighted in orange.
- Three dark and three light central-pattern cells are exported and drawn in magenta. A missing pattern displays exactly: `Le motif central n’a pas été détecté.`
- Player and pattern corrections are direct clicks on the screenshot; the standard workflow has no coordinate fields.
- Action budget and all four spell states use explicit, visibly selected controls. `unknown`, `available`, and `unavailable` are distinct states.
- `Calculer le tour` stays disabled until player, pillar completeness, pattern, action budget, spell states, and detection review are complete.
- Rule codes, state versions, server path, and internal statuses exist only behind the Debug control.

## Clean start

- User start command: `docker compose up --build`
- Web: `http://localhost:3000`
- API readiness: `http://localhost:8000/api/v1/health/ready`
- Node is pinned to `24.17.0` by image tag and digest.
- npm is pinned to `11.18.0`; dependency installation is `npm ci` from `package-lock.json` with scripts disabled.
- Git data, archives, virtual environments, pytest/Python caches, `node_modules`, `.next`, Playwright results, reports, and runtime sessions are excluded from Docker context.
- The obsolete local `apps/web/Dockerfile.bak` was removed.

## Verified results

- clean no-cache Web/API image build: passed;
- API suite in the built image: **36 passed**;
- TypeScript and Next.js production build: passed;
- API readiness: `ready`; Web HTTP response: `200`;
- Playwright Chromium real-fixture flow: **2 passed in 4.4 s**;
- real screenshot upload-to-review time in the browser test: below 5 seconds;
- Compose down and restart: passed.

## Remaining safety boundary

This repair does not close the separate arena boundary review: 43 boundary cells are confirmed and 7 remain unresolved (`C009`, `C016`, `C025`, `C064`, `C081`, `C168`, `C193`). The 338-cell count remains provisional for full positional authority. General gameplay rule verification and locked-corpus accuracy also remain open. Fixture-proof solving is enabled only for an exact retained fixture hash in review mode; arbitrary screenshots do not inherit fixture authority.
