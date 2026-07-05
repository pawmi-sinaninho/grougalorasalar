from __future__ import annotations

from grougal_solver.recommendation_validator import validate_recommendation


def _state() -> dict:
    return {
        "arena": {
            "walkable": [
                {"x": -4, "y": -3},
                {"x": -3, "y": -2},
                {"x": -2, "y": -1},
                {"x": -4, "y": -2},
                {"x": -4, "y": -4},
            ],
            "boundaryUnverified": [],
            "occludedUnknown": [],
            "permanentBlocked": [],
        },
        "player": {"current": {"x": -4, "y": -3}},
        "pillars": [
            {
                "id": "P_LOW",
                "cell": {"x": -3, "y": -2},
                "spellType": "indecision",
                "confidence": 0.78,
                "snapResidualCell": 0.23,
            }
        ],
        "resources": {
            "spells": {
                "indecision": {"availability": "available", "value": 2, "confirmed": True},
                "reflection": {"availability": "available", "value": 2, "confirmed": True},
                "repulsion": {"availability": "available", "value": 2, "confirmed": True},
                "attraction": {"availability": "available", "value": 2, "confirmed": True},
            }
        },
    }


def _recommendation() -> dict:
    return {
        "status": "provisional_solution",
        "statusReasonCodes": ["VISION-CONCRETE-CANDIDATE-REQUIRES-CAUTION"],
        "actions": [
            {
                "order": 1,
                "spell": "reflection",
                "sourceCell": {"x": -4, "y": -3},
                "targetKind": "pillar",
                "targetPillarId": "P_LOW",
                "targetCell": {"x": -3, "y": -2},
                "destinationCell": {"x": -2, "y": -1},
                "canonicalSignature": "reflection@pillar:-3,-2:P_LOW",
                "instruction": "reflection -> P_LOW",
            }
        ],
        "expected": {
            "finalCell": {"x": -2, "y": -1},
            "raceOutcome": "crocoburio_advance",
            "blackPillarIds": [],
            "whitePillarIds": [],
            "rechargedSpells": [],
            "directCenterEffect": "none",
            "nextSpellState": {
                "indecision": 2,
                "reflection": 1,
                "repulsion": 2,
                "attraction": 2,
            },
        },
        "confidence": {"visual": 1.0, "mechanical": 0.5, "overall": 0.5},
    }


def test_validator_blocks_low_confidence_target_pillar() -> None:
    result = validate_recommendation(_state(), _recommendation())

    assert result["status"] == "blocked_unverified_rule"
    assert result["actions"] == []
    assert result["expected"]["finalCell"] is None
    assert "VALIDATOR-ACTION-1-TARGET-PILLAR-LOW-CONFIDENCE" in result["statusReasonCodes"]
    assert "VALIDATOR-ACTION-1-TARGET-PILLAR-WEAK-SNAP" in result["statusReasonCodes"]


def test_validator_passes_strong_diagonal_reflection() -> None:
    state = _state()
    state["pillars"][0]["confidence"] = 0.98
    state["pillars"][0]["snapResidualCell"] = 0.01

    result = validate_recommendation(state, _recommendation())

    assert result["status"] == "provisional_solution"
    assert result["actions"]


def test_validator_blocks_reflection_without_real_target_pillar() -> None:
    state = _state()
    state["pillars"] = []

    result = validate_recommendation(state, _recommendation())

    assert result["status"] == "blocked_unverified_rule"
    assert "VALIDATOR-ACTION-1-TARGET-PILLAR-MISSING" in result["statusReasonCodes"]


def test_validator_blocks_bad_indecision_geometry() -> None:
    state = _state()
    recommendation = _recommendation()
    recommendation["actions"] = [
        {
            "order": 1,
            "spell": "indecision",
            "sourceCell": {"x": -4, "y": -3},
            "targetKind": "cell",
            "targetCell": {"x": -3, "y": -2},
            "destinationCell": {"x": -3, "y": -2},
            "canonicalSignature": "indecision@cell:-3,-2",
            "instruction": "indecision -> case -3,-2",
        }
    ]

    result = validate_recommendation(state, recommendation)

    assert result["status"] == "blocked_unverified_rule"
    assert "VALIDATOR-ACTION-1-INDECISION-NOT-ORTHOGONAL" in result["statusReasonCodes"]
