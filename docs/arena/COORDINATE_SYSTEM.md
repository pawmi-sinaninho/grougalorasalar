# CANONICAL COORDINATE SYSTEM — v0.3.0

## 1. Verified source image facts

The retained reference file is **1951 × 1267 pixels**. The Phase-1 note stating `1527 × 991` was incorrect and is superseded by direct file inspection and SHA-256 verification.

Reference SHA-256:

```text
2756a38a4451117001dedeab2e4da14423d4aa50978bc4549c9ff0cb1340f976
```

## 2. Logical axes

The arena uses integer logical cells `(x, y)`.

- `+x` points down-right on the screenshot.
- `+y` points down-left on the screenshot.
- the draft projection origin is logical cell `(0, 0)` near the visual centre pattern.

This orientation preserves the Phase-1 square-grid movement contracts.

## 3. Provisional single-reference transform

For `user_reference.png`:

```text
origin_pixel = (964.895, 441.7425)
basis_x      = ( 66.75, 33.375)
basis_y      = (-66.75, 33.375)
```

Projection:

```text
pixel_x = 964.895  + 66.75*x - 66.75*y
pixel_y = 441.7425 + 33.375*x + 33.375*y
```

Approximate inverse before snapping:

```text
dx = pixel_x - 964.895
dy = pixel_y - 441.7425

x_float = 0.5 * (dx / 66.75 + dy / 33.375)
y_float = 0.5 * (-dx / 66.75 + dy / 33.375)
```

The editor rounds to the nearest integer cell only when the pixel point is within the configured snap tolerance.

## 4. Accuracy status

The transform was fitted from the two dominant floor-line families and manually checked against:

- three visible glyph cells;
- the controlled player cell;
- multiple pillar bases;
- the centre lattice.

Estimated residual on the retained screenshot is approximately **2.5 pixels**. This is not a cross-resolution calibration guarantee.

## 5. Projection anchor

`projectionAnchorCell = (0, 0)` is a **draft convention**, selected from the arena centre and the guide's centre-pattern description. It is not promoted to verified gameplay truth until a second clean screenshot or a current replay confirms the same physical origin.

Consequences:

- the manual editor may encode the reference screenshot;
- glyph offsets may be stored;
- authoritative solving remains blocked while `anchorConfirmed = false`.

## 6. Cell classes

Every candidate cell belongs to exactly one draft class:

- `walkable_observed`: a visible player, pillar or glyph proves the cell is part of the arena presentation;
- `walkable_confirmed`: unobscured interior floor in the retained screenshot;
- `boundary_unverified`: visible or partial edge floor not safe to promote from one screenshot;
- `occluded_unknown`: cell centre lies under HUD or foreground art;
- `permanent_blocked`: directly proven non-walkable interior cell.

Version 0.3.0 intentionally contains no promoted `permanent_blocked` cell. Apparent holes near the border are kept outside the confirmed mask or in an uncertain class.

## 7. Solver boundary

The tactical solver receives logical cells only. Pixel coordinates, crop dimensions and calibration residuals remain editor/vision metadata.
