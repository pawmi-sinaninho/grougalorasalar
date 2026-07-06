from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from grougal_solver.util import SPELLS, cell_tuple


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


def _charges_key(given: dict[str, Any]) -> str:
    spells = ((given.get("resources") or {}).get("spells") or {})
    return ",".join(f"{spell}={spells.get(spell, {}).get('value')}" for spell in SPELLS)


def _available_spell_count(given: dict[str, Any]) -> int:
    spells = ((given.get("resources") or {}).get("spells") or {})
    return sum(1 for spell in SPELLS if isinstance(spells.get(spell, {}).get("value"), int) and spells[spell]["value"] > 0)


def _root_count(item: dict[str, Any]) -> int:
    return len(((item.get("recommendation") or {}).get("diagnostics") or {}).get("definiteRootActions") or [])


def _terminal_count(item: dict[str, Any]) -> int:
    return len(((item.get("recommendation") or {}).get("diagnostics") or {}).get("terminalCandidates") or [])


def _failure_shape(item: dict[str, Any]) -> str:
    recommendation = item.get("recommendation") or {}
    reasons = recommendation.get("statusReasonCodes") or []
    root_count = _root_count(item)
    terminal_count = _terminal_count(item)

    if "S-NO-LEGAL-MOVEMENT" in reasons:
        if root_count == 0:
            return "no_root_action"
        return "root_action_without_displacement"
    if "S-NO-SAFE-SOLUTION" in reasons:
        if terminal_count == 0:
            return "legal_actions_no_terminal"
        return "all_terminals_black_unsafe"
    return "other"


def analyse_failures(path: Path) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            items.append(json.loads(stripped))

    status = Counter()
    reasons = Counter()
    shapes = Counter()
    charges = Counter()
    available_counts = Counter()
    root_counts = Counter()
    terminal_counts = Counter()
    glyph_templates = Counter()
    edge_margins = Counter()

    examples: dict[str, dict[str, Any]] = {}

    for item in items:
        given = item.get("given") or {}
        recommendation = item.get("recommendation") or {}
        status[str(recommendation.get("status", "unknown"))] += 1
        for reason in recommendation.get("statusReasonCodes") or []:
            reasons[str(reason)] += 1

        shape = _failure_shape(item)
        shapes[shape] += 1
        examples.setdefault(
            shape,
            {
                "index": item.get("index"),
                "scenarioSeed": item.get("scenarioSeed"),
                "charges": _charges_key(given),
                "player": given.get("player", {}).get("current"),
                "rootActions": _root_count(item),
                "terminalCandidates": _terminal_count(item),
                "reasonCodes": recommendation.get("statusReasonCodes") or [],
            },
        )

        charges[_charges_key(given)] += 1
        available_counts[_available_spell_count(given)] += 1
        root_counts[_root_count(item)] += 1
        terminal_counts[_terminal_count(item)] += 1
        glyph_templates[str((given.get("synthetic") or {}).get("glyphTemplateId", "unknown"))] += 1

        player = (given.get("player") or {}).get("current")
        if player:
            margin = _edge_margin(cell_tuple(player))
            if margin <= 1:
                bucket = "edge_0_1"
            elif margin <= 3:
                bucket = "edge_2_3"
            elif margin <= 6:
                bucket = "edge_4_6"
            else:
                bucket = "centre_7_plus"
            edge_margins[bucket] += 1

    return {
        "failureFile": str(path),
        "count": len(items),
        "status": dict(status.most_common()),
        "reasonCodes": dict(reasons.most_common(20)),
        "failureShapes": dict(shapes.most_common()),
        "availableSpellCounts": dict(sorted(available_counts.items())),
        "rootActionCounts": dict(sorted(root_counts.items())),
        "terminalCandidateCounts": dict(sorted(terminal_counts.items())),
        "glyphTemplates": dict(glyph_templates.most_common()),
        "playerEdgeMargins": dict(edge_margins.most_common()),
        "topChargeStates": dict(charges.most_common(15)),
        "exampleByShape": examples,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyse random_scenario_failures.jsonl from random_scenario_stats.py.")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=REPO_ROOT / "stats" / "random-scenarios" / "random_scenario_failures.jsonl",
    )
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "stats" / "random-scenarios" / "random_failure_analysis.json")
    args = parser.parse_args()

    summary = analyse_failures(args.path)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
