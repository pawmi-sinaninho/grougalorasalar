#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def validate(schema_rel: str, instance_rel: str) -> None:
    schema = load(schema_rel)
    instance = load(instance_rel)
    errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        details = " | ".join(f"{list(e.path)}: {e.message}" for e in errors[:12])
        raise AssertionError(f"{instance_rel} against {schema_rel}: {details}")


# Preserve complete Phase-4 regression chain.
r = subprocess.run(
    [sys.executable, str(ROOT / "tests/validate_phase4.py")],
    cwd=ROOT,
    text=True,
    capture_output=True,
)
if r.returncode != 0:
    raise AssertionError("Phase-4 regression failed: " + r.stdout + r.stderr)

schema_examples = {
    "schemas/api-error.schema.json": "examples/api-error.state-version.json",
    "schemas/analysis-session.schema.json": "examples/analysis-session.review.json",
    "schemas/editor-command.schema.json": "examples/editor-command.set-player.json",
    "schemas/overlay-document.schema.json": "examples/overlay-document.review.json",
    "schemas/analysis-event.schema.json": "examples/analysis-event.recognition-completed.json",
}
for schema_rel, example_rel in schema_examples.items():
    Draft202012Validator.check_schema(load(schema_rel))
    validate(schema_rel, example_rel)

ownership = load("data/architecture/package-ownership.v0.6.0.json")
assert ownership["schemaVersion"] == "0.6.0"
assert ownership["runtime"] == {
    "node": "24.17.0",
    "python": "3.13.14",
    "nextMajor": 16,
    "fastapi": "0.138.1",
}
paths = {x["path"] for x in ownership["packages"]}
for required in ["apps/web", "services/api", "python/grougal_vision", "python/grougal_solver", "packages/contracts"]:
    assert required in paths

endpoints = load("data/api/endpoint-catalog.v0.6.0.json")
assert endpoints["basePath"] == "/api/v1"
ops = {x["operationId"] for x in endpoints["endpoints"]}
for required in ["create_analysis", "upload_image", "apply_editor_command", "solve", "get_overlay", "delete_analysis"]:
    assert required in ops
assert len(endpoints["developmentOnly"]) == 3

pages = load("data/product/page-state-catalog.v0.6.0.json")
state_ids = {x["id"] for x in pages["workspaceStates"]}
for required in ["registration_review", "ready_for_solver", "solved", "technical_failure", "deleted"]:
    assert required in state_ids
assert pages["mobileCorrectionSupported"] is False
assert pages["breakpoints"] == {"mobileMax": 767, "tabletMax": 1179, "desktopMin": 1180}

backlog = load("data/product/phase6-backlog.v0.6.0.json")
ids = [x["id"] for x in backlog["items"]]
assert len(ids) == len(set(ids)) == 19
assert ids[0] == "P6-001" and ids[-1] == "P6-019"
assert [x["wave"] for x in backlog["items"]] == sorted([x["wave"] for x in backlog["items"]])

copy = load("data/content/ui-copy.v0.6.0.json")
assert copy["defaultLocale"] == "fr"
assert copy["supportedLocales"] == ["fr", "de", "en"]
for key, translations in copy["messages"].items():
    assert set(translations) == {"fr", "de", "en"}, key
    assert all(translations.values()), key

required_docs = [
    "docs/architecture/PRE_LIVE_TECHNICAL_BLUEPRINT.md",
    "docs/api/HTTP_API_AND_EVENT_CONTRACTS.md",
    "docs/frontend/PAGE_COMPONENT_STATE_INVENTORY.md",
    "docs/frontend/VISUAL_INTERACTION_SYSTEM.md",
    "docs/content/FRENCH_FIRST_COPY.md",
    "docs/privacy/PRIVACY_RETENTION_AND_DELETION.md",
    "docs/development/LOCAL_DEVELOPMENT_AND_FIXTURE_MODE.md",
    "docs/testing/TEST_MATRIX_AND_PERFORMANCE_BUDGETS.md",
    "docs/deployment/DEPLOYMENT_OBSERVABILITY_AND_RECOVERY.md",
    "docs/product/PHASE_6_IMPLEMENTATION_BACKLOG.md",
    "docs/workflow/PHASE_6_CHAT_BRIEF.md",
]
for rel in required_docs:
    p = ROOT / rel
    assert p.exists() and p.stat().st_size > 800, rel

master = (ROOT / "MASTER_SPEC.md").read_text(encoding="utf-8")
assert any(version in master for version in ("**Version:** 0.6.0", "**Version:** 0.7.0", "**Version:** 0.8.0", "**Version:** 0.9.0", "**Version:** 1.0.0"))
assert "Phase 5 — Complete Pre-Live Technical & Visual Specification" in master
assert "## 68. Phase-5 acceptance result" in master
assert any(next_phase in master for next_phase in ("Immediate next phase: Phase 6", "Immediate next phase: Phase 7", "Immediate next phase: Phase 7B"))

status = (ROOT / "CURRENT_STATUS.md").read_text(encoding="utf-8")
assert any(version in status for version in ("Version:** 0.6.0", "Version:** 0.7.0", "Version:** 0.8.0", "Version:** 0.9.0", "Version:** 1.0.0"))
assert any(phase in status for phase in ("First Pre-Live Implementation", "Browser-first Fast Recognition", "Canonical Arena Mask", "Boundary Refinement", "7B-R", "ZERO-INPUT"))

next_step = (ROOT / "NEXT_STEP.md").read_text(encoding="utf-8")
assert (
    ("MODEL-001" in next_step and ("manual" in next_step.lower() or "validation" in next_step.lower()))
    or ("provisional_solution" in next_step and "corpus" in next_step.lower())
)

print("PASS: Phase-4 regression plus Phase-5 architecture, API, UI, privacy, testing, deployment and Phase-6 backlog contracts validated.")
