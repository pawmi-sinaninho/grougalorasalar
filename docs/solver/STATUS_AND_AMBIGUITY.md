# STATUS, AMBIGUITY AND FAILURE HANDLING

## Authority classes

Rule-catalog statuses map to solver authority as follows:

| Rule status | Solver authority |
|---|---|
| `verified_multi_source` | authoritative |
| `verified_direct_observation` | authoritative |
| `single_source_supported` | confirmable |
| `screenshot_observed` | authoritative only for the specific visual fact, never for a mechanic |
| `hypothesis` | blocking |
| `unknown` | blocking |

## Exact status semantics

### `invalid_state`

Use only for contradictory or malformed input: duplicate occupancy, player outside arena, black/white overlap, conflicting budgets, invalid profile ranges, multiplayer or missing mandatory identifiers.

### `blocked_unverified_rule`

Use when a hypothesis/unknown can change:

- whether an action is legal;
- where it ends;
- whether the turn is safe;
- the post-turn resources when that difference reaches ranking;
- the identity or order of the best recommendation.

### `no_safe_solution`

Use only after proving candidate-set completeness under resolved mechanics. It is not a substitute for missing information.

### `confirmation_required`

Use when the complete best result depends only on one or more `single_source_supported` rules or a manually confirmed boundary cell. User confirmation may unlock the UI action instructions, but it does not relabel the result as mechanically verified.

### `solved`

Use only when all dependencies affecting legality, terminal outcome and ranking are authoritative and every critical visual field used is confirmed.

## Partial uncertainty

Unknown data that is irrelevant to the winning candidate does not automatically block:

- an unknown spell may be ignored when the winner uses other confirmed spells and no unknown action could outrank it;
- unknown progress indices allow per-turn race direction but not terminal win/loss;
- uncertain recharge does not block when race safety differs earlier in ranking;
- uncertain lower ranking keys do not block when an earlier key already establishes strict order.

This is evaluated by dependency reachability, not by a blanket “any unknown blocks everything” rule.
