# TEST REPORT — v0.9.0 release-blocker repair

**Run date:** 2026-06-30  
**Platform:** Windows, Docker Desktop 4.79.0, Docker Engine 29.5.3

## Exact commands and results

| Command | Result |
|---|---|
| `docker compose down --rmi all -v --remove-orphans` | Project containers, images, network, and session volume removed |
| `docker compose build --no-cache --pull` | Web and API built; Web context about 70 kB, API context about 60 MB |
| `docker run --rm grougadofus-api:latest python -m pytest -q` | **36 passed** |
| `npm.cmd run typecheck` in `apps/web` | passed |
| `docker compose up --build` | API healthy; Web ready |
| GET `http://localhost:8000/api/v1/health/ready` | `status: ready` |
| GET `http://localhost:3000` | HTTP 200 and expected page title |
| `npm.cmd run test:e2e` in `apps/web` | **2 passed in 4.4 s** |
| `docker compose down` followed by `docker compose up --build` | second start passed |

## Real browser proof

Playwright `1.61.1` with its version-bound Chromium uploads `packages/fixtures/real/phase7/round-01.png` and verifies:

1. recognition becomes reviewable within five seconds;
2. one controlled-player overlay is present at the API-asserted logical cell `(1,-1)`;
3. 24 pillar overlays and 6 pattern-cell overlays are visible;
4. standard page text contains none of `blocked_unverified_rule`, `rules_blocked`, `server_fast_fallback`, `stateVersion`, or `S-BLOCK-*`;
5. the solver button is disabled before review;
6. pillar list, pattern, action budget, four spell states, and detections are confirmed;
7. the solver button becomes enabled and produces a player-facing recommendation.

A second browser case uploads the empty arena and verifies the exact missing-pattern message plus both direct-click correction controls.

## Build defect disposition

The original `npm install --ignore-scripts` path was removed. The accepted Web build uses Node `24.17.0` at a fixed OCI digest, upgrades to npm `11.18.0`, asserts both versions, and runs `npm ci --ignore-scripts --no-audit --no-fund`. The system Edge cleanup issue observed during test development was eliminated from the release test path by using Playwright’s version-bound Chromium.
