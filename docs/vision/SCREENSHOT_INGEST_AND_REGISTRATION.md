# SCREENSHOT INGEST & REGISTRATION SPECIFICATION — Phase 4

## 1. Purpose

Convert an arbitrary supported screenshot into a logical-grid transform without using raw image dimensions as a proxy for arena scale. Registration is a vision function only; it may not decide movement legality or tactical outcome.

## 2. Input contract

Accepted encodings:

- PNG;
- JPEG;
- WebP.

Engineering limits for the pre-live build:

- minimum image size: 1280 × 720;
- maximum decoded size: 33.2 megapixels;
- malformed or animated files are rejected;
- EXIF orientation is normalised before hashing or analysis;
- the original is retained only with explicit consent.

The main arena, controlled avatar and central glyph region must be present. Missing gauges or progress tracks do not invalidate the image, but they leave the respective fields unresolved.

## 3. Arena-presence decision

Arena presence uses two independent families of evidence:

1. **geometric evidence** — two isometric floor-line families, candidate cell spacing and expected axis orientation;
2. **landmark evidence** — stable arena structures sampled across at least three separated board regions.

A colour histogram or single template is never sufficient. The reference floor palette is not unique enough to identify the fight safely.

Decision thresholds are in `data/vision/recognition-policy.v0.5.0.json`:

- accepted: confidence ≥ 0.97;
- manual review: 0.80–0.9699;
- rejected: < 0.80.

Even an accepted presence score cannot auto-confirm a critical field while the model calibration status is `unvalidated`.

## 4. Registration model

The logical arena remains the Phase-2 square grid rendered isometrically:

```text
pixel = origin + x * basisX + y * basisY
```

Registration estimates:

- `origin`;
- `basisX`;
- `basisY`;
- inlier landmarks;
- residuals in logical-cell units;
- alternative hypotheses.

A full projective homography is not the default because it can absorb wrong correspondences and produce false precision. A homography may be evaluated only as a diagnostic. The exported tactical transform remains the affine grid basis above.

## 5. Candidate generation

Candidate transforms are generated from:

1. floor-line intersections;
2. stable map-landmark correspondences;
3. optional prior transform from the same capture session;
4. manual three-anchor input.

At most five candidates proceed to scoring. Each must satisfy:

- `+x` visually down-right;
- `+y` visually down-left;
- positive non-degenerate cell area;
- plausible basis-length ratio against the arena model;
- overlap with the candidate-cell envelope.

## 6. Scoring and acceptance

For each candidate, compute:

- median reprojection residual in cells;
- p95 residual in cells;
- inlier count;
- number of spatially separated inlier regions;
- arena-mask overlap;
- landmark-template agreement;
- separation from the second-best candidate.

Accepted registration requires all of:

- at least six inliers;
- inliers in at least three board regions;
- median residual ≤ 0.06 cell;
- p95 residual ≤ 0.10 cell;
- confidence ≥ 0.97;
- no competing candidate within 0.08 confidence.

Review registration allows median ≤ 0.10, p95 ≤ 0.16 and confidence ≥ 0.80. Anything worse is rejected.

These are conservative engineering thresholds, not measured accuracy claims. Phase 7 may tighten them; relaxing them requires a recorded decision and regression evidence.

## 7. Crop and UI-scale behaviour

- The transform is estimated from board content, not screenshot width.
- Window borders and unused margins are ignored.
- UI scaling is allowed to move gauges independently of the board transform.
- The board transform and UI-region registration are therefore separate outputs.
- A crop may be accepted only when all solver-critical board regions remain visible.
- A crop that removes resource UI may continue to manual resource entry.

## 8. Manual correction

When registration is unresolved, the user places:

1. logical origin `(0,0)`;
2. one known `+x` cell centre;
3. one known `+y` cell centre.

The UI then requests two additional residual checks. Manual confirmation records the original automatic hypotheses and the final transform. It does not overwrite the detector score or label the detector as correct.

## 9. Rejection conditions

Reject rather than guess when:

- the arena is absent;
- the main board is critically cropped;
- basis directions are inverted or degenerate;
- too few landmarks are visible;
- transform hypotheses remain ambiguous;
- p95 residual exceeds 0.16 cell;
- the image appears to contain a replay, montage or multiple game views.

## 10. Output

The registration stage emits the `registration` object inside `RecognitionResult`, including confidence, reason codes and alternatives. The solver receives only logical coordinates produced after registration is confirmed.
