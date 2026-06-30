# ARENA DIGITAL TWIN SPECIFICATION — Phase 2

## 1. Purpose

The arena digital twin is the implementation-independent logical representation of the fixed Grougalorasalar combat map. It supports manual state entry before computer vision exists.

It does not decide movement legality and does not resolve unknown gameplay rules.

## 2. Authoritative artefacts

- `data/arena/arena-model.draft-v0.5.0.json`
- `data/arena/cell-classification.csv`
- `data/arena/calibration-anchors.json`
- `assets/annotated/reference_grid_overlay.png`
- `assets/annotated/arena_mask_diagram.png`

The JSON arena model is the machine-readable source. Diagrams are review aids.

## 3. Draft mask summary

Version 0.3.0 contains 338 candidate cells:

| Class | Count | Meaning |
|---|---:|---|
| `walkableConfirmed` | 193 | visible unobscured interior floor |
| `walkableObserved` | 34 | visible object/glyph/player occupancy proves the cell |
| `boundaryUnverified` | 37 | partial or edge floor requiring further evidence |
| `occludedUnknown` | 74 | hidden by HUD or foreground art |
| `permanentBlocked` | 0 | no interior cell is promoted without direct proof |

The counts are acceptance-test values for this version, not final arena dimensions.

## 4. Cell-use policy

### Manual evidence capture

The editor permits placement on:

- `walkableConfirmed`;
- `walkableObserved`;
- `boundaryUnverified` after explicit confirmation;
- `occludedUnknown` only in an evidence-review mode.

### Solver use

Until the mask is verified:

- destinations on `walkableConfirmed` or `walkableObserved` may be simulated;
- destinations on `boundaryUnverified` produce `confirmation_required`;
- destinations on `occludedUnknown` produce `blocked_unverified_rule`;
- `permanentBlocked` and outside cells are invalid.

## 5. Permanent architecture

No interior blocker is asserted in v0.3.0. Apparent pits, wall edges and foreground structures are represented as:

- outside the candidate envelope;
- boundary-unverified cells;
- pixel occlusion regions.

This avoids converting visual ambiguity into tactical truth.

## 6. Occlusion catalogue

The draft includes six pixel-space regions:

- initiative bar;
- top-left spell bar;
- top-right HUD;
- left foreground arch;
- right foreground wall;
- lower foreground/track structure.

Occlusion regions affect editor confidence and calibration only. They never enter the rules engine.

## 7. Central pattern anchor

The physical reference pattern is encoded relative to logical `(0, 0)`. The anchor remains provisional.

Reference screenshot offsets:

```text
black: (-1,-1), (1,-1), (1,1)
white: (0,-3), (0,2), (2,-1)
```

The editor stores both:

- relative offsets;
- physical source cells on the arena.

This makes anchor corrections auditable.

## 8. Reference objects

The supplied screenshot can be reconstructed using:

- player `(7,-1)`;
- 27 pillar cells and spell types;
- the six glyph cells above;
- unknown resources and progress.

See `docs/arena/REFERENCE_TURN_ENCODING.md`.

## 9. Promotion gate

The arena model may move from `draft_single_reference` to `draft_multi_reference` only when:

1. at least one additional clean screenshot is registered;
2. the same logical grid explains both images;
3. the centre origin is independently confirmed;
4. every outer-ring cell is classified or explicitly remains unknown;
5. no object requires a contradictory cell assignment.

It becomes `verified` only after gameplay confirms destination validity at relevant boundary cells.
