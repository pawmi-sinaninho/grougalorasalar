from __future__ import annotations

from pathlib import Path
import random

from tools.random_scenario_stats import build_random_given, run_stats
from grougal_solver.arena import arena_given


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_random_scenario_generator_builds_solver_shape() -> None:
    arena = arena_given(PROJECT_ROOT)
    given = build_random_given(random.Random(123), arena=arena, pillar_min=22, pillar_max=22)

    assert given["player"]["current"]
    assert len(given["pillars"]) == 22
    assert set(given["resources"]["spells"]) == {"indecision", "reflection", "repulsion", "attraction"}
    assert given["flags"]["solverInputComplete"] is True


def test_random_scenario_stats_runs_small_batch(tmp_path) -> None:
    summary = run_stats(
        runs=3,
        seed=123,
        project_root=PROJECT_ROOT,
        out_dir=tmp_path,
        pillar_min=22,
        pillar_max=22,
        max_nodes=50_000,
        timeout_seconds=2.0,
        fixture_mode=False,
        prune_dominated=True,
        export_limit=3,
    )

    assert summary["runs"] == 3
    assert "solvedRate" in summary
    assert "quality" in summary
    assert "ratesPerRun" in summary["quality"]
    assert "crocoburioAdvanceRate" in summary["quality"]["ratesPerRun"]
    assert (tmp_path / "random_scenario_summary.json").exists()
    assert (tmp_path / "random_scenario_failures.jsonl").exists()


def test_realistic_random_scenario_mode_keeps_charges_and_player_margin() -> None:
    import random

    from tools.random_scenario_stats import _edge_margin

    arena = arena_given(PROJECT_ROOT)
    given = build_random_given(
        random.Random(321),
        arena=arena,
        pillar_min=22,
        pillar_max=22,
        charge_mode="healthy",
        player_margin_min=3,
    )

    charges = {
        spell: item["value"]
        for spell, item in given["resources"]["spells"].items()
    }

    assert all(value >= 1 for value in charges.values())
    assert _edge_margin((given["player"]["current"]["x"], given["player"]["current"]["y"])) >= 3


def test_full_start_random_scenario_mode_uses_two_charges() -> None:
    import random

    arena = arena_given(PROJECT_ROOT)
    given = build_random_given(
        random.Random(456),
        arena=arena,
        pillar_min=22,
        pillar_max=22,
        charge_mode="full-start",
    )

    assert {
        spell: item["value"]
        for spell, item in given["resources"]["spells"].items()
    } == {
        "indecision": 2,
        "reflection": 2,
        "repulsion": 2,
        "attraction": 2,
    }


def test_quality_metrics_report_recharge_and_race_rates(tmp_path) -> None:
    summary = run_stats(
        runs=10,
        seed=999,
        project_root=PROJECT_ROOT,
        out_dir=tmp_path,
        pillar_min=22,
        pillar_max=22,
        max_nodes=50_000,
        timeout_seconds=2.0,
        fixture_mode=True,
        prune_dominated=True,
        export_limit=3,
        charge_mode="late-fight",
        player_margin_min=3,
    )

    quality = summary["quality"]
    assert set(quality) == {"raceOutcomes", "raceOutcomesSolvedOnly", "ratesPerRun", "ratesPerSolved", "averages"}
    assert 0 <= quality["ratesPerRun"]["rechargeRate"] <= 1
    assert 0 <= quality["ratesPerSolved"]["crocoburioAdvanceRate"] <= 1
    assert quality["averages"]["totalChargesAfterRound"] is None or quality["averages"]["totalChargesAfterRound"] >= 0
