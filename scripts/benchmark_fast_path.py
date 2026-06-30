#!/usr/bin/env python3
from __future__ import annotations

import json
import statistics
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "services" / "api"))

from grougal_solver.fast_recognition import get_fast_engine
from grougal_solver.fixtures import load_fixture_catalog, run_fixture
from grougal_solver.image_ingest import normalise_image
from grougal_solver.recognition import baseline_recognition


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = (len(ordered) - 1) * q
    low = int(index)
    high = min(low + 1, len(ordered) - 1)
    fraction = index - low
    return ordered[low] * (1 - fraction) + ordered[high] * fraction


def stats(values: list[float]) -> dict:
    return {
        "samples": len(values),
        "medianMs": round(statistics.median(values), 3),
        "p95Ms": round(percentile(values, 0.95), 3),
        "maxMs": round(max(values), 3),
    }


def main() -> None:
    engine = get_fast_engine(ROOT)
    samples: dict[str, list[float]] = {
        "decode": [], "workingCopy": [], "registration": [], "canonicalWarp": [],
        "cellSampling": [], "baselineRecognition": [], "serverScreenshotToState": [], "solver": []
    }
    fixture_paths = [ROOT / f"packages/fixtures/real/phase7/round-{index:02d}.png" for index in range(1, 5)]
    for _ in range(3):
        for source in fixture_paths:
            with tempfile.TemporaryDirectory() as temp:
                details = normalise_image(source.read_bytes(), Path(temp))
                _, _, recognition = baseline_recognition(
                    ROOT,
                    Path(details["working"]),
                    source_sha256=details["sha256"],
                    source_width=details["width"],
                    source_height=details["height"],
                    working_width=details["workingWidth"],
                    working_height=details["workingHeight"],
                )
                ingest = details["metrics"]
                vision = recognition["metrics"]
                samples["decode"].append(ingest["decodeMs"])
                samples["workingCopy"].append(ingest["workingCopyMs"])
                samples["registration"].append(vision["registrationMs"])
                samples["canonicalWarp"].append(vision["canonicalWarpMs"])
                samples["cellSampling"].append(vision["cellSamplingMs"])
                samples["baselineRecognition"].append(vision["totalRecognitionMs"])
                samples["serverScreenshotToState"].append(ingest["totalIngestMs"] + vision["totalRecognitionMs"])

    catalogue = load_fixture_catalog(ROOT)
    for _ in range(5):
        for fixture in catalogue["fixtures"]:
            started = time.perf_counter()
            run_fixture(ROOT, fixture)
            samples["solver"].append((time.perf_counter() - started) * 1000.0)

    report = {
        "schemaVersion": "0.8.0",
        "measuredAt": "2026-06-28",
        "environment": "shared container; engineering sample only",
        "warmCache": True,
        "coldEngineInitialisationMs": engine.initialisation_ms,
        "targets": {
            "visibleFeedbackMs": 100,
            "browserDecodeAndWorkingCopyP95Ms": 150,
            "registrationP95Ms": 400,
            "baselineRecognitionP95Ms": 900,
            "solverP95Ms": 50,
            "localScreenshotToResultP95Ms": 1200,
            "serverFallbackP95Ms": 2500,
            "hardTimeoutMs": 5000
        },
        "samples": {name: stats(values) for name, values in samples.items()},
        "claims": {
            "engineeringTargetsOnly": True,
            "browserLocalPathMeasured": False,
            "productionHardwareMeasured": False,
            "detectorAccuracyMeasured": False
        }
    }
    destination = ROOT / "reports" / "performance-phase7a.json"
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
