from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pytest

from grougal_solver.profiles import ProfileError, RuleAuthority, compile_profile
from grougal_solver.solver import ArenaSets, DeterministicSolver


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SPELLS = ("indecision", "reflection", "repulsion", "attraction")
EIGHT_DIRECTIONS = (
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
)


def _arena() -> ArenaSets:
    return ArenaSets(
        walkable=frozenset(
            (x, y)
            for x in range(-12, 13)
            for y in range(-12, 13)
        ),
        boundary=frozenset(),
        occluded=frozenset(),
        blocked=frozenset(),
    )


def _pillar(
    pillar_id: str,
    cell: tuple[int, int],
    spell_type: str = "indecision",
) -> dict:
    return {
        "id": pillar_id,
        "cell": {"x": cell[0], "y": cell[1]},
        "spellType": spell_type,
    }


def _actions_for(
    active_spell: str,
    pillars: Iterable[dict],
) -> list[dict]:
    solver = DeterministicSolver(PROJECT_ROOT)
    profile = compile_profile(
        PROJECT_ROOT,
        action_budget=12,
        fixture_mode=True,
    )
    spell_states = {
        spell: {
            "availability": "available" if spell == active_spell else "unavailable",
            "confirmed": True,
            "value": 4 if spell == active_spell else 0,
        }
        for spell in SPELLS
    }
    given = {"resources": {"spells": spell_states}}
    pillar_by_cell = {
        (pillar["cell"]["x"], pillar["cell"]["y"]): pillar
        for pillar in pillars
    }

    definite, conditional = solver._enumerate_actions(
        source=(0, 0),
        given=given,
        profile=profile,
        arena=_arena(),
        pillar_by_cell=pillar_by_cell,
        cast_counts={spell: 0 for spell in SPELLS},
        spell_values={spell: 4 if spell == active_spell else 0 for spell in SPELLS},
        budget=12,
        authority=RuleAuthority(solver.rule_statuses),
        fixture_mode=True,
    )

    assert conditional == []
    return definite


def _target_cells(actions: Iterable[dict]) -> set[tuple[int, int]]:
    return {
        (action["targetCell"]["x"], action["targetCell"]["y"])
        for action in actions
    }


def _destination(action: dict) -> tuple[int, int]:
    return action["destinationCell"]["x"], action["destinationCell"]["y"]


def test_rules_profile_encodes_verified_target_geometry() -> None:
    profile = compile_profile(
        PROJECT_ROOT,
        action_budget=12,
        fixture_mode=True,
    )

    indecision = profile["movement"]["indecision"]
    assert indecision["contactMetric"] == "orthogonal"
    assert indecision["destinationOccupancy"] == "invalid"

    reflection = profile["movement"]["reflection"]
    assert reflection["targetPillarType"] == "any_pillar"
    assert reflection["rangeMetric"] == "manhattan"
    assert reflection["minRange"] == reflection["maxRange"] == 2
    assert reflection["alignment"] == "cardinal_or_diagonal"

    repulsion = profile["movement"]["repulsion"]
    assert repulsion["targetPillarType"] == "any_pillar"
    assert repulsion["rangeMetric"] == "aligned_steps"
    assert repulsion["minRange"] == 1
    assert repulsion["maxRange"] == 2
    assert set(repulsion["allowedAlignments"]) == {"cardinal", "diagonal"}

    attraction = profile["movement"]["attraction"]
    assert attraction["targetPillarType"] == "any_pillar"
    assert attraction["minRange"] == 1
    assert attraction["maxRange"] == 6
    assert attraction["alignment"] == "cardinal"
    assert attraction["lineOfSight"] == "required_clear"


@pytest.mark.parametrize(
    ("override", "value"),
    (
        ("movement.indecision.contactMetric", "chebyshev"),
        ("movement.reflection.minRange", 1),
        ("movement.repulsion.maxRange", 3),
        ("movement.attraction.alignment", "cardinal_or_diagonal"),
        ("movement.attraction.lineOfSight", "ignored"),
    ),
)
def test_profile_rejects_spell_geometry_drift(override: str, value: object) -> None:
    with pytest.raises(ProfileError):
        compile_profile(PROJECT_ROOT, overrides={override: value}, fixture_mode=True)


