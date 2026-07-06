from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from grougal_solver.arena import arena_given
from grougal_solver.solver import CapacityExceeded, DeterministicSolver
from grougal_solver.util import SPELLS, cell_tuple


GLYPH_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "id": "inner-diagonal",
        "blackOffsets": [
            {"dx": -1, "dy": -1}, {"dx": -1, "dy": 1},
            {"dx": 1, "dy": -1}, {"dx": 1, "dy": 1},
        ],
        "whiteOffsets": [
            {"dx": -3, "dy": 0}, {"dx": 0, "dy": -3},
            {"dx": -2, "dy": 0}, {"dx": 0, "dy": -2},
            {"dx": 0, "dy": 2}, {"dx": 2, "dy": 0},
            {"dx": 0, "dy": 3}, {"dx": 3, "dy": 0},
        ],
    },
    {
        "id": "outer-diagonal",
        "blackOffsets": [
            {"dx": -3, "dy": -3}, {"dx": -2, "dy": -2},
            {"dx": -3, "dy": 3}, {"dx": -2, "dy": 2},
            {"dx": 2, "dy": -2}, {"dx": 3, "dy": -3},
            {"dx": 2, "dy": 2}, {"dx": 3, "dy": 3},
        ],
        "whiteOffsets": [
            {"dx": -1, "dy": 0}, {"dx": 0, "dy": -1},
            {"dx": 0, "dy": 1}, {"dx": 1, "dy": 0},
        ],
    },
)


def _edge_margin(cell: tuple[int, int]) -> int:
    x, y = cell
    return min(
        x + 12,
        13 - x,
        y + 12,
        13 - y,
        x + y + 11,
        13 - (x + y),
        x - y + 13,
        13 - (x - y),
    )


def _random_charges(
    rng: random.Random,
    *,
    charge_mode: str,
    low_charge_bias: bool,
) -> dict[str, int]:
    if charge_mode == "chaos":
        if low_charge_bias and rng.random() < 0.55:
            charges = {spell: rng.choice([0, 1, 1, 2, 3]) for spell in SPELLS}
        else:
            charges = {spell: rng.randint(0, 4) for spell in SPELLS}
    elif charge_mode == "healthy":
        charges = {spell: rng.randint(1, 4) for spell in SPELLS}
    elif charge_mode == "full-start":
        charges = {spell: 2 for spell in SPELLS}
    elif charge_mode == "late-fight":
        charges = {spell: rng.choice([1, 1, 2, 2, 3, 4]) for spell in SPELLS}
    else:
        raise ValueError(f"Unknown charge mode: {charge_mode}")

    if all(value == 0 for value in charges.values()):
        charges[rng.choice(list(SPELLS))] = 1
    return charges


def _cell_dict(cell: tuple[int, int]) -> dict[str, int]:
    return {"x": int(cell[0]), "y": int(cell[1])}


def _arena_dict(project_root: Path) -> dict[str, Any]:
    raw = arena_given(project_root)
    if "walkable" in raw:
        return raw
    if "arena" in raw and "walkable" in raw["arena"]:
        return raw["arena"]
    raise RuntimeError("arena_given(...) did not return a dict containing walkable cells")


def _spell_state(charges: dict[str, int]) -> dict[str, Any]:
    return {
        "actionBudget": 12,
        "spells": {
            spell: {
                "availability": "available" if int(charges[spell]) > 0 else "unavailable",
                "value": int(charges[spell]),
                "confirmed": True,
            }
            for spell in SPELLS
        },
    }


def _glyphs(template: dict[str, Any]) -> dict[str, Any]:
    return {
        "blackOffsets": list(template["blackOffsets"]),
        "whiteOffsets": list(template["whiteOffsets"]),
        "physicalBlackCells": [{"x": item["dx"], "y": item["dy"]} for item in template["blackOffsets"]],
        "physicalWhiteCells": [{"x": item["dx"], "y": item["dy"]} for item in template["whiteOffsets"]],
    }


