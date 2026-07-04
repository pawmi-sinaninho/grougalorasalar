# Frontend-only Forced Overlay Patch

## Why

The frontend solver now returns a solved recommendation, but the screenshot still showed no target/movement overlay.

The UI only renders the SVG overlay when `recognition.registration.originImage` exists. In the frontend-only path this can be missing or unusable even though the solver has valid cells and actions.

## Changes

- Adds a browser-local fallback cell-to-image registration in `app/page.tsx`.
- Uses the fallback registration for frontend-only results when the API registration is missing or unusable.
- Forces the SVG overlay to sit above the screenshot with inline positioning.
- Adds inline SVG stroke/fill attributes for target lines, movement lines, pins, and final cell markers so visibility no longer depends on CSS only.

Expected result: numbered target pins, orange target lines, white movement lines, and the final-cell marker should be visible again.
