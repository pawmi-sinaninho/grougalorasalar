from __future__ import annotations

from typing import Any

from .util import SPELLS, deep_copy


class CommandRejected(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def apply_command(document: dict[str, Any], command: dict[str, Any]) -> dict[str, Any]:
    command_type = command["type"]
    payload = command.get("payload", {})
    state = deep_copy(document["turnState"])
    history = list(document.get("history", []))
    future = list(document.get("future", []))

    if command_type == "undo":
        if not history:
            raise CommandRejected("API-STATE-NOTHING-TO-UNDO", "No command can be undone")
        previous = history.pop()
        future.append(deep_copy(state))
        document["turnState"] = previous
        document["history"] = history
        document["future"] = future
        return document
    if command_type == "redo":
        if not future:
            raise CommandRejected("API-STATE-NOTHING-TO-REDO", "No command can be redone")
        next_state = future.pop()
        history.append(deep_copy(state))
        document["turnState"] = next_state
        document["history"] = history
        document["future"] = future
        return document

    history.append(deep_copy(state))
    future = []

    if command_type == "accept_detection":
        state["flags"]["criticalFieldsConfirmed"] = True
    elif command_type == "set_player_cell":
        state["player"]["current"] = _cell(payload.get("cell"))
    elif command_type == "add_pillar":
        pillar = {
            "id": str(payload.get("id") or f"P{len(state['pillars']) + 1:02d}"),
            "cell": _cell(payload.get("cell")),
            "spellType": _spell(payload.get("spellType")),
        }
        _assert_unique_pillar(state, pillar["cell"], None)
        state["pillars"].append(pillar)
    elif command_type == "move_pillar":
        pillar = _pillar(state, payload.get("id"))
        new_cell = _cell(payload.get("cell"))
        _assert_unique_pillar(state, new_cell, pillar["id"])
        pillar["cell"] = new_cell
    elif command_type == "set_pillar_type":
        _pillar(state, payload.get("id"))["spellType"] = _spell(payload.get("spellType"))
    elif command_type == "delete_pillar":
        pillar_id = str(payload.get("id"))
        before = len(state["pillars"])
        state["pillars"] = [item for item in state["pillars"] if item["id"] != pillar_id]
        if len(state["pillars"]) == before:
            raise CommandRejected("API-STATE-PILLAR-NOT-FOUND", "Pillar does not exist")
    elif command_type == "set_pillar_set_complete":
        state["flags"]["pillarSetComplete"] = bool(payload.get("complete"))
    elif command_type == "paint_glyph_cell":
        colour = payload.get("colour")
        if colour not in {"black", "white"}:
            raise CommandRejected("API-CONTRACT-GLYPH-COLOUR", "Glyph colour must be black or white")
        offset = _offset(payload.get("offset"))
        own = state["glyphs"][f"{colour}Offsets"]
        other = state["glyphs"]["whiteOffsets" if colour == "black" else "blackOffsets"]
        own[:] = [item for item in own if item != offset] + [offset]
        other[:] = [item for item in other if item != offset]
    elif command_type == "erase_glyph_cell":
        offset = _offset(payload.get("offset"))
        for key in ("blackOffsets", "whiteOffsets"):
            state["glyphs"][key] = [item for item in state["glyphs"][key] if item != offset]
    elif command_type == "set_projection_anchor_confirmation":
        state["flags"]["anchorConfirmed"] = bool(payload.get("confirmed"))
    elif command_type == "set_action_budget":
        value = payload.get("value")
        if not isinstance(value, int) or value < 0 or value > 12:
            raise CommandRejected("API-CONTRACT-ACTION-BUDGET", "Action budget must be an integer from 0 to 12")
        state["resources"]["actionBudget"] = value
    elif command_type == "set_spell_state":
        spell = _spell(payload.get("spell"))
        availability = payload.get("availability")
        if availability not in {"available", "unavailable", "unknown"}:
            raise CommandRejected("API-CONTRACT-SPELL-STATE", "Invalid spell availability")
        value = payload.get("value")
        if value is not None and (not isinstance(value, int) or value < 0):
            raise CommandRejected("API-CONTRACT-SPELL-VALUE", "Spell value must be null or a non-negative integer")
        state["resources"]["spells"][spell] = {
            "availability": availability,
            "value": value,
            "confirmed": bool(payload.get("confirmed", True)),
        }
    elif command_type == "set_progress":
        runner = payload.get("runner")
        if runner not in {"dragon", "crocoburio"}:
            raise CommandRejected("API-CONTRACT-RUNNER", "Invalid runner")
        value = payload.get("value")
        if value is not None and (not isinstance(value, int) or value < 0):
            raise CommandRejected("API-CONTRACT-PROGRESS", "Progress must be null or non-negative")
        state.setdefault("progress", {})[runner] = value
    elif command_type in {"set_registration_anchors", "resolve_conflict"}:
        # Stored as explicit review metadata; registration remains manual.
        document.setdefault("reviewMetadata", {})[command_type] = payload
    else:
        raise CommandRejected("API-CONTRACT-COMMAND", f"Unsupported command: {command_type}")

    document["turnState"] = state
    document["history"] = history[-100:]
    document["future"] = future
    document["audit"] = list(document.get("audit", [])) + [
        {
            "commandId": command["commandId"],
            "type": command_type,
            "payload": payload,
            "issuedAt": command["issuedAt"],
        }
    ]
    document["recommendation"] = None
    document["recommendationInvalidated"] = True
    return document


def validate_turn_state(state: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if not state["flags"].get("criticalFieldsConfirmed"):
        reasons.append("MODEL-001")
    if not state["flags"].get("pillarSetComplete"):
        reasons.append("VISION-PILLAR-SET-INCOMPLETE")
    if not state["flags"].get("anchorConfirmed"):
        reasons.append("S-BLOCK-ANCHOR")
    if state["resources"].get("actionBudget") is None:
        reasons.append("S-BLOCK-ACTION-BUDGET")
    if any(
        not state["resources"]["spells"][spell].get("confirmed")
        or state["resources"]["spells"][spell].get("availability") == "unknown"
        for spell in SPELLS
    ):
        reasons.append("S-BLOCK-SPELL-STATE")
    return reasons


def _cell(value: Any) -> dict[str, int]:
    if not isinstance(value, dict) or not isinstance(value.get("x"), int) or not isinstance(value.get("y"), int):
        raise CommandRejected("API-CONTRACT-CELL", "Cell requires integer x and y")
    return {"x": value["x"], "y": value["y"]}


def _offset(value: Any) -> dict[str, int]:
    if not isinstance(value, dict) or not isinstance(value.get("dx"), int) or not isinstance(value.get("dy"), int):
        raise CommandRejected("API-CONTRACT-OFFSET", "Offset requires integer dx and dy")
    return {"dx": value["dx"], "dy": value["dy"]}


def _spell(value: Any) -> str:
    if value not in SPELLS:
        raise CommandRejected("API-CONTRACT-SPELL", "Unknown spell")
    return str(value)


def _pillar(state: dict[str, Any], pillar_id: Any) -> dict[str, Any]:
    for pillar in state["pillars"]:
        if pillar["id"] == pillar_id:
            return pillar
    raise CommandRejected("API-STATE-PILLAR-NOT-FOUND", "Pillar does not exist")


def _assert_unique_pillar(state: dict[str, Any], cell: dict[str, int], ignored_id: str | None) -> None:
    for pillar in state["pillars"]:
        if pillar["id"] != ignored_id and pillar["cell"] == cell:
            raise CommandRejected("API-STATE-DUPLICATE-PILLAR", "Another pillar already occupies this cell")
