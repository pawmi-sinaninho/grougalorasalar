# Zero-input release validation

**Classification:** single-session regression; not independent beta validation.

**Primary metric:** 4/4 (100%) retained real starts produced an executable recommendation with zero interaction.

Latency: p50 1320.436 ms, p95 1397.795 ms, max 1397.795 ms.

| Screenshot | Player | Pillars | Types | Black | White | Status | Actions | Final | Latency |
|---|---:|---:|---:|---:|---:|---|---:|---|---:|
| REAL-P7-01 | True | True | True | True | True | provisional_solution | 2 | 4,-2 | 1397.795 ms |
| REAL-P7-02 | True | True | True | True | True | provisional_solution | 1 | 3,0 | 1289.542 ms |
| REAL-P7-03 | True | True | True | True | True | provisional_solution | 2 | 1,-2 | 1351.331 ms |
| REAL-P7-04 | True | True | True | True | True | provisional_solution | 2 | 4,-2 | 1276.03 ms |

## Known limits

- All retained starts belong to one capture session.
- Only four of the requested eight start screenshots are present in the repository.
- The individual original black/white glyph PNG bytes referenced by hash are absent; cached structural patches are derived from retained reference imagery.
- Independent beta accuracy and tactical outcome validation remain open.

## Stage latency

| Stage | p50 | p95 | max |
|---|---:|---:|---:|
| decodeMs | 29.641 ms | 55.789 ms | 55.789 ms |
| registrationMs | 139.734 ms | 146.816 ms | 146.816 ms |
| playerMs | 11.666 ms | 12.612 ms | 12.612 ms |
| pillarMs | 154.734 ms | 241.678 ms | 241.678 ms |
| glyphMs | 44.105 ms | 47.317 ms | 47.317 ms |
| hypothesisMs | 0.001 ms | 0.001 ms | 0.001 ms |
| solverMs | 545.216 ms | 568.075 ms | 568.075 ms |
| overlayMs | 123.094 ms | 129.087 ms | 129.087 ms |
| totalMs | 1320.436 ms | 1397.795 ms | 1397.795 ms |
