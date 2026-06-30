# MANUAL STATE EDITOR SPECIFICATION — Phase 2

## 1. Goal

A human must be able to reconstruct a screenshot as a structured turn state without automatic recognition.

The editor is a controlled evidence-entry tool, not a free-form paint canvas.

## 2. Required workflow

### Stage 1 — Source and calibration

- load or paste screenshot;
- display actual dimensions;
- select an arena model;
- verify origin and both logical axes;
- show residual and occlusion warnings;
- block later export if calibration is invalid.

### Stage 2 — Board objects

Tools:

- **Player**: click one cell to set or move the controlled avatar;
- **Pillar**: choose one of four spell types, then click to add;
- **Select**: inspect, move or reclassify an existing object;
- **Erase**: remove a pillar or player marker;
- **Boundary override**: permit a confirmed object on an unverified cell with a recorded confirmation.

Rules:

- one player maximum;
- one pillar maximum per logical cell;
- player and pillar may not share a cell;
- object IDs remain stable when moved or recoloured;
- every edit is undoable and recorded in the audit log.

### Stage 3 — Glyph pattern

The editor shows the physical centre-pattern ROI and a logical pattern board.

Tools:

- paint black;
- paint white;
- erase;
- move provisional anchor;
- convert physical source cells to offsets.

Rules:

- one cell cannot be both black and white;
- duplicate offsets are rejected;
- changing the anchor recomputes offsets but preserves physical source cells;
- an unconfirmed anchor blocks authoritative solving.

### Stage 4 — Resources

For each spell:

- availability: available / unavailable / unknown;
- optional numeric value;
- confidence;
- manual confirmation.

Action budget:

- integer when known;
- unknown when not visible;
- never inferred from ordinary DOFUS defaults.

### Stage 5 — Progress

For both runners:

- choose a visible track index;
- or set unknown;
- store confidence and confirmation independently.

The editor does not enforce a Crocoburio track maximum while V-001 remains unresolved.

### Stage 6 — Review and export

Review panel must show:

- player cell;
- pillar count and colour count;
- black and white offsets;
- resource completeness;
- progress completeness;
- all visual warnings;
- all mechanical assumptions;
- export status.

## 3. Interaction details

- left click: apply active tool;
- right click or `Esc`: cancel current placement;
- `Delete`: remove selected object;
- `Ctrl+Z` / `Ctrl+Shift+Z`: undo / redo;
- arrow keys: move selected marker one logical cell;
- number keys `1–4`: select pillar type;
- `B`, `W`, `E`: black, white, erase glyph tool;
- zoom changes rendering only and never logical coordinates.

## 4. Confirmation model

A confirmation is a structured record, not a generic checkbox.

Required confirmation kinds:

- `visual`: user confirms an ambiguous object;
- `arena_boundary`: user permits an uncertain cell;
- `projection_anchor`: user accepts the draft centre origin;
- `mechanical`: user accepts a supported but unverified rule.

Confirmations include an ID, statement, boolean value and audit timestamp in implementation.

## 5. Validation timing

Validation runs:

- after every edit;
- before stage transition;
- before turn-state export;
- before solver invocation.

Blockers are shown adjacent to the affected field and in the review list.

## 6. Export products

The editor exports:

1. a `TurnState` JSON;
2. a `ManualEditorSession` audit JSON;
3. optionally an annotated screenshot;
4. no original screenshot retention unless consent is explicit.

## 7. Reference acceptance case

The editor must reproduce `data/arena/reference-turn.manual.json` from the retained screenshot.

Expected manual result:

- player: `(7,-1)`;
- pillars: 27;
- black cells: 3;
- white cells: 3;
- resources: unknown;
- progress: unknown;
- export state: `confirmation_required`, not `solved`.

## 8. Phase-4 recognition import

The editor can now start from a `RecognitionResult` instead of an empty board.

It must preserve three layers:

1. original detector proposal;
2. accepted or overridden logical value;
3. complete user audit.

Recognition import rules:

- every observation remains addressable by stable ID;
- accepting a proposal records `accept_detection`;
- changing it records the observation ID in `overriddenObservationIds`;
- resolving a method conflict records `resolve_conflict`;
- confidence is never rewritten to 1.0 after manual confirmation;
- pillar-set completeness is confirmed separately from each pillar;
- any edit after a solver result invalidates that result.

The `ManualEditorSession.recognitionLink` object connects the manual session to its recognition proposal and unresolved conflicts.
