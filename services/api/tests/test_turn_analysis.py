from __future__ import annotations

from grougal_solver.turn_analysis import analyse_turn


def _state() -> dict:
    return {
        "player": {"current": {"x": 0, "y": 0}},
        "pillars": [{"id": "P01", "cell": {"x": 2, "y": 0}, "spellType": "reflection"}],
        "glyphs": {
            "blackOffsets": [{"dx": 1, "dy": 0}],
            "whiteOffsets": [{"dx": 0, "dy": 1}],
            "physicalBlackCells": [{"x": 1, "y": 0}],
            "physicalWhiteCells": [{"x": 0, "y": 1}],
        },
        "resources": {
            "actionBudget": 12,
            "spells": {
                spell: {"availability": "available", "value": 2, "confirmed": True}
                for spell in ("indecision", "reflection", "repulsion", "attraction")
            },
        },
        "flags": {"anchorConfirmed": True, "pillarHypothesisUsable": True},
    }


def _recognition(alternative: bool = False) -> dict:
    return {
        "registration": {"accepted": True},
        "recognitionValidated": False,
        "proposals": {
            "glyphPattern": {
                "alternatives": [] if not alternative else [{
                    "phase": "other",
                    "blackCells": [{"x": -1, "y": 0}],
                    "whiteCells": [{"x": 0, "y": -1}],
                }]
            }
        },
    }


class FakeSolver:
    def __init__(self, diverge: bool = False):
        self.diverge = diverge

    def solve_given(self, state: dict, **_: object) -> dict:
        first = state["glyphs"]["blackOffsets"][0]
        marker = "B" if self.diverge and first["dx"] < 0 else "A"
        return {
            "schemaVersion": "0.5.0",
            "status": "solved",
            "statusReasonCodes": ["S-SOLVED-CONTRACT"],
            "candidateId": marker,
            "sequenceKey": marker,
            "actions": [{"canonicalSignature": marker}],
            "expected": {
                "finalCell": {"x": 1 if marker == "A" else -1, "y": 0},
                "raceOutcome": "crocoburio_advance",
                "blackPillarIds": [],
                "whitePillarIds": [],
                "nextSpellState": {"indecision": 2, "reflection": 2, "repulsion": 2, "attraction": 2},
            },
            "diagnostics": {"large": "removed"},
        }


def test_unvalidated_but_complete_state_returns_concrete_provisional_solution() -> None:
    result, _ = analyse_turn(FakeSolver(), _state(), _recognition())  # type: ignore[arg-type]
    assert result["status"] == "provisional_solution"
    assert result["actions"]
    assert result["hypothesisSummary"]["tacticallyInvariant"] is True
    assert "diagnostics" not in result


def test_divergent_plausible_glyph_hypothesis_is_ambiguous() -> None:
    result, _ = analyse_turn(FakeSolver(diverge=True), _state(), _recognition(alternative=True))  # type: ignore[arg-type]
    assert result["status"] == "ambiguous_input"
    assert result["actions"] == []
    assert result["hypothesisSummary"]["tacticallyInvariant"] is False


def test_same_action_under_plausible_hypothesis_stays_provisional() -> None:
    result, _ = analyse_turn(FakeSolver(), _state(), _recognition(alternative=True))  # type: ignore[arg-type]
    assert result["status"] == "provisional_solution"
    assert result["actions"]
    assert result["hypothesisSummary"]["evaluated"] == 2
