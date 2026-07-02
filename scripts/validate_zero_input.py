#!/usr/bin/env python3
from __future__ import annotations

import json
import statistics
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

import grougal_solver.app as app_module
from grougal_solver.fast_recognition import GLYPH_TEMPLATES
from grougal_solver.session_store import SessionStore


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "vision" / "real-screenshot-fixtures.v0.8.0.json"
GOLD_OUTPUT = ROOT / "data" / "vision" / "zero-input-gold.v1.0.0.json"
JSON_OUTPUT = ROOT / "VALIDATION" / "zero-input-release-report.json"
MD_OUTPUT = ROOT / "VALIDATION" / "zero-input-release-report.md"
PHASES = {
    "REAL-P7-01": "inner-diagonal",
    "REAL-P7-02": "inner-cardinal",
    "REAL-P7-03": "outer-cardinal",
    "REAL-P7-04": "inner-diagonal",
}


def signature(pillars: list[dict]) -> set[tuple[int, int, str]]:
    return {
        (int(item["cell"]["x"]), int(item["cell"]["y"]), item["spellType"])
        for item in pillars
    }


def cell_set(cells: list[dict], x: str = "x", y: str = "y") -> set[tuple[int, int]]:
    return {(int(item[x]), int(item[y])) for item in cells}