def build_random_given(
    rng: random.Random,
    *,
    arena: dict[str, Any],
    pillar_min: int = 22,
    pillar_max: int = 28,
    low_charge_bias: bool = True,
    charge_mode: str = "chaos",
    player_margin_min: int = 0,
) -> dict[str, Any]:
    walkable = [cell_tuple(item) for item in arena["walkable"]]
    if len(walkable) < pillar_max + 2:
        raise RuntimeError("arena has too few walkable cells for random scenario generation")

    player_pool = [cell for cell in walkable if _edge_margin(cell) >= player_margin_min]
    if not player_pool:
        player_pool = walkable
    player = rng.choice(player_pool)
    available_cells = [cell for cell in walkable if cell != player]
    pillar_count = rng.randint(pillar_min, pillar_max)
    pillar_cells = rng.sample(available_cells, pillar_count)

    pillars = [
        {
            "id": f"P{index:02d}",
            "cell": _cell_dict(cell),
            "spellType": rng.choice(list(SPELLS)),
            "confidence": 1.0,
            "snapResidualCell": 0.0,
        }
        for index, cell in enumerate(pillar_cells, start=1)
    ]

    charges = _random_charges(
        rng,
        charge_mode=charge_mode,
        low_charge_bias=low_charge_bias,
    )

    template = rng.choice(GLYPH_TEMPLATES)
    return {
        "summary": "Synthetic random scenario generated by tools/random_scenario_stats.py",
        "profileMode": "synthetic_random_stats",
        "arena": arena,
        "player": {"current": _cell_dict(player), "previous": None},
        "pillars": pillars,
        "glyphs": _glyphs(template),
        "resources": _spell_state(charges),
        "progress": {"dragon": None, "crocoburio": None},
        "flags": {
            "anchorConfirmed": True,
            "criticalFieldsConfirmed": True,
            "multiplayerDetected": False,
            "pillarSetComplete": True,
            "pillarHypothesisUsable": True,
            "glyphHypothesisUsable": True,
            "solverInputComplete": True,
            "recognitionValidated": True,
            "modelCalibrationStatus": "synthetic",
        },
        "profileOverrides": {},
        "profileId": "dofuspourlesnoobs-observed-v1.0.0",
        "synthetic": {
            "glyphTemplateId": template["id"],
            "charges": charges,
            "pillarCount": pillar_count,
        },
    }


def _rate(value: int | float, denominator: int | float) -> float:
    return round(float(value) / max(float(denominator), 1.0), 6)


def _mean(values: list[int]) -> float | None:
    if not values:
        return None
    return round(statistics.fmean(values), 3)


def _classify_result(result: dict[str, Any]) -> str:
    status = result.get("status", "unknown")
    actions = result.get("actions") or []
    expected = result.get("expected") or {}
    if status in {"solved", "provisional_solution", "confirmation_required"} and actions:
        if expected.get("whitePillarIds") or expected.get("rechargedSpells"):
            return "solved_with_recharge"
        return "solved_safe_movement"
    return str(status)


