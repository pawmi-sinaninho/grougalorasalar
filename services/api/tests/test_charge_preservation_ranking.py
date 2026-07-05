from __future__ import annotations

from grougal_solver.solver import ArenaSets, DeterministicSolver


def _candidate(*, spell: str, sequence: str) -> dict:
    return {
        "raceOutcome": "neutral",
        "finalCell": {"x": 0, "y": 0},
        "castCount": 1,
        "sequence": [sequence],
        "actions": [{"spell": spell}],
        "whitePillarIds": [],
        "rechargedSpells": [],
        "nextSpellState": {
            "indecision": 0,
            "reflection": 3,
            "repulsion": 2,
            "attraction": 1,
        },
    }


def test_ranking_prefers_abundant_spell_when_no_recharge_is_available() -> None:
    solver = object.__new__(DeterministicSolver)
    arena = ArenaSets.from_given(
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

    abundant_cast = _candidate(spell="reflection", sequence="zz_abundant")
    scarce_cast = _candidate(spell="attraction", sequence="aa_scarce")

    assert solver._ranking_key(abundant_cast, arena) < solver._ranking_key(scarce_cast, arena)


def test_ranking_scarce_cast_tiebreaker_does_not_apply_to_white_recharge() -> None:
    solver = object.__new__(DeterministicSolver)
    arena = ArenaSets.from_given(
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

    # With a matching white hit, recharge outcome remains the primary signal;
    # the no-recharge scarcity penalty is disabled.
    abundant_cast = _candidate(spell="reflection", sequence="zz_abundant")
    scarce_cast = _candidate(spell="attraction", sequence="aa_scarce")
    abundant_cast["whitePillarIds"] = ["P01"]
    abundant_cast["rechargedSpells"] = ["reflection"]
    scarce_cast["whitePillarIds"] = ["P02"]
    scarce_cast["rechargedSpells"] = ["attraction"]

    assert solver._ranking_key(scarce_cast, arena) < solver._ranking_key(abundant_cast, arena)
