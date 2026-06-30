# NEXT STEP

The clean-start and unusable-player-workflow release blockers are closed. Do not add unrelated features before the following evidence work.

## 1. Close the seven-cell boundary review

Resolve `C009`, `C016`, `C025`, `C064`, `C081`, `C168`, and `C193` with a second accepted evidence criterion per cell. Then rerun `scripts/build_canonical_arena.py --check` and `scripts/validate_phase7b.py`.

## 2. Generalise the proven browser flow

Run the same overlay and correction workflow on the remaining real fixtures and the locked corpus. Measure player, pillar, and pattern accuracy without allowing an approximate fixture match to acquire fixture-only solver authority.

## 3. Finish release QA

Add keyboard/accessibility and responsive-browser coverage, then verify the published ZIP on a second clean Docker Desktop machine using only:

```bash
docker compose up --build
```
