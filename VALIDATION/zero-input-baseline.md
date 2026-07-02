# Zero-input baseline — 2026-07-02

Branch lineage: `main` → `fix/reference-screenshot-stabilization` → `codex/glyph-recognition-fix` (`8cc32a6`). Work started from `8cc32a6` on `codex/zero-input-enduser-flow`.

## Unmodified test baseline

- Python: `69 passed, 1 warning in 17.18s`.
- TypeScript: passed.
- Next.js production build: passed.
- Browser E2E was not run before dependency/browser setup.

## Reproduced blockers

1. `recognition.py` required `matchedFixtureId` before setting the old critical-ready flags.
2. `app.py` granted the solver's complete rules path only to an exact `REAL-P7-*` fixture hash.
3. The standard page exposed three confirmations and a separate solve button in Debug, while normal mode could remain on a generic analysis message.
4. Glyph classification used low saturation plus one black/white value threshold before global phase matching.
5. Pillar-set completeness was a manual boolean rather than an independent cell scan.
6. The upload endpoint stopped after recognition; solving required a second HTTP request.

This file records the pre-change baseline only. Current evidence is in `zero-input-release-report.md` and `.json`.
