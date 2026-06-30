# REFERENCE TURN MANUAL ENCODING

## Status

This is a manual reconstruction of the retained screenshot. It is a Phase-2 acceptance fixture, not a verified tactical turn.

## Core state

- arena model: `grougalorasalar-arena-draft-0.3.0`
- player: `(7,-1)`
- projection anchor: `(0,0)` — provisional
- black offsets: `(-1,-1)`, `(1,-1)`, `(1,1)`
- white offsets: `(0,-3)`, `(0,2)`, `(2,-1)`
- action budget: 12 from the verified rules profile
- spell availability/charge: unknown
- both progress indices: unknown

## Pillars

| ID | Cell | Spell type | Manual confidence |
|---|---|---|---:|
| `P01` | `(-9,-1)` | `indecision` | 0.95 |
| `P02` | `(-6,-2)` | `attraction` | 0.95 |
| `P03` | `(-4,-2)` | `repulsion` | 0.98 |
| `P04` | `(-1,-5)` | `indecision` | 0.98 |
| `P05` | `(0,-8)` | `reflection` | 0.94 |
| `P06` | `(2,-9)` | `attraction` | 0.90 |
| `P07` | `(-7,1)` | `reflection` | 0.98 |
| `P08` | `(-6,4)` | `repulsion` | 0.94 |
| `P09` | `(-3,1)` | `attraction` | 0.98 |
| `P10` | `(2,-5)` | `indecision` | 0.96 |
| `P11` | `(4,-5)` | `attraction` | 0.98 |
| `P12` | `(-1,1)` | `indecision` | 0.96 |
| `P13` | `(0,1)` | `reflection` | 0.96 |
| `P14` | `(2,-2)` | `reflection` | 0.98 |
| `P15` | `(-3,6)` | `reflection` | 0.96 |
| `P16` | `(0,4)` | `repulsion` | 0.98 |
| `P17` | `(2,1)` | `indecision` | 0.97 |
| `P18` | `(5,-2)` | `reflection` | 0.96 |
| `P19` | `(8,-4)` | `repulsion` | 0.88 |
| `P20` | `(-1,7)` | `attraction` | 0.98 |
| `P21` | `(3,4)` | `indecision` | 0.95 |
| `P22` | `(6,0)` | `indecision` | 0.98 |
| `P23` | `(3,7)` | `repulsion` | 0.97 |
| `P24` | `(6,3)` | `repulsion` | 0.97 |
| `P25` | `(10,0)` | `attraction` | 0.92 |
| `P26` | `(1,11)` | `indecision` | 0.95 |
| `P27` | `(11,2)` | `attraction` | 0.90 |

## Machine-readable fixture

```text
data/arena/reference-turn.manual.json
```

## Visual audit

```text
assets/annotated/reference_entities_overlay.png
```

## Expected validation result

- object geometry: valid;
- duplicate occupancy: none;
- player/pillar collision: none;
- visual board state: manually reproducible;
- projection anchor: confirmation required;
- resources and progress: incomplete;
- solver status: blocked, never `solved`.