def run_stats(
    *,
    runs: int,
    seed: int,
    project_root: Path,
    out_dir: Path,
    pillar_min: int,
    pillar_max: int,
    max_nodes: int,
    timeout_seconds: float,
    fixture_mode: bool,
    prune_dominated: bool,
    export_limit: int,
    charge_mode: str = "chaos",
    player_margin_min: int = 0,
) -> dict[str, Any]:
    rng = random.Random(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    arena = _arena_dict(project_root)
    solver = DeterministicSolver(project_root)

    counters: Counter[str] = Counter()
    reason_counters: Counter[str] = Counter()
    race_counters: Counter[str] = Counter()
    solved_race_counters: Counter[str] = Counter()
    solver_times_ms: list[float] = []
    white_hit_counts: list[int] = []
    recharged_spell_counts: list[int] = []
    total_charges_after: list[int] = []
    min_charges_after: list[int] = []
    zero_spell_counts_after: list[int] = []
    exported = 0
    failures_path = out_dir / "random_scenario_failures.jsonl"

    with failures_path.open("w", encoding="utf-8") as failures:
        for index in range(1, runs + 1):
            scenario_seed = rng.randrange(0, 2**63)
            scenario_rng = random.Random(scenario_seed)
            given = build_random_given(
                scenario_rng,
                arena=arena,
                pillar_min=pillar_min,
                pillar_max=pillar_max,
                charge_mode=charge_mode,
                player_margin_min=player_margin_min,
            )

            started = time.perf_counter()
            try:
                result = solver.solve_given(
                    given,
                    fixture_mode=fixture_mode,
                    max_nodes=max_nodes,
                    timeout_seconds=timeout_seconds,
                    prune_dominated=prune_dominated,
                )
                elapsed_ms = (time.perf_counter() - started) * 1000
                solver_times_ms.append(elapsed_ms)
                bucket = _classify_result(result)
            except CapacityExceeded as exc:
                elapsed_ms = (time.perf_counter() - started) * 1000
                solver_times_ms.append(elapsed_ms)
                result = {
                    "status": "capacity_error",
                    "statusReasonCodes": [str(exc)],
                    "actions": [],
                    "expected": {},
                }
                bucket = "capacity_error"

            counters[bucket] += 1
            expected = result.get("expected") or {}
            race_outcome = str(expected.get("raceOutcome") or "unknown")
            race_counters[race_outcome] += 1
            if bucket in {"solved_with_recharge", "solved_safe_movement"}:
                solved_race_counters[race_outcome] += 1

            white_hit_counts.append(len(expected.get("whitePillarIds") or []))
            recharged_spell_counts.append(len(expected.get("rechargedSpells") or []))

            next_spell_state = expected.get("nextSpellState") or {}
            known_next_values = [
                int(next_spell_state[spell])
                for spell in SPELLS
                if isinstance(next_spell_state.get(spell), int)
            ]
            if len(known_next_values) == len(SPELLS):
                total_charges_after.append(sum(known_next_values))
                min_charges_after.append(min(known_next_values))
                zero_spell_counts_after.append(sum(1 for value in known_next_values if value == 0))

            for reason in result.get("statusReasonCodes") or []:
                reason_counters[str(reason)] += 1

            if bucket not in {"solved_with_recharge", "solved_safe_movement"} and exported < export_limit:
                failures.write(
                    json.dumps(
                        {
                            "index": index,
                            "scenarioSeed": scenario_seed,
                            "bucket": bucket,
                            "elapsedMs": round(elapsed_ms, 3),
                            "given": given,
                            "recommendation": result,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )
                exported += 1

    solved = counters["solved_with_recharge"] + counters["solved_safe_movement"]
    quality = {
        "raceOutcomes": dict(race_counters.most_common()),
        "raceOutcomesSolvedOnly": dict(solved_race_counters.most_common()),
        "ratesPerRun": {
            "crocoburioAdvanceRate": _rate(race_counters["crocoburio_advance"], runs),
            "dragonAdvanceRate": _rate(race_counters["dragon_advance"], runs),
            "neutralRate": _rate(race_counters["neutral"], runs),
            "unknownRate": _rate(race_counters["unknown"], runs),
            "rechargeRate": _rate(counters["solved_with_recharge"], runs),
            "safeMovementOnlyRate": _rate(counters["solved_safe_movement"], runs),
        },
        "ratesPerSolved": {
            "crocoburioAdvanceRate": _rate(solved_race_counters["crocoburio_advance"], solved),
            "dragonAdvanceRate": _rate(solved_race_counters["dragon_advance"], solved),
            "neutralRate": _rate(solved_race_counters["neutral"], solved),
            "unknownRate": _rate(solved_race_counters["unknown"], solved),
            "rechargeRate": _rate(counters["solved_with_recharge"], solved),
            "safeMovementOnlyRate": _rate(counters["solved_safe_movement"], solved),
        },
        "averages": {
            "whitePillarsHit": _mean(white_hit_counts),
            "rechargedSpells": _mean(recharged_spell_counts),
            "totalChargesAfterRound": _mean(total_charges_after),
            "minChargeAfterRound": _mean(min_charges_after),
            "zeroSpellsAfterRound": _mean(zero_spell_counts_after),
        },
    }
    sorted_times = sorted(solver_times_ms)
    summary = {
        "runs": runs,
        "quality": quality,
        "seed": seed,
        "solved": solved,
        "solvedRate": round(solved / max(runs, 1), 6),
        "buckets": dict(counters.most_common()),
        "topReasonCodes": dict(reason_counters.most_common(20)),
        "timingMs": {
            "mean": round(statistics.fmean(solver_times_ms), 3) if solver_times_ms else None,
            "p95": round(sorted_times[int(0.95 * (len(sorted_times) - 1))], 3) if sorted_times else None,
            "max": round(max(solver_times_ms), 3) if solver_times_ms else None,
        },
        "settings": {
            "pillarMin": pillar_min,
            "pillarMax": pillar_max,
            "maxNodes": max_nodes,
            "timeoutSeconds": timeout_seconds,
            "fixtureMode": fixture_mode,
            "pruneDominated": prune_dominated,
            "exportLimit": export_limit,
            "chargeMode": charge_mode,
            "playerMarginMin": player_margin_min,
        },
        "outputs": {"failuresJsonl": str(failures_path)},
    }
    summary_path = out_dir / "random_scenario_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run random synthetic scenario statistics against DeterministicSolver.")
    parser.add_argument("--runs", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "stats" / "random-scenarios")
    parser.add_argument("--pillar-min", type=int, default=22)
    parser.add_argument("--pillar-max", type=int, default=28)
    parser.add_argument("--max-nodes", type=int, default=100_000)
    parser.add_argument("--timeout-seconds", type=float, default=2.0)
    parser.add_argument("--fixture-mode", action="store_true")
    parser.add_argument("--no-prune-dominated", action="store_true")
    parser.add_argument("--export-limit", type=int, default=50)
    parser.add_argument(
        "--charge-mode",
        choices=["chaos", "healthy", "full-start", "late-fight"],
        default="chaos",
        help="Synthetic charge distribution: chaos=current stress test, healthy=no zero charges, full-start=all 2, late-fight=1..4 biased realistic.",
    )
    parser.add_argument(
        "--player-margin-min",
        type=int,
        default=0,
        help="Minimum tactical distance from arena edge for generated player starts. Falls back to all cells if impossible.",
    )
    args = parser.parse_args()

    summary = run_stats(
        runs=args.runs,
        seed=args.seed,
        project_root=args.project_root,
        out_dir=args.out_dir,
        pillar_min=args.pillar_min,
        pillar_max=args.pillar_max,
        max_nodes=args.max_nodes,
        timeout_seconds=args.timeout_seconds,
        fixture_mode=args.fixture_mode,
        prune_dominated=not args.no_prune_dominated,
        export_limit=args.export_limit,
        charge_mode=args.charge_mode,
        player_margin_min=args.player_margin_min,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
