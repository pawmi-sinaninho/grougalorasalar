from __future__ import annotations

from grougal_solver.solver import ArenaSets, DeterministicSolver


def _arena() -> ArenaSets:
    return ArenaSets.from_given(
        {
            "walkable": [
                {"x": 0, "y": 0},
                {"x": -1, "y": 0},
                {"x": 1, "y": 0},
                {"x": 0, "y": -1},
                {"x": 0, "y": 1},
            ],
            "boundaryUnverified": [],
            "occludedUnknown": [],
            "permanentBlocked": [],
        }
    )


def _candidate(*, sequence: str, race: str, white: bool, next_state: dict[str, int]) -> dict:
    return {
        "raceOutcome": race,
        "finalCell": {"x": 0, "y": 0},
        "castCount": 1,
        "sequence": [sequence],
        "actions": [{"spell": "indecision"}],
        "whitePillarIds": ["P01"] if white else [],
        "rechargedSpells": ["attraction"] if white else [],
        "nextSpellState": next_state,
    }


def test_ranking_prefers_white_recharge_over_plain_safe_movement() -> None:
    solver = object.__new__(DeterministicSolver)
    plain_move = _candidate(
        sequence="aa_plain",
        race="neutral",
        white=False,
        next_state={"indecision": 0, "reflection": 1, "repulsion": 1, "attraction": 2},
    )
    recharge_move = _candidate(
        sequence="zz_recharge",
        race="crocoburio_advance",
        white=True,
        next_state={"indecision": 0, "reflection": 1, "repulsion": 1, "attraction": 3},
    )

    assert solver._ranking_key(recharge_move, _arena()) < solver._ranking_key(plain_move, _arena())


def test_ranking_keeps_shorter_safe_sequence_before_recharge() -> None:
    solver = object.__new__(DeterministicSolver)
    one_cast_plain = _candidate(
        sequence="aa_one_cast",
        race="neutral",
        white=False,
        next_state={"indecision": 0, "reflection": 1, "repulsion": 1, "attraction": 2},
    )
    two_cast_recharge = _candidate(
        sequence="zz_two_cast_recharge",
        race="crocoburio_advance",
        white=True,
        next_state={"indecision": 0, "reflection": 1, "repulsion": 1, "attraction": 3},
    )
    two_cast_recharge["castCount"] = 2
    two_cast_recharge["actions"] = [{"spell": "indecision"}, {"spell": "reflection"}]

    assert solver._ranking_key(one_cast_plain, _arena()) < solver._ranking_key(two_cast_recharge, _arena())
