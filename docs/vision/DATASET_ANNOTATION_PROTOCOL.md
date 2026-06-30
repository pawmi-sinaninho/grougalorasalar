# DATASET & ANNOTATION PROTOCOL — Phase 4

## 1. Dataset unit

One record represents one screenshot of one combat turn plus capture metadata and structured labels. Consecutive screenshots from the same run share a `sessionId` and split group.

## 2. Required coverage dimensions

The corpus must deliberately cover:

- 1920×1080, 2560×1440, 3840×2160 and other real resolutions;
- fullscreen, borderless and windowed modes;
- supported UI-scale variants;
- French, German and English clients;
- different visual presets and colour profiles;
- cursor hover, selected cell, spell effects and partial occlusion;
- lossless and realistic lossy screenshots;
- normal turns, near-edge player positions and dense pillar layouts;
- screenshots missing optional lower UI regions;
- negative examples from other fights and visually similar maps.

Coverage is reported, not assumed from aggregate screenshot count.

## 3. Privacy and consent

Each image records separate permission for:

- retention;
- model training;
- public display.

No permission is inferred from upload. Chat, account names, guild names or unrelated personal content are redacted before training or public examples. Hashes are calculated after canonical orientation but before visual redaction, with both versions linked internally when consent allows.

## 4. Annotation layers

### Layer A — image and registration

- arena present/absent;
- complete/cropped regions;
- logical transform anchors;
- registration quality issues.

### Layer B — board state

- controlled player cell;
- every pillar cell and spell type;
- visibility/occlusion per pillar;
- multiplayer state.

### Layer C — glyph state

- physical black cells;
- physical white cells;
- anchor cell;
- uncertain/occluded cells.

### Layer D — UI state

- action budget;
- each spell availability/value;
- Crocoburio progress;
- Grougalorasalar progress;
- turn number when visible.

Unknown is a valid label. Annotators may not fill missing UI values from game knowledge.

## 5. Annotation workflow

1. first annotator labels all visible fields;
2. second independent annotator labels all solver-blocking fields;
3. automatic invariant checks run;
4. disagreements are adjudicated by a third reviewer or replay evidence;
5. only `adjudicated_gold` records enter the locked test set.

The project reference screenshot remains `provisional_single_annotation`; it is not a gold accuracy benchmark.

## 6. Split policy

Split by capture session, not individual image. Screenshots from one run, device or near-duplicate sequence may not cross train/validation/test boundaries.

Recommended target ratios:

- 70% training;
- 15% validation;
- 15% locked test.

Ratios are secondary to stratification. A sparse resolution/UI-scale stratum may be reserved entirely for holdout testing.

## 7. Augmentation policy

Allowed for training only:

- resize within supported scale range;
- mild compression;
- small brightness/contrast changes;
- non-destructive cursor overlays;
- bounded crop/padding that preserves labelled visibility.

Forbidden:

- geometric warps that change cell labels without recomputation;
- colour changes that alter pillar or glyph class;
- synthetic pillar insertion into the locked test set;
- near-duplicate augmented copies in validation/test.

Synthetic data is reported separately from real screenshots.

## 8. Quality checks

Automatic checks include:

- unique player;
- unique pillar cells;
- no player/pillar overlap;
- black/white disjointness;
- all labelled cells inside the annotated arena envelope or explicitly marked boundary override;
- transform round-trip residual;
- session progress monotonicity as a warning;
- image hash duplicate detection.

## 9. Versioning

Every record stores:

- annotation schema version;
- arena-model revision;
- label revision;
- annotator count and adjudication status;
- client version when known;
- split group.

Changing an arena transform or projection anchor invalidates affected gold labels until re-adjudicated.
