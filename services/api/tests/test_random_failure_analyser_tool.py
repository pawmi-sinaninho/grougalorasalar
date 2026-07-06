from __future__ import annotations

import json

from tools.analyse_random_failures import analyse_failures


def test_random_failure_analyser_classifies_shapes(tmp_path) -> None:
    path = tmp_path / "failures.jsonl"
    item = {
        "index": 1,
        "scenarioSeed": 123,
        "given": {
            "player": {"current": {"x": 0, "y": 0}},
            "resources": {
                "spells": {
                    "indecision": {"value": 0},
                    "reflection": {"value": 1},
                    "repulsion": {"value": 0},
                    "attraction": {"value": 1},
                }
            },
            "synthetic": {"glyphTemplateId": "inner-diagonal"},
        },
        "recommendation": {
            "status": "no_safe_solution",
            "statusReasonCodes": ["S-NO-LEGAL-MOVEMENT"],
            "diagnostics": {"definiteRootActions": [], "terminalCandidates": []},
        },
    }
    path.write_text(json.dumps(item) + "\n", encoding="utf-8")

    result = analyse_failures(path)

    assert result["count"] == 1
    assert result["failureShapes"]["no_root_action"] == 1
    assert result["availableSpellCounts"][2] == 1
