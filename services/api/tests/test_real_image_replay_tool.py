from __future__ import annotations

from pathlib import Path

import pytest

from tools.real_image_replay import collect_entries, run_replay


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_real_image_replay_collects_folder_entries() -> None:
    fixture_dir = PROJECT_ROOT / "packages" / "fixtures" / "real" / "phase7"
    if not fixture_dir.exists():
        pytest.skip("phase7 real fixture folder not present")

    entries = collect_entries(images=[str(fixture_dir)], manifest=None)

    assert entries
    assert all(Path(item["image"]).exists() for item in entries)


def test_real_image_replay_runs_single_fixture(tmp_path) -> None:
    fixture = PROJECT_ROOT / "packages" / "fixtures" / "real" / "phase7" / "round-01.png"
    if not fixture.exists():
        pytest.skip("phase7 real fixture not present")

    summary = run_replay(
        [{"id": "round-01", "image": str(fixture)}],
        out_dir=tmp_path,
        session_dir=tmp_path / "sessions",
    )

    assert summary["images"] == 1
    assert summary["processed"] == 1
    assert summary["failedUploads"] == 0
    assert summary["recognition"]["registrationAcceptedRate"] == 1.0
    assert summary["session"]["readyForSolverRate"] == 1.0
    assert summary["recommendation"]["statuses"]
    assert (tmp_path / "real_image_replay_details.jsonl").exists()
    assert (tmp_path / "real_image_replay_summary.json").exists()
