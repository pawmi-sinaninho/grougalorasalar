# PROPERTY-TEST SPECIFICATION

## Geometry properties

1. Reflet involution: reflecting destination through the same pillar returns the original source.
2. Rejet direction: for a valid aligned target, destination-player vector equals `distance*u` away from the pillar.
3. Attrait direction: for non-short-range valid targets, destination-player vector equals `distance*u` toward the pillar.
4. Translation invariance: translating source, target, pillars and arena by the same vector translates every destination and projected cell identically.
5. Canonical ordering is independent of input pillar-array order.

## Projection properties

6. Projection is translation invariant.
7. Black/white collisions depend only on logical cell equality, never pixel distance.
8. Duplicate offsets are rejected.
9. Black and white physical source-cell sets may not overlap.
10. Pillar IDs in collision lists are unique and sorted.

## Resource properties

11. Remaining action budget never increases during a sequence.
12. Numeric charge never becomes negative.
13. Availability-only definite paths use each spell at most once unless R-048 is resolved otherwise.
14. Recharge is applied only at end-turn resolution.
15. With stacking disabled, a spell receives at most one matching-pillar recharge unit.
16. With known max charge, post-recharge values do not exceed max.

## Search and ranking properties

17. Every definite terminal sequence is reproducible from definite edges only.
18. Deduplication does not change the set of reachable node states.
19. Reordering input pillars does not change ordered recommendations.
20. Re-running the same request yields byte-equivalent canonical action signatures and ranking keys.
21. A zero-cast or black-adverse candidate is never recommendable.
22. Among black-safe candidates, fewer casts always outrank more casts; canonical sequence is consulted only after keys 1–5 tie.
23. Unknown lower keys do not block when a higher key establishes strict order.
24. `no_safe_solution` is impossible while a conditional safe candidate exists.

## Status properties

25. Any structural contradiction yields `invalid_state` regardless of tactical candidates.
26. A blocking rule dependency that can change the winner yields `blocked_unverified_rule`.
27. Single-source-only dependencies yield `confirmation_required`, not `solved`.
28. Unknown progress indices do not alter per-turn race direction.
29. User confirmation does not promote rule-catalog authority.
30. A specification-test profile cannot be loaded in production mode.