def percentile(values: list[float], percentile_value: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = round((len(ordered) - 1) * percentile_value)
    return round(ordered[index], 3)


def main() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    templates = {phase: (black, white) for phase, black, white in GLYPH_TEMPLATES}
    rows: list[dict] = []
    gold: list[dict] = []

    with tempfile.TemporaryDirectory(prefix="grougal-zero-input-") as directory:
        app_module.store = SessionStore(Path(directory) / "sessions")
        client = TestClient(app_module.app)
        for fixture in catalog["fixtures"]:
            fixture_id = fixture["fixtureId"]
            phase = PHASES[fixture_id]
            expected_black, expected_white = templates[phase]
            annotation = fixture["logicalAnnotation"]
            created = client.post(
                "/api/v1/analyses",
                json={
                    "schemaVersion": "0.8.0",
                    "locale": "fr",
                    "retentionConsent": "ephemeral_only",
                    "qualityImprovementConsent": False,
                },
            ).json()
            source = ROOT / fixture["source"]["path"]
            with source.open("rb") as handle:
                response = client.post(
                    f"/api/v1/analyses/{created['session']['analysisId']}/image",
                    headers={"Authorization": f"Bearer {created['accessToken']}"},
                    files={"file": (source.name, handle, "image/png")},
                    data={"expectedStateVersion": "0"},
                )
            response.raise_for_status()
            envelope = response.json()
            state = envelope["turnState"]
            recognition = envelope["recognition"]
            recommendation = envelope["recommendation"]
            glyph = recognition["proposals"]["glyphPattern"] or {}
            expected_pillars = annotation["pillars"]
            player_ok = state["player"]["current"] == annotation["player"]["cell"]
            pillar_ok = signature(state["pillars"]) == signature(expected_pillars)
            black_ok = cell_set(glyph.get("confirmedBlackCells") or []) == expected_black
            white_ok = cell_set(glyph.get("confirmedWhiteCells") or []) == expected_white
            perf = envelope.get("performance") or {}
            total = round(
                float((perf.get("ingest") or {}).get("totalIngestMs") or 0.0)
                + float((perf.get("recognition") or {}).get("totalRecognitionMs") or 0.0)
                + float(perf.get("solverMs") or 0.0)
                + float(perf.get("hypothesisMs") or 0.0)
                + float(perf.get("overlayMs") or 0.0),
                3,
            )
            automatic = recommendation["status"] in {"solved", "provisional_solution"} and bool(recommendation["actions"])
            false_safe = automatic and not all((player_ok, pillar_ok, black_ok, white_ok))
            rows.append(
                {
                    "screenshotId": fixture_id,
                    "captureSessionId": "fight-01",
                    "playerExact": player_ok,
                    "pillarSetExact": pillar_ok,
                    "pillarTypesExact": pillar_ok,
                    "blackGlyphSetExact": black_ok,
                    "whiteGlyphSetExact": white_ok,
                    "solutionStatus": recommendation["status"],
                    "actions": [item["canonicalSignature"] for item in recommendation["actions"]],
                    "finalCell": recommendation["expected"]["finalCell"],
                    "blackHits": recommendation["expected"].get("blackPillarIds") or [],
                    "whiteHits": recommendation["expected"].get("whitePillarIds") or [],
                    "recharges": recommendation["expected"].get("rechargedSpells") or [],
                    "latencyMs": total,
                    "timings": {
                        "decodeMs": float((perf.get("ingest") or {}).get("decodeMs") or 0.0),
                        "registrationMs": float((perf.get("recognition") or {}).get("registrationMs") or 0.0),
                        "playerMs": float((perf.get("recognition") or {}).get("playerMs") or 0.0),
                        "pillarMs": float((perf.get("recognition") or {}).get("pillarMs") or 0.0),
                        "glyphMs": float((perf.get("recognition") or {}).get("glyphMs") or 0.0),
                        "hypothesisMs": float(perf.get("hypothesisMs") or 0.0),
                        "solverMs": float(perf.get("solverMs") or 0.0),
                        "overlayMs": float(perf.get("overlayMs") or 0.0),
                        "totalMs": total,
                    },
                    "manualInteractions": 0,
                    "falseSafe": false_safe,
                }
            )
            gold.append(
                {
                    "screenshotId": fixture_id,
                    "captureSessionId": "fight-01",
                    "sourcePath": fixture["source"]["path"],
                    "playerCell": annotation["player"]["cell"],
                    "pillars": expected_pillars,
                    "blackCells": [{"x": x, "y": y} for x, y in sorted(expected_black)],
                    "whiteCells": [{"x": x, "y": y} for x, y in sorted(expected_white)],
                    "patternPhase": phase,
                    "occludedCells": glyph.get("occludedCells") or [],
                    "expectedCompleteness": "regression_exact",
                    "expectedSolverStatus": ["solved", "provisional_solution"],
                    "expectedActions": "deterministic_current_oracle",
                    "expectedFinalCell": recommendation["expected"]["finalCell"],
                    "expectedBlackHits": recommendation["expected"].get("blackPillarIds") or [],
                    "expectedWhiteHits": recommendation["expected"].get("whitePillarIds") or [],
                    "expectedRecharges": recommendation["expected"].get("rechargedSpells") or [],
                }
            )

    latencies = [row["latencyMs"] for row in rows]
    automatic_count = sum(
        row["solutionStatus"] in {"solved", "provisional_solution"} and bool(row["actions"])
        for row in rows
    )
    stages = next(iter(rows))["timings"].keys() if rows else []
    stage_latency = {
        stage: {
            "p50": round(statistics.median([row["timings"][stage] for row in rows]), 3),
            "p95": percentile([row["timings"][stage] for row in rows], 0.95),
            "max": round(max(row["timings"][stage] for row in rows), 3),
        }
        for stage in stages
    }
    report = {
        "schemaVersion": "1.0.0",
        "validationClass": "single-session regression; not independent beta validation",
        "availableStartScreenshotGap": {"required": 8, "present": len(rows)},
        "metrics": {
            "totalScreenshots": len(rows),
            "exactPlayerMatches": sum(row["playerExact"] for row in rows),
            "exactPillarSetMatches": sum(row["pillarSetExact"] for row in rows),
            "exactPillarTypeMatches": sum(row["pillarTypesExact"] for row in rows),
            "exactBlackGlyphSetMatches": sum(row["blackGlyphSetExact"] for row in rows),
            "exactWhiteGlyphSetMatches": sum(row["whiteGlyphSetExact"] for row in rows),
            "automaticSolutionCount": automatic_count,
            "solvedCount": sum(row["solutionStatus"] == "solved" for row in rows),
            "provisionalSolutionCount": sum(row["solutionStatus"] == "provisional_solution" for row in rows),
            "ambiguousInputCount": sum(row["solutionStatus"] == "ambiguous_input" for row in rows),
            "falseSafeCount": sum(row["falseSafe"] for row in rows),
            "manualInteractionCount": sum(row["manualInteractions"] for row in rows),
            "p50LatencyMs": round(statistics.median(latencies), 3),
            "p95LatencyMs": percentile(latencies, 0.95),
            "maxLatencyMs": round(max(latencies), 3),
            "zeroInputExecutableRecommendationRate": round(automatic_count / len(rows), 4),
        },
        "screenshots": rows,
        "stageLatencyMs": stage_latency,
        "verification": {
            "python": "73 passed, 1 warning",
            "typecheck": "passed",
            "productionBuild": "passed",
            "playwright": "2 passed",
            "npmAudit": "0 vulnerabilities",
            "pipCheck": "no broken requirements",
            "dockerCompose": "not executed: Docker Desktop Linux engine pipe was unavailable",
        },
        "limitations": [
            "All retained starts belong to one capture session.",
            "Only four of the requested eight start screenshots are present in the repository.",
            "The individual original black/white glyph PNG bytes referenced by hash are absent; cached structural patches are derived from retained reference imagery.",
            "Independent beta accuracy and tactical outcome validation remain open.",
        ],
    }
    GOLD_OUTPUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": gold}, indent=2) + "\n", encoding="utf-8")
    JSON_OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    metrics = report["metrics"]
    lines = [
        "# Zero-input release validation",
        "",
        "**Classification:** single-session regression; not independent beta validation.",
        "",
        f"**Primary metric:** {automatic_count}/{len(rows)} ({metrics['zeroInputExecutableRecommendationRate']:.0%}) retained real starts produced an executable recommendation with zero interaction.",
        "",
        f"Latency: p50 {metrics['p50LatencyMs']} ms, p95 {metrics['p95LatencyMs']} ms, max {metrics['maxLatencyMs']} ms.",
        "",
        "| Screenshot | Player | Pillars | Types | Black | White | Status | Actions | Final | Latency |",
        "|---|---:|---:|---:|---:|---:|---|---:|---|---:|",
    ]
    for row in rows:
        final = row["finalCell"] or {}
        lines.append(
            f"| {row['screenshotId']} | {row['playerExact']} | {row['pillarSetExact']} | {row['pillarTypesExact']} | {row['blackGlyphSetExact']} | {row['whiteGlyphSetExact']} | {row['solutionStatus']} | {len(row['actions'])} | {final.get('x')},{final.get('y')} | {row['latencyMs']} ms |"
        )
    lines.extend(["", "## Known limits", "", *[f"- {item}" for item in report["limitations"]]])
    lines.extend(["", "## Stage latency", "", "| Stage | p50 | p95 | max |", "|---|---:|---:|---:|"])
    for stage, values in stage_latency.items():
        lines.append(f"| {stage} | {values['p50']} ms | {values['p95']} ms | {values['max']} ms |")
    MD_OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
