# PAGE, COMPONENT & STATE INVENTORY — Phase 5

## 1. Routes

| Route | Purpose | Availability |
|---|---|---|
| `/` | explanation, upload/paste and privacy choice | public |
| `/analyse/[analysisId]` | complete review, correction, solve and result workspace | token-protected |
| `/methode` | what is detected, what remains manual, rule limits | public |
| `/confidentialite` | retention, consent, deletion and contact text | public |
| `/diagnostic` | fixture browser, contract checks and traces | development/test only |

No login, profile, dashboard or screenshot history exists in V1.

## 2. Primary workspace layout

Desktop `>=1180px`:

```text
Top status rail
+-------------------------------------------------------------+
| screenshot workbench (min 65%) | review/result panel 35%    |
| zoom/pan + overlay             | next unresolved item        |
|                                 | validation + primary action |
+-------------------------------------------------------------+
Bottom audit/trace drawer
```

Tablet `768–1179px`: screenshot above, panel below, persistent compact status rail.

Mobile `<768px`: upload status and final recommendation are readable, but precision correction is blocked. The user receives the exact message to continue on a larger screen. No imprecise touch editor is shipped under the label “supported”.

## 3. Workspace states

| UI state | Primary content | Primary action |
|---|---|---|
| `created` | drop zone and supported-format note | `Ajouter une capture` |
| `uploading` | byte progress and cancel | `Annuler` |
| `ingesting` | file checks | none |
| `recognition_running` | stage progress without fake percentages | none |
| `registration_review` | anchors and residual checks | `Valider l’alignement` |
| `board_review` | player, pillars, completeness, glyphs | next unresolved field |
| `resources_review` | action budget and four spell states | `Valider les ressources` |
| `rules_blocked` | named mechanical unknowns | confirm supported assumption or export evidence |
| `ready_for_solver` | compact verified-state summary | `Calculer le tour` |
| `solving` | cancellable calculation state | `Annuler le calcul` |
| `solved` | numbered actions, final cell and outcome | `Copier les étapes` |
| `confirmation_required` | recommendation plus named assumption | `Confirmer l’hypothèse` |
| `no_safe_solution` | exhausted definite search evidence | `Vérifier l’état` |
| `rejected` | one reason and one remedy | `Choisir une autre capture` |
| `technical_failure` | request ID and retry/delete choices | `Réessayer` |
| `expired` | no data recoverable | `Nouvelle analyse` |

## 4. Component inventory

### Shell

- `ProductHeader`: product name, locale, method/privacy links;
- `AnalysisStatusRail`: lifecycle, unresolved count, expiry, deletion;
- `WorkspaceSplitPane`: responsive layout only;
- `AuditDrawer`: detector proposal, overrides, confirmations and solver trace.

### Upload

- `ScreenshotDropzone`: drag, paste and file picker;
- `ImageRequirements`: type, size, board visibility and solo scope;
- `ConsentChoice`: ephemeral default plus optional quality-improvement consent;
- `UploadProgress` and `UploadFailure`.

### Board workbench

- `ScreenshotViewport`: pan/zoom, device-pixel-ratio aware;
- `LogicalGridLayer`: non-interactive canonical cells;
- `ObservationLayer`: player, pillars, glyphs, conflicts;
- `ActionOverlayLayer`: sequence arrows and numbered targets;
- `OverlayLegend`: shapes, not colour alone;
- `RegistrationTool`, `PlayerTool`, `PillarTool`, `GlyphTool`;
- `ZoomControls`, `FitToBoard`, `UndoRedoControls`.

### Review panel

- `ReviewQueue`: tactical-impact ordering;
- `ObservationCard`: proposal, alternatives, confidence components and source;
- `PillarSetCompletenessCard`;
- `SpellStateGrid`;
- `ActionBudgetField`;
- `ProgressTrackField`;
- `ConflictResolver`;
- `ValidationSummary`;
- `PrimaryWorkflowAction` with exact state-dependent label.

### Result

- `ActionSequence`: numbered casts with spell, target and destination;
- `ExpectedOutcome`: final cell, race direction, recharge and terminal limitation;
- `AssumptionBanner`;
- `AlternativesAccordion` limited to two;
- `CopyStepsButton`;
- `StateInvalidatedNotice`.

## 5. Component invariants

- only one component may issue the primary workflow action;
- every logical cell control has a keyboard equivalent;
- colour is redundant with symbol and text;
- confidence is never presented without gate state and reason;
- progress unknown removes terminal claims from result components;
- post-solve edits immediately hide old action arrows;
- raw logical coordinates appear in diagnostics, not the normal player instruction;
- the screenshot remains visually dominant during correction.

## 6. Keyboard map

- `1–4`: pillar type;
- `B`, `W`, `E`: glyph black, white, erase;
- `P`: player tool;
- arrow keys: move selected marker;
- `Delete`: delete selected pillar;
- `Ctrl/Cmd+Z`, `Ctrl/Cmd+Shift+Z`: undo/redo;
- `Space` while dragging: pan;
- `+`, `-`, `0`: zoom in, out, fit;
- `Esc`: cancel active operation;
- `Enter`: accept the focused review item only when no alternative is unresolved.

All shortcuts are shown in tooltips and may not override browser/system shortcuts unexpectedly.
