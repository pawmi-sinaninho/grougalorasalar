from __future__ import annotations

from grougal_solver.editor import CommandRejected, apply_command
from grougal_solver.editor import validate_turn_state
from grougal_solver.recognition import blank_given
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def command(kind: str, payload: dict, version: int = 0) -> dict:
    return {
        "schemaVersion": "0.6.0",
        "commandId": f"cmd_{kind}",
        "analysisId": "ana_test",
        "expectedStateVersion": version,
        "type": kind,
        "payload": payload,
        "issuedAt": "2026-06-28T12:00:00Z",
    }


def test_pillar_ids_survive_move_and_reclassification() -> None:
    document = {"turnState": blank_given(PROJECT_ROOT), "history": [], "future": [], "audit": [], "recommendation": {"status": "solved"}}
    document = apply_command(document, command("add_pillar", {"id": "P1", "cell": {"x": 0, "y": 0}, "spellType": "reflection"}))
    document = apply_command(document, command("move_pillar", {"id": "P1", "cell": {"x": 1, "y": 0}}))
    document = apply_command(document, command("set_pillar_type", {"id": "P1", "spellType": "repulsion"}))
    assert document["turnState"]["pillars"] == [{"id": "P1", "cell": {"x": 1, "y": 0}, "spellType": "repulsion"}]
    assert document["recommendation"] is None
    assert document["recommendationInvalidated"] is True


def test_duplicate_pillar_is_rejected_atomically() -> None:
    document = {"turnState": blank_given(PROJECT_ROOT), "history": [], "future": [], "audit": []}
    document = apply_command(document, command("add_pillar", {"id": "P1", "cell": {"x": 0, "y": 0}, "spellType": "reflection"}))
    try:
        apply_command(document, command("add_pillar", {"id": "P2", "cell": {"x": 0, "y": 0}, "spellType": "repulsion"}))
    except CommandRejected as exc:
        assert exc.code == "API-STATE-DUPLICATE-PILLAR"
    else:
        raise AssertionError("duplicate pillar was accepted")


def test_detection_acceptance_does_not_silently_confirm_pillar_completeness() -> None:
    document = {"turnState": blank_given(PROJECT_ROOT), "history": [], "future": [], "audit": []}
    document = apply_command(document, command("accept_detection", {}))
    assert document["turnState"]["flags"]["criticalFieldsConfirmed"] is True
    assert document["turnState"]["flags"]["pillarSetComplete"] is False


def test_unknown_spell_state_remains_a_solver_blocker() -> None:
    state = blank_given(PROJECT_ROOT)
    state["flags"].update({"criticalFieldsConfirmed": True, "pillarSetComplete": True, "anchorConfirmed": True})
    state["resources"]["actionBudget"] = 3
    for spell in state["resources"]["spells"].values():
        spell.update({"availability": "unknown", "confirmed": True})
    assert "S-BLOCK-SPELL-STATE" in validate_turn_state(state)
