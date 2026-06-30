# Phase 7A Test and Performance Report — v0.8.0

## Automated scope

The executable suite covers:

- the retained reference plus all four new real screenshots;
- fixture hash/dimension/provenance integrity;
- exact player and pillar logical output for the four new screenshots;
- synthetic 1920 × 1080, 2560 × 1440 and 3840 × 2160 variants;
- JPEG quality 72;
- small borders;
- small crops;
- non-arena fallback;
- no OCR in the normal path;
- no affine/pixel data in the logical solver state;
- unconfirmed results remaining blocked;
- JavaScript syntax and message protocol for the Web Worker;
- all previous API, editor, privacy and 26 solver-fixture tests.

Synthetic variants test transform invariance. They are not substitutes for independent real capture sessions.

## Current result

- Python: **19 passed**;
- TypeScript: **passed**;
- Next.js production build: **passed**;
- npm audit: **0 known vulnerabilities**;
- Web Worker JavaScript syntax: **passed**.

## Measured warm-cache sample

Shared-container sample from `reports/performance-phase7a.json`:

| Stage | Samples | Median | p95 | Engineering target |
|---|---:|---:|---:|---:|
| working-copy creation | 12 | 68.095 ms | 118.866 ms | browser decode + copy ≤150 ms |
| arena registration | 12 | 88.441 ms | 298.714 ms | ≤400 ms |
| baseline recognition | 12 | 447.798 ms | 757.498 ms | ≤900 ms |
| server screenshot-to-state | 12 | 1,197.785 ms | 1,479.611 ms | server fallback ≤2,500 ms |
| solver | 130 | 1.143 ms | 3.220 ms | ≤50 ms |

The server PNG decode p95 was 421.494 ms. This does not test the browser decode target; browser-local `createImageBitmap` timing still requires Playwright on supported hardware. Cold engine initialisation was 2,883.239 ms and occurs once per process, not once per screenshot.

## Claims explicitly not made

- no browser-hardware p95 result;
- no production latency result;
- no detector-accuracy percentage;
- no locked-corpus false-safe rate;
- no validation across independent client languages/UI scales beyond the current real capture session;
- no Docker Compose execution in this environment.
