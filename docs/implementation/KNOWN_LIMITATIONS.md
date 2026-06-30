# Known Limitations — v0.8.0

## Release blockers for authoritative solving

1. **Open combat mechanics:** V-001 through V-010 remain unresolved by current-version complete-turn evidence.
2. **Projection anchor:** `(0,0)` remains provisional.
3. **Automatic confirmation:** `MODEL-001` remains active. Strong registration/detection scores do not bypass review.
4. **Locked corpus:** the required 150 adjudicated screenshots from at least 15 independent capture sessions do not exist.
5. **Glyph/UI completeness:** player and visible pillar extraction are implemented, but glyph completeness, action budget, spell state and progress indices are not generally verified.
6. **Multiplayer:** rejected/not modelled.

## Fast-path limits

- The four new screenshots belong to one capture session and are fixtures, not an independent validation set.
- Registered fixture signatures can reproduce known-round glyph proposals but are not a general glyph detector.
- The browser performs preview and preprocessing only; ORB registration, cell classification and the authoritative solver remain server-side.
- The 1.2-second fully local target is not measured or achieved as a browser-only path in v0.8.0.
- The 5-second hard timeout is documented but not yet enforced through an isolated cancellable worker process.
- The server PNG decode time is not evidence for or against the browser `createImageBitmap` target.
- All four new files are retained at 2048 × 1151, but upstream scaling before upload cannot be proved or excluded.

## Current UI limitations

- Numeric/form correction remains; direct isometric click editing is incomplete.
- The browser does not expose every API command, notably move/delete/reclassify, undo/redo and progress entry.
- Action budget is fixed at the verified 12 AP and is not entered manually.
- Spell availability is exposed; full numeric charge editing is incomplete.
- Runtime locale switching for German/English is not wired.
- Tablet/mobile correction has not passed browser acceptance tests.
- No Playwright, visual-regression or automated accessibility suite is included.

## Runtime and operations limitations

- No external malware scanner is integrated; file handling relies on decode/size/type limits and image re-encoding.
- Session state is filesystem/process-local; horizontal scaling is unsafe.
- Expiry cleanup is not yet supervised as a production periodic job.
- Rate limiting, reverse-proxy limits and production telemetry exporters remain unimplemented.
- Docker Compose could not be executed in the build environment.

## Oracle/data limitations

The Phase-3 fixture catalogue still mixes full-result assertions with candidate-focused examples. The v0.8.0 tests preserve semantic scope rather than silently rewriting historical data. A versioned erratum remains required.

## Validation limits

- Performance results use shared container hardware and small warm-cache samples.
- The host used Node 22.16.0 while the package/Docker baseline requires Node 24; typecheck/build still passed.
- Container startup, browser E2E, reverse proxy, production storage permissions and recovery were not executed.
- No detector precision/recall, false-safe rate, live-fight win rate or production latency is claimed.

## Phase 7B-R boundary-refinement limits

- The 338-coordinate arena footprint is provisional: 43 boundary cells are confirmed and 7 are unresolved (`C009`, `C016`, `C025`, `C064`, `C081`, `C168`, `C193`).
- The projection anchor remains provisional even though the grid geometry and cell list are fixed.
- The original byte file of the green boundary annotation is unavailable; its semantic rule is preserved but is not counted as per-cell evidence.
- Registration success across the current seven images is geometry evidence, not detector precision/recall or independent corpus validation.
- The canonical mask does not resolve glyph, resource, progress or multiplayer extraction.
