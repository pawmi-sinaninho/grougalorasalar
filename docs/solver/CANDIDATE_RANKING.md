# CANDIDATE RANKING

The normative machine-readable policy is `data/solver/ranking-policy.v0.5.0.json`.

## Lexicographic key

Candidates are compared by these keys in order:

1. hard eligibility: at least one movement and no projected or direct black effect;
2. movement-cast count, ascending;
3. post-turn resource resilience;
4. safe progress: Crocoburio advance, then neutral;
5. verified local degree of the final cell;
6. canonical sequence key.

A later key may not compensate for a worse earlier key. A white collision is optional and cannot justify an additional cast when a shorter black-safe sequence exists.

## Resource resilience

Build one value per spell in fixed order. In numeric mode, cap known values at known maximum. In availability-only mode, map available to 1 and unavailable to 0. Sort the four values ascending and maximize the resulting vector lexicographically. This is max-min fairness: the most depleted spell is improved first.

If a value is unknown and the resource key is reached, ordering is unresolved and the result is blocked. If race safety already differs, the unknown resource key is irrelevant.

## Local degree

Count orthogonally adjacent cells classified `walkable_confirmed` or `walkable_observed`. Boundary and occluded cells contribute zero. This measures stable terrain escape options.

Pillar-based next-turn mobility is intentionally excluded because both pillar layout and glyph pattern change each turn.

## Final tie

The canonical sequence key is a deterministic technical tie-break only. It compares parsed typed action tuples, not raw display strings. It carries no tactical meaning.
