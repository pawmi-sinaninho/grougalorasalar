from __future__ import annotations

import pytest

from grougal_solver.fight_state import (
    ACTION_BUDGET,
    new_fight_state,
    reconcile_round_start,
    resource_state,
    stage_transition,
)


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
