from __future__ import annotations

import pytest

from grougal_solver.fight_state import (
    ACTION_BUDGET,
    new_fight_state,
    reconcile_round_start,
    resource_state,
    stage_transition,
)
from grougal_solver.solver import resolve_next_charges


SPELLS = ("indecision", "reflection", "repulsion", "attraction")


def test_new_fight_starts_round_one_with_twelve_ap_and_two_charges() -> None:
    fight = new_fight_state()
    assert fight["round"] == 1
    assert set(fight["charges"].values()) == {2}
    resources = resource_state(fight["charges"])
    assert resources["actionBudget"] == ACTION_BUDGET == 12
    assert all(item["value"] == 2 and item["confirmed"] for item in resources["spells"].values())


def test_next_round_is_committed_only_when_the_new_screenshot_matches_expected_player() -> None:
    fight = reconcile_round_start(new_fight_state(), {"x": 0, "y": 0})
    recommendation = {
        "expected": {
            "finalCell": {"x": -2, "y": 1},
            "nextSpellState": {
                "indecision": 1,
                "reflection": 2,
                "repulsion": 2,
                "attraction": 1,
            },
            "raceOutcome": "crocoburio_advance",
            "whitePillarIds": [],
        }
    }
    stage_transition(fight, recommendation)
    reconcile_round_start(fight, {"x": -2, "y": 1})
    assert fight["round"] == 2
    assert fight["charges"] == {
        "indecision": 1,
        "reflection": 2,
        "repulsion": 2,
        "attraction": 1,
    }
    assert fight["pendingTransition"] is None
    assert fight["syncStatus"] == "synchronised"


def test_player_mismatch_never_silently_consumes_pending_transition() -> None:
    fight = new_fight_state()
    stage_transition(
        fight,
        {
            "expected": {
                "finalCell": {"x": 1, "y": 0},
                "nextSpellState": {
                    "indecision": 1,
                    "reflection": 3,
                    "repulsion": 2,
                    "attraction": 2,
                },
            }
        },
    )
    reconcile_round_start(fight, {"x": 0, "y": 1})
    assert fight["round"] == 1
    assert set(fight["charges"].values()) == {2}
    assert fight["pendingTransition"] is not None
    assert fight["syncStatus"] == "player_mismatch"


def test_observed_round_eight_to_nine_transition_recharges_yellow_after_red_cast() -> None:
    fight = new_fight_state()
    fight["round"] = 8
    fight["charges"] = {
        "indecision": 2,
        "reflection": 3,
        "repulsion": 2,
        "attraction": 2,
    }
    stage_transition(
        fight,
        {
            "expected": {
                "finalCell": {"x": 1, "y": 3},
                "nextSpellState": {
                    "indecision": 2,
                    "reflection": 3,
                    "repulsion": 3,
                    "attraction": 1,
                },
                "whitePillarIds": ["yellow-observed-round-08"],
            }
        },
    )
    reconcile_round_start(fight, {"x": 1, "y": 3})
    assert fight["round"] == 9
    assert fight["charges"] == {
        "indecision": 2,
        "reflection": 3,
        "repulsion": 3,
        "attraction": 1,
    }


def test_invalid_or_partial_charge_state_is_rejected() -> None:
    with pytest.raises(ValueError):
        resource_state({"indecision": 2})


def test_charge_formula_is_bounded_and_exact_through_fourteen_rounds() -> None:
    """Model-check every reachable one-spell transition for a 14-round fight."""
    reachable = {2}
    seen: set[int] = set()
    for _round in range(1, 15):
        next_reachable: set[int] = set()
        for current in reachable:
            for casts in range(current + 1):
                for white_hits in range(5):
                    expected = min(4, current - casts + white_hits)
                    actual = resolve_next_charges(current, casts, white_hits)
                    assert actual == expected
                    assert 0 <= actual <= 4
                    next_reachable.add(actual)
                    seen.add(actual)
        reachable = next_reachable
    assert seen == {0, 1, 2, 3, 4}


def test_four_spell_fight_state_commits_once_per_round_until_round_fourteen() -> None:
    """Exercise staging, confirmation and anti-double-apply across all 14 rounds."""
    fight = reconcile_round_start(new_fight_state(), {"x": 0, "y": 0})
    visited_values = set(fight["charges"].values())

    for round_number in range(1, 14):
        current = dict(fight["charges"])
        next_charges: dict[str, int] = {}
        for spell_index, spell in enumerate(SPELLS):
            casts = min(current[spell], (round_number + spell_index) % 3)
            white_hits = (round_number * (spell_index + 1)) % 4
            next_charges[spell] = min(4, current[spell] - casts + white_hits)
            assert resolve_next_charges(current[spell], casts, white_hits) == next_charges[spell]

        final_cell = {"x": round_number, "y": -round_number}
        stage_transition(
            fight,
            {
                "expected": {
                    "finalCell": final_cell,
                    "nextSpellState": next_charges,
                    "raceOutcome": "crocoburio_advance",
                    "whitePillarIds": [],
                }
            },
        )
        assert fight["round"] == round_number
        assert fight["charges"] == current

        reconcile_round_start(fight, final_cell)
        assert fight["round"] == round_number + 1
        assert fight["charges"] == next_charges
        assert fight["pendingTransition"] is None

        # Re-reading the same round-start screenshot cannot apply the forecast twice.
        reconcile_round_start(fight, final_cell)
        assert fight["round"] == round_number + 1
        assert fight["charges"] == next_charges
        visited_values.update(next_charges.values())

    assert fight["round"] == 14
    assert {0, 4}.issubset(visited_values)
