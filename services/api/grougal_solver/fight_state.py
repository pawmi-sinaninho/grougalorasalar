from __future__ import annotations

from typing import Any


SPELLS = ("indecision", "reflection", "repulsion", "attraction")
INITIAL_CHARGES = 2
MAX_CHARGES = 4
ACTION_BUDGET = 12


def new_fight_state() -> dict[str, Any]:
    return {
        "schemaVersion": "1.0.0",
        "round": 1,
        "charges": {spell: INITIAL_CHARGES for spell in SPELLS},
        "syncStatus": "awaiting_first_screenshot",
        "verifiedStartCell": None,
        "pendingTransition": None,
    }


def resource_state(charges: dict[str, int]) -> dict[str, Any]:
    normalised = normalise_charges(charges)
    return {
        "actionBudget": ACTION_BUDGET,
        "spells": {
            spell: {
                "availability": "available" if normalised[spell] > 0 else "unavailable",
                "value": normalised[spell],
                "confirmed": True,
            }
            for spell in SPELLS
        },
    }


def stage_transition(fight: dict[str, Any], recommendation: dict[str, Any]) -> dict[str, Any]:
    expected = recommendation.get("expected") or {}
    final_cell = expected.get("finalCell")
    next_spell_state = expected.get("nextSpellState")
    if not final_cell or not isinstance(next_spell_state, dict):
        return fight
    fight["pendingTransition"] = {
        "fromRound": int(fight["round"]),
        "expectedFinalCell": {"x": int(final_cell["x"]), "y": int(final_cell["y"])},
        "nextCharges": normalise_charges(next_spell_state),
        "raceOutcome": expected.get("raceOutcome", "unknown"),
        "whitePillarIds": list(expected.get("whitePillarIds") or []),
    }
    fight["syncStatus"] = "awaiting_next_round_screenshot"
    return fight


def reconcile_round_start(fight: dict[str, Any], detected_player: dict[str, int] | None) -> dict[str, Any]:
    if detected_player is None:
        fight["syncStatus"] = "player_unresolved"
        return fight

    detected = {"x": int(detected_player["x"]), "y": int(detected_player["y"])}
    pending = fight.get("pendingTransition")
    if pending is None:
        fight["verifiedStartCell"] = detected
        fight["syncStatus"] = "synchronised"
        return fight

    if detected != pending["expectedFinalCell"]:
        fight["syncStatus"] = "player_mismatch"
        fight["detectedStartCell"] = detected
        return fight

    fight["round"] = int(fight["round"]) + 1
    fight["charges"] = normalise_charges(pending["nextCharges"])
    fight["verifiedStartCell"] = detected
    fight["pendingTransition"] = None
    fight.pop("detectedStartCell", None)
    fight["syncStatus"] = "synchronised"
    return fight


def normalise_charges(values: dict[str, Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    for spell in SPELLS:
        value = values.get(spell)
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"Missing numeric charge value for {spell}")
        if not 0 <= value <= MAX_CHARGES:
            raise ValueError(f"Charge value outside 0..{MAX_CHARGES} for {spell}")
        result[spell] = value
    return result
