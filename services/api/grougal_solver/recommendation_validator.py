from __future__ import annotations

from typing import Any

SPELLS = ("indecision", "reflection", "repulsion", "attraction")
PILLAR_SPELLS = {"reflection", "repulsion", "attraction"}
MAX_CHARGE = 4
MIN_TARGET_CONFIDENCE = 0.90
MAX_TARGET_SNAP_RESIDUAL = 0.15


def _cell_tuple(cell: Any) -> tuple[int, int] | None:
    if not isinstance(cell, dict):
        return None
    x = cell.get("x")
    y = cell.get("y")
    if not isinstance(x, int) or not isinstance(y, int):
        return None
    return x, y


def _sign(value: int) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def _classify(cell: tuple[int, int], arena: dict[str, Any]) -> str:
    walkable = {_cell_tuple(item) for item in arena.get("walkable", [])}
    boundary = {_cell_tuple(item) for item in arena.get("boundaryUnverified", [])}
    occluded = {_cell_tuple(item) for item in arena.get("occludedUnknown", [])}
    blocked = {_cell_tuple(item) for item in arena.get("permanentBlocked", [])}
    if cell in walkable:
        return "walkable"
    if cell in boundary:
        return "boundary"
    if cell in occluded:
        return "occluded"
    if cell in blocked:
        return "blocked"
    return "outside"


def _is_line_or_diagonal(dx: int, dy: int) -> bool:
    return (dx == 0 and dy != 0) or (dy == 0 and dx != 0) or abs(dx) == abs(dy)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _target_pillar(action: dict[str, Any], pillars_by_id: dict[str, dict[str, Any]], pillars_by_cell: dict[tuple[int, int], dict[str, Any]]) -> dict[str, Any] | None:
    target_cell = _cell_tuple(action.get("targetCell"))
    pillar_id = action.get("targetPillarId")
    if isinstance(pillar_id, str):
        pillar = pillars_by_id.get(pillar_id)
        if pillar is None:
            return None
        if target_cell is not None and _cell_tuple(pillar.get("cell")) != target_cell:
            return None
        return pillar
    if target_cell is not None:
        return pillars_by_cell.get(target_cell)
    return None


