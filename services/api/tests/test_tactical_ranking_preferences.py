from __future__ import annotations

from pathlib import Path

from grougal_solver.solver import ArenaSets, DeterministicSolver

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _solver() -> DeterministicSolver:
    return DeterministicSolver(PROJECT_ROOT)


def _candidate(
    *,
    final_cell: tuple[int, int] = (0, 0),
    cast_count: int = 1,
    charges: dict[str, int] | None = None,
) -> dict:
    charges = charges or {
        "indecision": 1,
        "reflection": 1,
        "repulsion": 1,
        "attraction": 1,
    }
    return {
        "raceOutcome": "neutral",
        "finalCell": {"x": final_cell[0], "y": final_cell[1]},
        "nextSpellState": charges,
        "castCount": cast_count,
        "sequence": [f"seq-{cast_count}-{final_cell[0]}-{final_cell[1]}"],
    }


def test_ranking_prefers_not_emptying_a_spell_between_equally_short_sequences() -> None:
    solver = _solver()
    arena = ArenaSets(frozenset(), frozenset(), frozenset(), frozenset())

    one_cast_but_empty = _candidate(
        cast_count=1,
        charges={
            "indecision": 0,
            "reflection": 2,
            "repulsion": 2,
            "attraction": 2,
        },
    )
    one_cast_balanced = _candidate(
        cast_count=1,
        charges={
            "indecision": 1,
            "reflection": 1,
            "repulsion": 2,
            "attraction": 2,
        },
    )

    assert solver._ranking_key(one_cast_balanced, arena) < solver._ranking_key(one_cast_but_empty, arena)


def test_ranking_prefers_interior_cell_when_resources_are_equal() -> None:
    solver = _solver()
    walkable = frozenset({
        (0, 0), (-1, 0), (1, 0), (0, -1), (0, 1),
        (13, 0), (12, 0), (13, -1), (13, 1),
    })
    arena = ArenaSets(walkable, frozenset(), frozenset(), frozenset())

    centre = _candidate(final_cell=(0, 0), cast_count=1)
    exposed_edge = _candidate(final_cell=(13, 0), cast_count=1)

    assert solver._ranking_key(centre, arena) < solver._ranking_key(exposed_edge, arena)
