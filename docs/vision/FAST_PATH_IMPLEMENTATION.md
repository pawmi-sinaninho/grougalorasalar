# Fast Recognition Path — v0.8.0

## Scope

This implementation handles the fixed Grougalorasalar arena using deterministic image registration and logical-cell sampling. It is a baseline detector, not an accuracy certification. Every critical output remains `review_required` while `modelCalibrationStatus = unvalidated`.

## Pipeline

1. Decode and safely re-encode the upload.
2. Build a 1280-pixel-wide WebP working copy.
3. Match cached ORB features from the retained reference against the working copy.
4. Estimate a partial affine transform using RANSAC.
5. Reject weak, spatially concentrated or ambiguous transforms.
6. Warp the image to the 1951 × 1267 canonical reference frame.
7. Inspect only known arena cells and known icon colour/shape bands.
8. Detect the controlled player through the blue unit-base region at candidate cell centres.
9. Match an optional registered fixture signature for versioned glyph proposals.
10. Emit logical observations and performance timings.
11. Require user review for every solver-blocking field.
12. Pass only the logical state—not pixels or transforms—to the solver.

## Stable registration evidence

The detector does not depend on one button label, language string or exact resolution. It uses distributed local features from:

- arena floor/grid texture;
- fixed architectural edges around the arena;
- stable board boundaries and decorative landmarks;
- multiple spatial regions of the board.

At least 40 RANSAC inliers and three spatial regions are required by the executable baseline. The Phase-4 stricter acceptance policy remains the release authority; v0.8.0 therefore returns review-required proposals even when the transform is numerically strong.

## Working resolution

- minimum registration working width: 960 px;
- maximum registration working width: 1280 px;
- no dependence on an exact source resolution;
- canonical output: 1951 × 1267 px;
- board classification crop: canonical x=100…1850, y=0…880.

The browser and server both create bounded working copies. The original safe-normalised image is retained only inside the ephemeral analysis directory for review and annotated output.

## Affine basis

The retained logical basis is:

```text
origin  = (964.895, 441.7425)
basisX  = ( 66.75,   33.375)
basisY  = (-66.75,   33.375)
```

Registration maps this basis into the uploaded image. Classification then occurs in canonical coordinates. Overlay generation uses the registered image-space origin and basis instead of scaling hard-coded pixels.

## Ambiguity and rejection

A registration is rejected to manual correction when any of the following is true:

- fewer than 60 ratio-test matches;
- fewer than 40 RANSAC inliers;
- fewer than three spatial regions;
- p95 residual above 0.16 logical cell;
- a second affine hypothesis approaches the best result;
- scale outside 0.45…1.60;
- absolute rotation above 3 degrees.

The fallback sequence is:

1. retained reference identity path;
2. cached ORB/RANSAC affine registration;
3. registered fixture signature, if uniquely matched;
4. manual registration/correction.

No unsafe default state is emitted when registration fails.

## Pillar classification

Pillars are found from the common pedestal/icon location after canonical warp. Four HSV bands represent the four known icon types. Component centroid offsets are calibrated relative to the logical cell centre. Each component is snapped to the nearest candidate cell and rejected above 0.25-cell residual.

Duplicate colour proposals at one cell are resolved using snap residual plus expected component area. The resulting pillar set is still marked incomplete until a user confirms completeness.

## Player detection

The controlled avatar is distinguished from the lower Crocoburio runner by examining only candidate cells on the main board. A blue/cyan unit-base patch is scored around each logical cell centre. The best cell requires:

- at least 150 qualifying pixels;
- a score ratio of at least 2.0 over the second-best cell.

This detector does not inspect lower-track combat-order numbers as action points.

## Glyph and UI fields

The four arena fixtures contain conservative glyph annotations; ambiguous or occluded cells stay in `unknownCandidateCells`. The verified profile supplies 12 AP, while calibrated toolbar recognition supplies spell availability and exact zero charges. Positive exact counts and progress indices remain unknown unless a calibrated cue resolves them.

OCR is not imported or invoked in the standard path.

## Cache behaviour

The engine caches at process start:

- the reference image;
- ORB reference keypoints/descriptors;
- arena candidate cells;
- fixture metadata;
- registered fixture fingerprints;
- colour/component calibration constants.

Templates and feature descriptors are not reloaded for each screenshot.

## Performance instrumentation

The API exposes these measurements separately:

- decode;
- orientation/RGB conversion;
- browser/server working-copy creation;
- safe normalised write;
- registration;
- canonical warp;
- cell sampling;
- fixture matching;
- total recognition;
- server screenshot-to-state;
- solver duration.

All budgets are engineering targets until measured on supported user hardware.

## Correction behaviour

Any editor command:

- increments `stateVersion`;
- clears the previous recommendation;
- sets `recommendationInvalidated = true`;
- removes the previous annotated URL in the browser;
- forces a new solve before actions can be shown again.
