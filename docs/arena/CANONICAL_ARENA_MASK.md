# CANONICAL ARENA MASK — v0.9.0

> **Boundary-refinement status:** the earlier “canonical complete” conclusion is superseded. The 338 coordinates remain a provisional working set with 43 confirmed and 7 unresolved boundary cells.

## 1. Result

The current Grougalorasalar working mask contains **338 unique coordinates**. The count is structurally reproducible, but seven boundary positions are not yet independently confirmed.

This value is no longer a visual estimate. It is derived from one exact set of unique integer coordinates and independently reproduced through both logical diagonal axes.

The machine-readable source of truth is:

```text
data/arena/grougalorasalar.cells.json
```

All SVG and PNG assets are generated from this JSON. They are not authored or corrected by image generation.

## 2. Evidence hierarchy

The canonical mask combines four evidence types:

1. `assets/reference/empty_arena.jpeg` provides unobstructed grid lines, cell centres, alternating floor brightness and fixed architectural landmarks.
2. The user's green boundary annotation establishes that every marked outermost cell belongs to the combat map; the marked cell itself is included.
3. `assets/reference/user_hidden_cells_annotation.png` confirms outer cells hidden or partially hidden by architecture, rocks, foreground tracks or camera perspective.
4. The retained reference and four Phase-7 combat screenshots confirm that one logical grid registers across different live rounds and object layouts.

The original byte file of the green boundary annotation is not present. Its semantic rule remains documented, but it is no longer counted as per-cell evidence. A boundary cell is confirmed only with at least two accepted criteria.

## 3. Logical coordinate system

- origin cell: `(0, 0)`;
- `+x`: down-right on the screenshot;
- `+y`: down-left on the screenshot;
- reference image size: `1951 × 1267`;
- reference origin: `(964.895, 441.7425)`;
- `basisX = (66.75, 33.375)`;
- `basisY = (-66.75, 33.375)`.

Projection:

```text
pixel = origin + x*basisX + y*basisY
```

Each cell polygon is the logical square `[x±0.5, y±0.5]` projected through the same affine basis.

## 4. Exact footprint

The playable coordinate set is exactly the set of integer `(x, y)` satisfying:

```text
-12 <= x <= 13
-12 <= y <= 13
-11 <= x + y <= 13
-13 <= x - y <= 13
```

Additional properties:

- provisional working coordinates: `338`;
- boundary cells: `50`;
- exposed boundary edges: `104`;
- interior holes: `0`;
- permanent blocked cells inside the footprint: `0` currently asserted.
- confirmed / inferred / unresolved boundary cells: `43 / 0 / 7`.

The formula is a compact reproduction rule. The enumerated JSON list remains the runtime authority.

## 5. Independent cell-count verification

### Method A — unique coordinate list

```text
len(unique(x, y)) = 338
```

### Method B — rows grouped by `x + y`

There are 25 rows from `-11` through `13`. Their counts alternate between 14 and 13:

```text
14, 13, 14, 13, 14, 13, 14, 13, 14, 13, 14, 13, 14,
13, 14, 13, 14, 13, 14, 13, 14, 13, 14, 13, 14
```

Sum: `338`.

### Method C — rows grouped by `x - y`

There are 27 rows from `-13` through `13`. Their counts alternate between 13 and 12:

```text
13, 12, 13, 12, 13, 12, 13, 12, 13, 12, 13, 12, 13, 12,
13, 12, 13, 12, 13, 12, 13, 12, 13, 12, 13, 12, 13
```

Sum: `338`.

All three methods are generated and tested from the same coordinate semantics but use different grouping axes and detect different classes of omission or duplication.

## 6. Floor parity

Logical parity is defined by:

```text
parity = (x + y) mod 2
```

- parity `0`: `light`;
- parity `1`: `dark`.

Every orthogonal logical neighbour changes one of `x` or `y` by one and therefore must have the opposite parity.

The empty arena image provides an independent visual check:

- median LAB-L for parity 0: `208.0`;
- median LAB-L for parity 1: `182.5`;
- median separation: `25.5`.

Lighting, textures and occlusion can alter individual measured pixels. Therefore visible brightness validates the coordinate parity but never defines it.

## 7. Cell record contract

Each cell contains:

- deterministic integer `id` sorted by `y`, then `x`;
- stable string `stableId`;
- logical `(x, y)`;
- parity;
- source authority and confidence;
- boundary status;
- occlusion class;
- canonical reference centre;
- exact four-point reference polygon;
- reciprocal logical neighbours;
- provenance.

The solver uses logical coordinates. Sequential IDs are storage and UI references only.

## 8. Generated artefacts

Primary data and validation contracts:

```text
schemas/canonical-arena-cells.schema.json
schemas/canonical-arena-boundary.schema.json
data/arena/grougalorasalar.cells.json
data/arena/grougalorasalar.cells.csv
data/arena/grougalorasalar.boundary.json
data/arena/grougalorasalar.registration.json
data/arena/grougalorasalar.landmarks.json
```

Generated review/debug assets:

```text
assets/arena/grougalorasalar-mask.svg
assets/arena/grougalorasalar-mask.png
assets/arena/grougalorasalar-cell-centers.png
assets/arena/grougalorasalar-cell-polygons.png
assets/arena/grougalorasalar-debug-overlay.png
assets/arena/grougalorasalar-boundary-debug.png
assets/arena/validation/*.overlay.png
```

Rebuild:

```bash
python scripts/build_canonical_arena.py
```

Reproducibility check:

```bash
python scripts/build_canonical_arena.py --check
```

## 9. Registration use

The runtime public contract is:

```python
register_screenshot_to_arena(image, project_root) -> RegistrationResult
```

A compatibility alias is also exposed:

```python
registerScreenshotToArena(image, project_root)
```

Registration estimates the affine transform from the canonical reference to the submitted screenshot. After acceptance, all 338 canonical centres and polygons are projected into the screenshot. Recognition samples only predefined per-cell regions.

## 10. Authority boundary

The interior grid is stable for implementation. The outer footprint remains review-gated until `C009`, `C016`, `C025`, `C064`, `C081`, `C168` and `C193` receive a second accepted evidence criterion.

This does not verify:

- movement path or edge-collision behaviour;
- whether every boundary cell is a legal destination for every spell;
- projection-anchor gameplay semantics;
- unresolved mechanics V-001 through V-010;
- automatic object-detection accuracy.

Those remain separate gameplay and validation gates.
