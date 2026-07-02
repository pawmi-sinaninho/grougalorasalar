#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def run(*args: str) -> str:
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise AssertionError(f"command failed ({' '.join(args)}):\n{result.stdout}{result.stderr}")
    return result.stdout + result.stderr


# Preserve every previous specification gate.
run(sys.executable, "tests/validate_phase5.py")

required = [
    "docker-compose.yml",
    "services/api/Dockerfile",
    "services/api/requirements.txt",
    "services/api/grougal_solver/app.py",
    "services/api/grougal_solver/solver.py",
    "services/api/grougal_solver/session_store.py",
    "services/api/grougal_solver/editor.py",
    "services/api/grougal_solver/recognition.py",
    "services/api/tests/test_api_vertical_slice.py",
    "apps/web/Dockerfile",
    "apps/web/package.json",
    "apps/web/package-lock.json",
    "apps/web/app/page.tsx",
    "packages/contracts/schema-manifest.json",
    "data/runtime/runtime-manifest.v0.7.0.json",
    "data/product/phase6-implementation-status.v0.7.0.json",
    "reports/performance-phase6.json",
    "reports/SBOM.spdx.json",
    "docs/implementation/PHASE_6_IMPLEMENTATION_REPORT.md",
    "docs/implementation/KNOWN_LIMITATIONS.md",
    "docs/operations/RUNBOOK.md",
    "DEFECT_BACKLOG.md",
]
for rel in required:
    path = ROOT / rel
    assert path.exists() and path.stat().st_size > 0, rel

# Generated contracts must be deterministic.
before_manifest = (ROOT / "packages/contracts/schema-manifest.json").read_bytes()
before_ts = (ROOT / "packages/contracts/src/generated.ts").read_bytes()
run(sys.executable, "scripts/generate_contracts.py")
assert (ROOT / "packages/contracts/schema-manifest.json").read_bytes() == before_manifest
assert (ROOT / "packages/contracts/src/generated.ts").read_bytes() == before_ts

# Runtime manifest must match the files used by readiness.
manifest = load("data/runtime/runtime-manifest.v0.7.0.json")
assert manifest["schemaVersion"] == manifest["releaseVersion"] == "0.7.0"
for item in manifest["files"]:
    path = ROOT / item["path"]
    assert path.exists(), item["path"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], item["path"]

status = load("data/product/phase6-implementation-status.v0.7.0.json")
assert status["phase"] == 6
assert status["implemented"]["manualVerticalSlice"] is True
assert status["implemented"]["deterministicSolver"] is True
assert status["implemented"]["generalScreenshotDetector"] is False
assert status["automaticCriticalConfirmation"] is False
assert status["modelCalibrationStatus"] == "unvalidated"

# Safety policy must remain explicit in runtime source.
app_source = (ROOT / "services/api/grougal_solver/app.py").read_text(encoding="utf-8")
recognition_source = (ROOT / "services/api/grougal_solver/recognition.py").read_text(encoding="utf-8")
assert '"automaticCriticalConfirmation": False' in app_source
assert '"modelCalibrationStatus": "unvalidated"' in app_source
assert '"autoConfirmed": False' in recognition_source
assert "FIXTURE_MODE and ENVIRONMENT in" in app_source

# Product statuses are distinct from technical capacity failures.
solver_source = (ROOT / "services/api/grougal_solver/solver.py").read_text(encoding="utf-8")
turn_analysis_source = (ROOT / "services/api/grougal_solver/turn_analysis.py").read_text(encoding="utf-8")
assert "class CapacityExceeded" in solver_source
assert "100_000" in solver_source or "100000" in solver_source
assert "API-CAPACITY-SOLVER" in turn_analysis_source

# The web page must visibly disclose the zero-input boundary.
page = (ROOT / "apps/web/app/page.tsx").read_text(encoding="utf-8")
assert "Aucune saisie ni confirmation" in page
assert "uploadImage" in page and "runSolver" in page

# Performance samples must fit the frozen engineering budgets.
perf = load("reports/performance-phase6.json")["samples"]
assert perf["referenceImageNormalisation"]["p95Ms"] <= 8_000
assert perf["solverFixture"]["p95Ms"] <= 500
assert perf["sessionMutation"]["p95Ms"] <= 150
assert perf["sessionDelete"]["p95Ms"] <= 500

package = load("apps/web/package.json")
assert package["version"] in {"0.7.0", "0.8.0", "0.9.0", "1.0.0"}
assert "24" in package["engines"]["node"]
assert package["overrides"]["postcss"] == "8.5.10"

master = (ROOT / "MASTER_SPEC.md").read_text(encoding="utf-8")
assert any(version in master for version in ("**Version:** 0.7.0", "**Version:** 0.8.0", "**Version:** 0.9.0", "**Version:** 1.0.0"))
assert "## 78. Phase-6 acceptance result" in master
assert "Immediate next phase: Phase 7" in master
assert "automaticCriticalConfirmation` is always `false`" in master

current = (ROOT / "CURRENT_STATUS.md").read_text(encoding="utf-8")
assert ("7 passed" in current and "Phase 7 — Pre-Live Validation" in current) or "ZERO-INPUT" in current
next_step = (ROOT / "NEXT_STEP.md").read_text(encoding="utf-8")
assert "critical false-safe recommendations equal zero" in next_step or "locked 150-screenshot" in next_step

print("PASS: Phase-6 repository, safety boundary, runtime integrity, implementation status, performance budgets and Phase-7 handoff validated.")
