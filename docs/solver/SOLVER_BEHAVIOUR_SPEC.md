# SOLVER BEHAVIOUR SPECIFICATION — Phase 3

## 1. Scope

This document fixes the deterministic behaviour of the turn solver. It does **not** promote any unresolved DOFUS mechanic. A concrete `RulesProfile` supplies mechanics; the solver supplies repeatable enumeration, transition, classification and ranking.

## 2. Inputs

A solve request consists of:

- one schema-valid `TurnState`;
- one schema-valid `RulesProfile`;
- one arena model;
- the rule catalogue and dependency map;
- request mode `authoritative` or `review`.

The screenshot itself is not read by the solver.

## 3. Preflight order

The implementation must evaluate these checks in order and collect all applicable reason codes:

1. schema validity;
2. solo-only constraint;
3. exactly one player and no duplicate pillar occupancy;
4. valid arena-model reference and usable calibration;
5. critical board and glyph fields confirmed;
6. projection anchor confirmed;
7. action budget resolved from state or profile;
8. rules-profile consistency;
9. spell-state consistency.

Structural contradictions return `invalid_state`. Missing or unresolved mechanical data returns `blocked_unverified_rule`; it is not mislabeled as invalid input.

## 4. Action budget source

Resolution order:

1. use `TurnState.spellState.actionBudget` when non-null and confirmed;
2. otherwise use `RulesProfile.resources.actionBudgetPerTurn` when non-null;
3. when both are non-null and differ, return `invalid_state` with `S-INVALID-BUDGET-CONFLICT`;
4. when neither is known, return `blocked_unverified_rule` with `S-BLOCK-ACTION-BUDGET`.

Movement action cost must be a positive integer. Zero-cost movement is rejected as a profile error because it can make the finite search contract invalid.

## 5. Search graph

A node key is:

```text
(player cell,
 remaining action budget,
 per-spell resource state,
 per-spell cast counts in availability-only mode)
```

Every node yields an explicit terminal `end_turn` candidate. A movement edge is added only for a definite-legal action. Conditional actions are recorded in a parallel conditional graph and are not merged into the authoritative graph.

Equivalent definite nodes are deduplicated. The retained path is the path with the lexicographically smallest canonical sequence key. Because every movement action has positive cost, the graph is finite.

## 6. Resource legality

### Numeric mode

A spell is definite-legal only when:

- availability is not `unavailable`;
- numeric value is known;
- value is at least its charge cost;
- action budget is sufficient.

Charge and action cost are committed immediately when the edge is traversed.

### Availability-only mode

A confirmed `available` spell permits one definite cast in a sequence. A second cast of the same spell is conditional on R-048 and therefore belongs only to the conditional graph. This is a conservative product boundary, not a claim that the spell actually depletes after one use.

`unknown` availability does not block actions using other confirmed spells.

## 7. Arena authority

- `walkable_confirmed` and `walkable_observed`: definite destination;
- `boundary_unverified`: conditional destination requiring confirmation;
- `occluded_unknown`: blocking destination;
- `permanent_blocked` or outside the candidate envelope: definite invalid destination.

A manually confirmed boundary cell is treated as `walkable_observed` for that solve request only and is preserved in `arena.cellConfirmations`.

## 8. Terminal resolution

For each definite terminal candidate:

1. determine stationary condition from the configured reference;
2. inspect direct physical central glyph cells;
3. project all black and white offsets around the final cell;
4. collect pillar IDs by exact logical-cell equality;
5. determine adverse conditions;
6. determine race direction;
7. apply or suppress recharge according to the profile;
8. derive next resource state;
9. derive terminal fight state only when current progress and track length are known.

Unknown track indices do not block reporting `crocoburio_advance` or `dragon_advance`; they only force `terminalFightState = unknown`.

## 9. Definite, conditional and invalid

- **definite:** every legality, destination, resource and outcome field is fixed by the input and profile;
- **conditional:** at least one supported branch or uncertain arena cell can change the result;
- **invalid:** the candidate violates a definite rule or structural invariant.

A conditional action may be shown in review diagnostics, but never mixed into the definite candidate count.

## 10. Completeness requirement

`no_safe_solution` is legal only when:

- the definite graph is complete for all resolved mechanics;
- at least one definite terminal candidate exists;
- every definite terminal candidate advances the dragon or is otherwise adverse;
- no conditional candidate can produce a safe ending.

If an unresolved branch could contain a safe result, the status is `blocked_unverified_rule`.
