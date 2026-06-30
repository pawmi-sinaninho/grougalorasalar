# REFERENCE SCREENSHOT ANALYSIS — v0.3.0

## File identity

- Path: `assets/reference/user_reference.png`
- Actual dimensions: **1951 × 1267**
- SHA-256: `2756a38a4451117001dedeab2e4da14423d4aa50978bc4549c9ff0cb1340f976`
- Source type: user-supplied current-style screenshot

The former `1527 × 991` dimension statement was a documentation error.

## Confirmed visual regions

### Main board

The main tactical board occupies the upper part of the screenshot. It contains the controlled avatar, generated coloured pillars and the physical central black/white reference pattern.

### Controlled avatar

The selected yellow-green crocodile-like unit on the main board is manually snapped to logical cell `(7, -1)` in the draft transform.

### Progress entities

- lower-left white route: Crocoburio runner;
- lower-right dark route: Grougalorasalar;
- neither is the controlled board avatar.

### Resource lanes

Four colour-coded resource lanes are visible above the progress tracks. Their exact numeric semantics remain unverified.

## Manual reference encoding

The current draft identifies:

- 27 visible pillars;
- 1 controlled-player cell;
- 3 visible black reference cells;
- 3 visible white reference cells.

The full encoding is stored in:

```text
data/arena/reference-turn.manual.json
```

The visual audit is stored in:

```text
assets/annotated/reference_entities_overlay.png
```

## Limitations

- one screenshot cannot prove the entire edge mask;
- foreground architecture hides lower and side cells;
- the central projection origin is provisional;
- spell charges, AP/cast budget and progress indices are not encoded as facts;
- no automatic object recognition is claimed in this phase.
