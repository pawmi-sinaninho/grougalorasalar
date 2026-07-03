# Zero-input release validation

**Classification:** single-session regression; not independent beta validation.

**Primary metric:** 4/4 (100%) retained real starts produced an executable recommendation with zero interaction.

Latency: p50 611.356 ms, p95 814.223 ms, max 814.223 ms.

| Screenshot | Player | Pillars | Types | Black | White | Status | Actions | Final | Latency |
|---|---:|---:|---:|---:|---:|---|---:|---|---:|
| REAL-P7-01 | True | True | True | True | True | provisional_solution | 1 | 2,-1 | 814.223 ms |
| REAL-P7-02 | True | True | True | True | True | provisional_solution | 1 | 1,-1 | 615.656 ms |
| REAL-P7-03 | True | True | True | True | True | provisional_solution | 1 | 0,1 | 607.057 ms |
| REAL-P7-04 | True | True | True | True | True | provisional_solution | 1 | 0,-2 | 588.223 ms |

## Known limits

- All retained starts belong to one capture session.
- Only four of the requested eight start screenshots are present in the repository.
- The individual original black/white glyph PNG bytes referenced by hash are absent; cached structural patches are derived from retained reference imagery.
- Independent beta accuracy and tactical outcome validation remain open.

## Stage latency

| Stage | p50 | p95 | max |
|---|---:|---:|---:|
| decodeMs | 25.253 ms | 43.5 ms | 43.5 ms |
| registrationMs | 98.492 ms | 107.714 ms | 107.714 ms |
| playerMs | 8.867 ms | 9.601 ms | 9.601 ms |
| pillarMs | 117.37 ms | 238.041 ms | 238.041 ms |
| glyphMs | 35.402 ms | 38.365 ms | 38.365 ms |
| hypothesisMs | 0.0 ms | 0.001 ms | 0.001 ms |
| solverMs | 1.387 ms | 2.023 ms | 2.023 ms |
| overlayMs | 102.126 ms | 107.764 ms | 107.764 ms |
| totalMs | 611.356 ms | 814.223 ms | 814.223 ms |