def validate_recommendation(turn_state: dict[str, Any] | None, recommendation: dict[str, Any] | None) -> dict[str, Any] | None:
    """Fail-safe post-solver validation.

    This does not run image recognition and does not search for better moves.
    It only blocks already-selected recommendations that violate hard rules or
    depend on visibly weak target pillars.
    """
    if not isinstance(turn_state, dict) or not isinstance(recommendation, dict):
        return recommendation
    if recommendation.get("status") not in {"solved", "provisional_solution"}:
        return recommendation

    actions = recommendation.get("actions") or []
    if not actions:
        return recommendation

    issues: list[str] = []
    arena = turn_state.get("arena") or {}
    pillars = [item for item in turn_state.get("pillars", []) if isinstance(item, dict)]
    pillars_by_id = {item.get("id"): item for item in pillars if isinstance(item.get("id"), str)}
    pillars_by_cell = {cell: item for item in pillars for cell in [_cell_tuple(item.get("cell"))] if cell is not None}
    occupied = set(pillars_by_cell)

    current = _cell_tuple((turn_state.get("player") or {}).get("current"))
    if current is None:
        issues.append("VALIDATOR-NO-PLAYER")

    spell_values: dict[str, int | None] = {}
    for spell in SPELLS:
        raw = ((turn_state.get("resources") or {}).get("spells") or {}).get(spell, {}).get("value")
        spell_values[spell] = raw if isinstance(raw, int) else None

    for index, action in enumerate(actions, start=1):
        if current is None:
            break
        spell = action.get("spell")
        source = _cell_tuple(action.get("sourceCell"))
        target = _cell_tuple(action.get("targetCell"))
        destination = _cell_tuple(action.get("destinationCell"))

        if spell not in SPELLS:
            issues.append(f"VALIDATOR-ACTION-{index}-UNKNOWN-SPELL")
            continue
        if source != current:
            issues.append(f"VALIDATOR-ACTION-{index}-SOURCE-MISMATCH")
        if target is None:
            issues.append(f"VALIDATOR-ACTION-{index}-MISSING-TARGET")
        if destination is None:
            issues.append(f"VALIDATOR-ACTION-{index}-MISSING-DESTINATION")
            continue

        value = spell_values.get(spell)
        if value is not None:
            if value <= 0:
                issues.append(f"VALIDATOR-ACTION-{index}-NO-CHARGE")
            spell_values[spell] = value - 1

        if _classify(destination, arena) != "walkable":
            issues.append(f"VALIDATOR-ACTION-{index}-DESTINATION-NOT-WALKABLE")
        if destination in occupied:
            issues.append(f"VALIDATOR-ACTION-{index}-DESTINATION-OCCUPIED")

        if spell == "indecision" and target is not None:
            dx = target[0] - current[0]
            dy = target[1] - current[1]
            if abs(dx) + abs(dy) != 1:
                issues.append(f"VALIDATOR-ACTION-{index}-INDECISION-NOT-ORTHOGONAL")
            if destination != target:
                issues.append(f"VALIDATOR-ACTION-{index}-INDECISION-DESTINATION-MISMATCH")
            if target in occupied:
                issues.append(f"VALIDATOR-ACTION-{index}-INDECISION-TARGET-OCCUPIED")
            if _classify(target, arena) != "walkable":
                issues.append(f"VALIDATOR-ACTION-{index}-INDECISION-TARGET-NOT-WALKABLE")

        if spell in PILLAR_SPELLS and target is not None:
            pillar = _target_pillar(action, pillars_by_id, pillars_by_cell)
            if pillar is None:
                issues.append(f"VALIDATOR-ACTION-{index}-TARGET-PILLAR-MISSING")
            else:
                confidence = pillar.get("confidence")
                if isinstance(confidence, (int, float)) and float(confidence) < MIN_TARGET_CONFIDENCE:
                    issues.append(f"VALIDATOR-ACTION-{index}-TARGET-PILLAR-LOW-CONFIDENCE")
                snap_residual = pillar.get("snapResidualCell")
                if isinstance(snap_residual, (int, float)) and float(snap_residual) > MAX_TARGET_SNAP_RESIDUAL:
                    issues.append(f"VALIDATOR-ACTION-{index}-TARGET-PILLAR-WEAK-SNAP")

            dx = target[0] - current[0]
            dy = target[1] - current[1]
            if spell == "reflection":
                # Live-confirmed rule: Reflet is only castable on a diagonal
                # pillar exactly one cell from the player.
                if not (abs(dx) == 1 and abs(dy) == 1):
                    issues.append(f"VALIDATOR-ACTION-{index}-REFLECTION-BAD-GEOMETRY")
                expected = (current[0] + 2 * dx, current[1] + 2 * dy)
                if destination != expected:
                    issues.append(f"VALIDATOR-ACTION-{index}-REFLECTION-DESTINATION-MISMATCH")
            elif spell == "repulsion":
                if not _is_line_or_diagonal(dx, dy) or max(abs(dx), abs(dy)) not in {1, 2}:
                    issues.append(f"VALIDATOR-ACTION-{index}-REPULSION-BAD-GEOMETRY")
                away = (_sign(current[0] - target[0]), _sign(current[1] - target[1]))
                move = (_sign(destination[0] - current[0]), _sign(destination[1] - current[1]))
                if move != away and destination != current:
                    issues.append(f"VALIDATOR-ACTION-{index}-REPULSION-NOT-AWAY-FROM-PILLAR")
            elif spell == "attraction":
                distance = max(abs(dx), abs(dy))
                if not ((dx == 0) ^ (dy == 0)) or distance < 1 or distance > 6:
                    issues.append(f"VALIDATOR-ACTION-{index}-ATTRACTION-BAD-GEOMETRY")
                toward = (_sign(target[0] - current[0]), _sign(target[1] - current[1]))
                move = (_sign(destination[0] - current[0]), _sign(destination[1] - current[1]))
                if move != toward and destination != current:
                    issues.append(f"VALIDATOR-ACTION-{index}-ATTRACTION-NOT-TOWARD-PILLAR")
                if destination == target:
                    issues.append(f"VALIDATOR-ACTION-{index}-ATTRACTION-STOPS-ON-PILLAR")

        current = destination

    expected_final = _cell_tuple((recommendation.get("expected") or {}).get("finalCell"))
    if expected_final is not None and current is not None and expected_final != current:
        issues.append("VALIDATOR-FINAL-CELL-MISMATCH")

    next_spell_state = (recommendation.get("expected") or {}).get("nextSpellState") or {}
    if isinstance(next_spell_state, dict):
        for spell, value in next_spell_state.items():
            if spell in SPELLS and isinstance(value, int) and (value < 0 or value > MAX_CHARGE):
                issues.append("VALIDATOR-NEXT-CHARGE-OUT-OF-RANGE")

    if not issues:
        return recommendation

    blocked = dict(recommendation)
    expected = dict(blocked.get("expected") or {})
    expected["finalCell"] = None
    blocked["expected"] = expected
    blocked["actions"] = []
    blocked["status"] = "blocked_unverified_rule"
    blocked["solverStatus"] = "blocked_by_recommendation_validator"
    blocked["statusReasonCodes"] = _unique(list(blocked.get("statusReasonCodes") or []) + ["S-VALIDATION-FAILED"] + issues)
    blocked["warnings"] = _unique(list(blocked.get("warnings") or []) + issues)
    blocked["confidence"] = {"visual": 0.0, "mechanical": 0.0, "overall": 0.0}
    return blocked
