from __future__ import annotations

from pathlib import Path
from typing import Any

from .solver import DeterministicSolver
from .util import load_json


def load_fixture_catalog(project_root: Path) -> dict[str, Any]:
    return load_json(project_root / "data" / "solver" / "fixture-catalog.v0.5.0.json")


def get_fixture(project_root: Path, fixture_id: str) -> dict[str, Any]:
    for fixture in load_fixture_catalog(project_root)["fixtures"]:
        if fixture["fixtureId"] == fixture_id:
            return fixture
    raise KeyError(fixture_id)


def run_fixture(project_root: Path, fixture: dict[str, Any]) -> dict[str, Any]:
    solver = DeterministicSolver(project_root)
    return solver.solve_given(
        fixture["given"],
        focus_rule_ids=fixture.get("focusRuleIds", []),
        fixture_mode=True,
    )


def contract_projection(result: dict[str, Any]) -> dict[str, Any]:
    diagnostics = result.get("diagnostics", {})
    return {
        "status": result["status"],
        "statusReasonCodes": result["statusReasonCodes"],
        "definiteRootActions": diagnostics.get("definiteRootActions", []),
        "conditionalRootActions": diagnostics.get("conditionalRootActions", []),
        "orderedRecommendedSequences": [
            action_sequence(result)
        ]
        + [item.get("sequence", []) for item in result.get("alternatives", [])]
        if result.get("actions")
        else [],
    }


def action_sequence(result: dict[str, Any]) -> list[str]:
    return [action["canonicalSignature"] for action in result.get("actions", [])]
