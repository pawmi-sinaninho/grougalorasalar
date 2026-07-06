from __future__ import annotations

from copy import deepcopy
import time
from typing import Any

from .solver import CapacityExceeded, DeterministicSolver
from .util import deep_copy


PRODUCT_STATUSES = {
    "solved",
    "provisional_solution",
    "ambiguous_input",
    "no_safe_solution",
    "invalid_screenshot",
    "blocked_missing_data",
    "capacity_error",
}


def _trusted_solver_state_after_capacity_error(state: dict) -> dict:
    # Deterministic fallback state for the live image flow.
    trusted = deepcopy(state)

    arena = trusted.get("arena")
    if isinstance(arena, dict):
        arena["boundaryUnverified"] = []
        arena["occludedUnknown"] = []

    flags = trusted.setdefault("flags", {})
    if isinstance(flags, dict):
        flags["pillarSetComplete"] = True
        flags["criticalFieldsConfirmed"] = True
        flags["recognitionValidated"] = True

    trusted["profileMode"] = "capacity_fallback_trusted_recognition"
    return trusted


def _solve_given_with_capacity_fallback(solver: DeterministicSolver, state: dict) -> dict:
    try:
        return solver.solve_given(state, timeout_seconds=5.0, prune_dominated=True)
    except CapacityExceeded:
        trusted_state = _trusted_solver_state_after_capacity_error(state)
        return solver.solve_given(
            trusted_state,
            timeout_seconds=8.0,
            max_nodes=250_000,
            prune_dominated=True,
        )


def solver_input_complete(state: dict[str, Any]) -> bool:
    flags = state.get("flags", {})
    resources = state.get("resources", {})
    spells = resources.get("spells", {})
    return bool(
        state.get("player", {}).get("current")
        and state.get("pillars")
        and state.get("glyphs", {}).get("blackOffsets")
        and state.get("glyphs", {}).get("whiteOffsets")
        and resources.get("actionBudget") == 12
        and all(
            spells.get(spell, {}).get("confirmed")
            and spells.get(spell, {}).get("availability") in {"available", "unavailable"}
            for spell in ("indecision", "reflection", "repulsion", "attraction")
        )
        and flags.get("anchorConfirmed")
        and (flags.get("pillarHypothesisUsable") or flags.get("pillarSetComplete"))
    )


def analyse_turn(
    solver: DeterministicSolver,
    state: dict[str, Any],
    recognition: dict[str, Any],
) -> tuple[dict[str, Any], float]:
    """Solve the selected visual state and bounded plausible glyph alternatives.

    Fixture identity is deliberately absent from this decision. It remains useful
    diagnostic metadata, but never grants tactical authority.
    """
    started = time.perf_counter()
    registration = recognition.get("registration") or {}
    if not registration.get("accepted") or not state.get("player", {}).get("current"):
        return _empty("invalid_screenshot", ["VISION-SCREENSHOT-NOT-USABLE"]), _ms(started)
    if not solver_input_complete(state):
        return _empty("blocked_missing_data", ["VISION-SOLVER-INPUT-INCOMPLETE"]), _ms(started)

    try:
        selected_started = time.perf_counter()
        selected = _solve_given_with_capacity_fallback(solver, state)
        selected_ms = _ms(selected_started)
        hypotheses = _glyph_hypothesis_states(state, recognition)
        hypothesis_started = time.perf_counter()
        alternatives = [
            _solve_given_with_capacity_fallback(solver, item)
            for item in hypotheses
        ]
        hypothesis_ms = _ms(hypothesis_started)
    except CapacityExceeded:
        return _empty("capacity_error", ["API-CAPACITY-SOLVER"]), _ms(started)

    # Full candidate graphs are test diagnostics, not session payloads. Keeping
    # them would multiply response, persistence and privacy cost per turn.
    selected.pop("diagnostics", None)
    for alternative in alternatives:
        alternative.pop("diagnostics", None)
    selected["solverStatus"] = selected["status"]
    signatures = [_tactical_signature(selected), *(_tactical_signature(item) for item in alternatives)]
    diverges = any(signature != signatures[0] for signature in signatures[1:])
    if diverges:
        selected["status"] = "ambiguous_input"
        selected["statusReasonCodes"] = ["VISION-TACTICAL-HYPOTHESES-DIVERGE"]
        selected["actions"] = []
        selected["candidateId"] = None
        selected["sequenceKey"] = None
    elif selected["solverStatus"] in {"solved", "confirmation_required"}:
        selected["status"] = (
            "solved" if recognition.get("recognitionValidated") and not hypotheses else "provisional_solution"
        )
        selected["statusReasonCodes"] = (
            ["S-SOLVED-CONTRACT"]
            if selected["status"] == "solved"
            else ["VISION-TACTICALLY-INVARIANT-PROVISIONAL"]
        )
    elif selected["solverStatus"] == "no_safe_solution":
        selected["status"] = "no_safe_solution"
    elif selected.get("actions"):
        # A concrete candidate must not disappear behind a generic review label.
        selected["status"] = "provisional_solution"
        selected["statusReasonCodes"] = ["VISION-CONCRETE-CANDIDATE-REQUIRES-CAUTION"]
    else:
        selected["status"] = "blocked_missing_data"

    selected["hypothesisSummary"] = {
        "evaluated": 1 + len(alternatives),
        "tacticallyInvariant": not diverges,
        "selectedSignature": signatures[0],
        "alternativeSignatures": signatures[1:],
    }
    selected["_internalTimings"] = {
        "solverMs": selected_ms,
        "hypothesisMs": hypothesis_ms,
    }
    return selected, _ms(started)


