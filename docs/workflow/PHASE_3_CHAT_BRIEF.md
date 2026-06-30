# PHASE 3 CHAT BRIEF

We are continuing **GROUGALORASALAR SOLVER**.

Read completely:

1. `MASTER_SPEC.md`
2. `CURRENT_STATUS.md`
3. `DECISIONS.md`
4. `docs/arena/ARENA_DIGITAL_TWIN_SPEC.md`
5. `docs/editor/MANUAL_STATE_EDITOR_SPEC.md`
6. `docs/editor/ARENA_VALIDATION_CATALOG.md`
7. `data/arena/arena-model.draft-v0.5.0.json`
8. `data/arena/reference-turn.manual.json`
9. `NEXT_STEP.md`

## Exclusive task

Create **Phase 3 — Solver Behaviour & Test Oracle Specification**.

## Required outputs

- exact action-enumeration contract for all four spells;
- rule-gated transition semantics;
- state-transition trace format;
- candidate ranking and deterministic tie-breaks;
- impossible/ambiguous state handling;
- fixture catalogue with expected outcome sets;
- property-test specification;
- updated master v0.4.0;
- complete Phase-3 ZIP.

## Constraints

- no Codex;
- no automatic recognition implementation;
- unknown mechanics remain explicit profile values;
- the provisional arena boundary and projection anchor may not be silently promoted;
- fixtures depending on unknown mechanics must expect a blocked or confirmation status.
