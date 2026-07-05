from __future__ import annotations

from pathlib import Path

from grougal_solver.profiles import RuleAuthority, compile_profile
from grougal_solver.solver import ArenaSets, DeterministicSolver

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SPELLS = ("indecision", "reflection", "repulsion", "attraction")


def test_low_confidence_pillar_target_is_conditional_not_definite() -> None:
    solver = DeterministicSolver(PROJECT_ROOT)
    profile = compile_profile(PROJECT_ROOT, {}, action_budget=12, fixture_mode=False)
    given = {
        "resources": {
            "spells": {
                spell: {"availability": "available", "value": 2, "confirmed": True}
                for spell in SPELLS
            }
        }
    }
    arena = ArenaSets(
        walkable=frozenset({(0, 0), (1, 1), (2, 2)}),
        boundary=frozenset(),
        occluded=frozenset(),
        blocked=frozenset(),
    )
    pillar = {
        "id": "P_LOW",
        "cell": {"x": 1, "y": 1},
        "spellType": "indecision",
        "confidence": 0.78,
        "snapResidualCell": 0.23,
    }

    definite, conditional = solver._enumerate_actions(
        (0, 0),
        given,
        profile,
        arena,
        {(1, 1): pillar},
        {spell: 0 for spell in SPELLS},
        {spell: 2 for spell in SPELLS},
        12,
        RuleAuthority(solver.rule_statuses),
        False,
    )

    assert not [action for action in definite if action["targetPillarId"] == "P_LOW"]
    weak_targets = [action for action in conditional if action["targetPillarId"] == "P_LOW"]
    assert weak_targets
    assert "VISION-LOW-CONFIDENCE-TARGET-PILLAR" in weak_targets[0]["conditionalRuleIds"]
    assert "VISION-LOW-SNAP-TARGET-PILLAR" in weak_targets[0]["conditionalRuleIds"]