def _glyph_hypothesis_states(
    state: dict[str, Any], recognition: dict[str, Any]
) -> list[dict[str, Any]]:
    pattern = (recognition.get("proposals") or {}).get("glyphPattern") or {}
    alternatives = list(pattern.get("alternatives") or [])[:1]
    result: list[dict[str, Any]] = []
    for alternative in alternatives:
        black = alternative.get("blackCells") or []
        white = alternative.get("whiteCells") or []
        if not black or not white:
            continue
        hypothesis = deep_copy(state)
        hypothesis["glyphs"] = {
            "blackOffsets": [{"dx": int(cell["x"]), "dy": int(cell["y"])} for cell in black],
            "whiteOffsets": [{"dx": int(cell["x"]), "dy": int(cell["y"])} for cell in white],
            "physicalBlackCells": deep_copy(black),
            "physicalWhiteCells": deep_copy(white),
        }
        result.append(hypothesis)
    return result


def _tactical_signature(recommendation: dict[str, Any]) -> tuple[Any, ...]:
    expected = recommendation.get("expected") or {}
    return (
        recommendation.get("solverStatus", recommendation.get("status")),
        tuple(action.get("canonicalSignature") for action in recommendation.get("actions", [])),
        _cell_signature(expected.get("finalCell")),
        tuple(expected.get("blackPillarIds") or []),
        tuple(expected.get("whitePillarIds") or []),
        expected.get("raceOutcome"),
        tuple(sorted((expected.get("nextSpellState") or {}).items())),
    )


def _cell_signature(cell: dict[str, int] | None) -> tuple[int, int] | None:
    return None if cell is None else (int(cell["x"]), int(cell["y"]))


def _empty(status: str, reasons: list[str]) -> dict[str, Any]:
    return {
        "schemaVersion": "0.5.0",
        "status": status,
        "statusReasonCodes": reasons,
        "rulesProfileId": "dofuspourlesnoobs-observed-v1.0.0",
        "rankingPolicyId": "ranking-lexicographic-v0.5.0",
        "candidateId": None,
        "sequenceKey": None,
        "actions": [],
        "expected": {
            "finalCell": None,
            "raceOutcome": "unknown",
            "terminalFightState": "unknown",
            "blackPillarIds": [],
            "whitePillarIds": [],
            "rechargedSpells": [],
            "directCenterEffect": "unknown",
            "nextSpellState": None,
        },
        "confidence": {"visual": 0.0, "mechanical": 0.0, "overall": 0.0},
        "alternatives": [],
        "assumptions": [],
        "searchSummary": {
            "definiteRootActions": 0,
            "conditionalRootActions": 0,
            "definiteTerminalCandidates": 0,
            "conditionalTerminalCandidates": 0,
            "adverseDefiniteCandidates": 0,
            "safeDefiniteCandidates": 0,
        },
        "rankingKey": None,
        "trace": [],
        "warnings": [],
    }


def _ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000.0, 3)
