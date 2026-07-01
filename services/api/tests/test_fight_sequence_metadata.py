from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_corrected_training_sequence_has_two_frames_but_live_uses_one_start_frame() -> None:
    sequence = json.loads(
        (PROJECT_ROOT / "data" / "vision" / "fight-01-sequence.v1.0.0.json").read_text(encoding="utf-8")
    )
    assert sequence["liveContract"]["screenshotsPerRound"] == 1
    assert sequence["liveContract"]["captureMoment"] == "start_of_round"
    assert sequence["liveContract"]["endFrameRequired"] is False
    assert len(sequence["rounds"]) == 8
    assert all(item.get("start") and item.get("trainingEnd") for item in sequence["rounds"])


def test_round_two_owns_the_corrected_blue_end_frame_and_no_wrong_name_survives() -> None:
    sequence = json.loads(
        (PROJECT_ROOT / "data" / "vision" / "fight-01-sequence.v1.0.0.json").read_text(encoding="utf-8")
    )
    names = {
        frame["file"]
        for round_item in sequence["rounds"]
        for frame in (round_item["start"], round_item["trainingEnd"])
    }
    assert "fight-01-round-02-1blueused.png" in names
    assert "fight-01-round-01-1blueused.png" not in names


def test_observed_training_end_positions_form_a_continuous_fight() -> None:
    sequence = json.loads(
        (PROJECT_ROOT / "data" / "vision" / "fight-01-sequence.v1.0.0.json").read_text(encoding="utf-8")
    )
    for current, following in zip(sequence["rounds"], sequence["rounds"][1:]):
        assert current["trainingEnd"]["player"] == following["start"]["player"]


def test_round_eight_resource_observation_matches_normative_transition() -> None:
    sequence = json.loads(
        (PROJECT_ROOT / "data" / "vision" / "fight-01-sequence.v1.0.0.json").read_text(encoding="utf-8")
    )
    round_eight = sequence["rounds"][7]
    assert round_eight["casts"] == ["attraction"]
    assert round_eight["observedMatchingWhiteHits"] == {"repulsion": 1}
    assert round_eight["chargesAtNextRound"] == {
        "indecision": 2,
        "reflection": 3,
        "repulsion": 3,
        "attraction": 1,
    }