def test_indecision_targets_only_four_adjacent_empty_cells() -> None:
    empty_board_actions = _actions_for("indecision", [])
    assert _target_cells(empty_board_actions) == {(-1, 0), (0, -1), (0, 1), (1, 0)}
    assert len(empty_board_actions) == 4

    actions = _actions_for(
        "indecision",
        [_pillar("P_BLOCK", (1, 0), "reflection")],
    )

    assert _target_cells(actions) == {(-1, 0), (0, -1), (0, 1)}
    assert all(action["targetKind"] == "cell" for action in actions)


def test_reflet_targets_exactly_the_eight_radius_two_pillar_cells() -> None:
    expected = {
        (x, y)
        for x in range(-2, 3)
        for y in range(-2, 3)
        if abs(x) + abs(y) == 2
    }
    pillars = [
        _pillar(f"P{index:02d}", cell, "attraction")
        for index, cell in enumerate(sorted(expected), start=1)
    ]

    actions = _actions_for("reflection", pillars)

    assert len(actions) == 8
    assert _target_cells(actions) == expected
    assert all(action["targetKind"] == "pillar" for action in actions)
    assert all(
        _destination(action)
        == (
            2 * action["targetCell"]["x"],
            2 * action["targetCell"]["y"],
        )
        for action in actions
    )


def test_reflet_rejects_wrong_range_and_non_aligned_pillars() -> None:
    pillars = [
        _pillar("P_NEAR", (1, 0), "attraction"),
        _pillar("P_FAR", (3, 0), "attraction"),
        _pillar("P_OFF_AXIS", (2, 1), "attraction"),
    ]

    assert _actions_for("reflection", pillars) == []


def test_rejet_targets_any_pillar_on_eight_rays_up_to_two_cells() -> None:
    expected = {
        (distance * dx, distance * dy)
        for dx, dy in EIGHT_DIRECTIONS
        for distance in (1, 2)
    }
    actions = [
        _actions_for(
            "repulsion",
            [_pillar(f"P{index:02d}", cell, "reflection")],
        )[0]
        for index, cell in enumerate(sorted(expected), start=1)
    ]

    assert len(actions) == 16
    assert _target_cells(actions) == expected
    assert all(action["targetKind"] == "pillar" for action in actions)


def test_rejet_rejects_radius_three_and_non_aligned_pillars() -> None:
    pillars = [
        _pillar("P_FAR", (3, 0), "reflection"),
        _pillar("P_OFF_AXIS", (2, 1), "reflection"),
    ]

    assert _actions_for("repulsion", pillars) == []


def test_attrait_targets_any_linear_pillar_from_one_to_six_cells() -> None:
    for dx, dy in ((-1, 0), (0, -1), (0, 1), (1, 0)):
        for distance in range(1, 7):
            target = (distance * dx, distance * dy)
            actions = _actions_for(
                "attraction",
                [_pillar(f"P{dx}_{dy}_{distance}", target, "reflection")],
            )

            assert len(actions) == 1
            assert _target_cells(actions) == {target}
            assert actions[0]["targetKind"] == "pillar"
            expected_steps = min(distance - 1, 3)
            assert _destination(actions[0]) == (expected_steps * dx, expected_steps * dy)


def test_attrait_rejects_diagonal_and_out_of_range_pillars() -> None:
    pillars = [
        _pillar("P_DIAGONAL", (6, 6), "reflection"),
        _pillar("P_TOO_FAR", (7, 0), "reflection"),
    ]

    assert _actions_for("attraction", pillars) == []


def test_attrait_rejects_target_behind_an_intermediate_pillar() -> None:
    actions = _actions_for(
        "attraction",
        [
            _pillar("P_BLOCKER", (4, 0), "indecision"),
            _pillar("P_TARGET", (6, 0), "reflection"),
        ],
    )

    assert {action["targetPillarId"] for action in actions} == {"P_BLOCKER"}
