# MANUAL EDITOR VALIDATION AND ERROR CATALOGUE

| Code | Severity | Condition | Required behaviour |
|---|---|---|---|
| `E-001` | blocker | image missing or unreadable | stop calibration |
| `E-002` | blocker | width/height unavailable | stop calibration |
| `E-010` | blocker | origin or basis point missing | stop object entry |
| `E-011` | blocker/warning | calibration residual above threshold | require correction or confirmation |
| `E-012` | blocker | degenerate or parallel basis vectors | reject transform |
| `E-020` | blocker | object outside candidate envelope | reject placement |
| `E-021` | warning | object on `boundaryUnverified` | require arena-boundary confirmation |
| `E-022` | blocker | object on `occludedUnknown` in normal mode | use evidence-review mode or move object |
| `E-030` | blocker | two pillars occupy one cell | remove or move one pillar |
| `E-031` | blocker | player and pillar share a cell | correct occupancy |
| `E-032` | blocker | pillar type missing | select one of four spell types |
| `E-033` | blocker | more than one player marker | keep exactly one |
| `E-040` | blocker | glyph cell is both black and white | choose one colour |
| `E-041` | blocker | projection anchor unconfirmed | confirm or keep solver blocked |
| `E-042` | warning | no black glyph entered | require explicit confirmation |
| `E-043` | warning | no white glyph entered | require explicit confirmation |
| `E-050` | blocker | multiplayer detected | reject V1 state |
| `E-060` | blocker for solve | spell used by recommendation is unknown/unavailable | enter or confirm state |
| `E-061` | blocker for solve | action budget unknown | enter budget |
| `E-070` | blocker | negative progress index | correct value |
| `E-071` | warning | progress index unknown | allow evidence export; block race prediction |
| `E-080` | blocker for solve | required rules-profile value unknown | return `blocked_unverified_rule` |
| `E-090` | blocker | unresolved validation issue at export | export editor draft only |

## Message requirements

Every message must contain:

- the affected field or cell;
- why the state is unsafe;
- the exact correction action;
- whether the issue blocks JSON export, solver use or both.

Example:

```text
E-021 — Cell (11,2) is on the unverified arena boundary.
Confirm that this cell is playable in the screenshot or move pillar P27.
The state may be saved as evidence, but authoritative solving remains blocked.
```
