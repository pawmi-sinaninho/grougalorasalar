#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def run(*args: str) -> str:
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise AssertionError(f"command failed ({' '.join(args)}):\n{result.stdout}{result.stderr}")
    return result.stdout + result.stderr


# Preserve the cumulative Phase-1–5 specification gates.
run(sys.executable, "tests/validate_phase5.py")

required = [
    "MASTER_SPEC.md",
    "CURRENT_STATUS.md",
    "DECISIONS.md",
    "NEXT_STEP.md",
    "CHANGELOG.md",
    "README.md",
    "TEST_REPORT.md",
    "DEFECT_BACKLOG.md",
    "services/api/grougal_solver/fast_recognition.py",
    "services/api/grougal_solver/recognition.py",
    "services/api/grougal_solver/image_ingest.py",
    "services/api/tests/test_fast_recognition.py",
    "apps/web/public/workers/analysis-worker.js",
    "apps/web/app/page.tsx",
    "data/vision/real-screenshot-fixtures.v0.8.0.json",
    "schemas/real-screenshot-fixture.schema.json",
    "data/runtime/runtime-manifest.v0.8.0.json",
    "data/runtime/runtime-manifest.v0.9.0.json",
    "data/product/phase7a-implementation-status.v0.8.0.json",
    "reports/performance-phase7a.json",
    "docs/architecture/BROWSER_FIRST_FAST_PATH_DECISION.md",
    "docs/vision/FAST_PATH_IMPLEMENTATION.md",
    "docs/testing/PHASE_7A_TEST_AND_PERFORMANCE_REPORT.md",
]
for rel in required:
    path = ROOT / rel
    assert path.exists() and path.stat().st_size > 0, rel

# Contract generation remains deterministic and includes the new fixture schema.
before_manifest = (ROOT / "packages/contracts/schema-manifest.json").read_bytes()
before_ts = (ROOT / "packages/contracts/src/generated.ts").read_bytes()
run(sys.executable, "scripts/generate_contracts.py")
assert (ROOT / "packages/contracts/schema-manifest.json").read_bytes() == before_manifest
assert (ROOT / "packages/contracts/src/generated.ts").read_bytes() == before_ts
contracts = load("packages/contracts/schema-manifest.json")
assert contracts["schemaVersion"] in {"0.8.0", "0.9.0"}
assert any(item["name"] == "real-screenshot-fixture.schema.json" for item in contracts["schemas"])

# New real fixture catalogue validates and retains byte-identical originals.
catalog = load("data/vision/real-screenshot-fixtures.v0.8.0.json")
schema = load("schemas/real-screenshot-fixture.schema.json")
jsonschema.Draft202012Validator(schema).validate(catalog)
assert catalog["fixtureCount"] == 4
assert catalog["distinctness"]["allSha256Unique"] is True
actual_hashes = set()
for fixture in catalog["fixtures"]:
    path = ROOT / fixture["source"]["path"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == fixture["source"]["sha256"]
    assert path.stat().st_size == fixture["source"]["byteSize"]
    assert fixture["source"]["retainedUnmodified"] is True
    assert fixture["source"]["possibleUploadScaling"]["isError"] is False
    assert fixture["logicalAnnotation"]["resources"]["actionBudget"]["value"] is None
    actual_hashes.add(digest)
assert len(actual_hashes) == 4

# Runtime readiness manifest matches all executable data and fixtures. Historical v0.8.0 remains retained, while the current cumulative release is validated through v0.9.0.
manifest = load("data/runtime/runtime-manifest.v0.9.0.json")
assert manifest["schemaVersion"] == manifest["releaseVersion"] == "0.9.0"
for item in manifest["files"]:
    path = ROOT / item["path"]
    assert path.exists(), item["path"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], item["path"]

status = load("data/product/phase7a-implementation-status.v0.8.0.json")
assert status["phase"] == "7A"
assert status["implemented"]["resolutionIndependentArenaRegistration"] is True
assert status["implemented"]["generalGlyphDetector"] is False
assert status["automaticCriticalConfirmation"] is False
assert status["modelCalibrationStatus"] == "unvalidated"
assert status["ocrInStandardPath"] is False

# Safety and runtime boundaries remain explicit.
app_source = (ROOT / "services/api/grougal_solver/app.py").read_text(encoding="utf-8")
recognition_source = (ROOT / "services/api/grougal_solver/recognition.py").read_text(encoding="utf-8")
fast_source = (ROOT / "services/api/grougal_solver/fast_recognition.py").read_text(encoding="utf-8")
page_source = (ROOT / "apps/web/app/page.tsx").read_text(encoding="utf-8")
worker_source = (ROOT / "apps/web/public/workers/analysis-worker.js").read_text(encoding="utf-8")
assert '"automaticCriticalConfirmation": False' in app_source
assert '"modelCalibrationStatus": "unvalidated"' in app_source
assert '"autoConfirmed": False' in recognition_source
assert "pytesseract" not in fast_source.lower()
assert "easyocr" not in fast_source.lower()
assert "ocrInvoked\": False" in fast_source
assert "createImageBitmap" in worker_source and "OffscreenCanvas" in worker_source
assert "preview_ready" in page_source and "recommendationInvalidated" not in page_source or "setAnnotatedUrl('')" in page_source
assert "Budget: 3 actions" not in page_source

# Measured server path fits the revised engineering budgets; browser targets remain unclaimed.
perf = load("reports/performance-phase7a.json")
assert perf["claims"]["engineeringTargetsOnly"] is True
assert perf["claims"]["browserLocalPathMeasured"] is False
samples = perf["samples"]
assert samples["registration"]["p95Ms"] <= 400
assert samples["baselineRecognition"]["p95Ms"] <= 900
assert samples["serverScreenshotToState"]["p95Ms"] <= 2500
assert samples["solver"]["p95Ms"] <= 50

package = load("apps/web/package.json")
assert package["version"] in {"0.8.0", "0.9.0"}
assert package["engines"]["node"] == "24.17.x"
assert package["engines"]["npm"] == "11.18.x"
assert package["packageManager"] == "npm@11.18.0"

master = (ROOT / "MASTER_SPEC.md").read_text(encoding="utf-8")
assert "**Version:** 0.9.0" in master
assert "## 88. Phase 7A acceptance" in master
assert "Phase 7B" in master
assert "visible feedback ≤ 100 ms" in master
assert "server fallback p95 ≤ 2.5 seconds" in master

current = (ROOT / "CURRENT_STATUS.md").read_text(encoding="utf-8")
assert "Phase 7B" in current and "338" in current
next_step = (ROOT / "NEXT_STEP.md").read_text(encoding="utf-8")
assert "150 adjudicated screenshots" in next_step
assert "Codex" in next_step

print("PASS: Phase-7A fixtures, fast path, safety gates, revised performance budgets and Phase-7B handoff validated.")
