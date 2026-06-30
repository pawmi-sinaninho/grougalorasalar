#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def validate(schema_rel: str, instance_rel: str, registry: Registry | None = None) -> None:
    schema = load(schema_rel)
    instance = load(instance_rel)
    errors = sorted(
        Draft202012Validator(schema, registry=registry or Registry()).iter_errors(instance),
        key=lambda e: list(e.path),
    )
    if errors:
        details = " | ".join(f"{list(e.path)}: {e.message}" for e in errors[:12])
        raise AssertionError(f"{instance_rel} against {schema_rel}: {details}")


# Preserve Phase-2 and Phase-3 cumulative regression checks.
r = subprocess.run(
    [sys.executable, str(ROOT / "tests/validate_phase3.py")],
    cwd=ROOT,
    text=True,
    capture_output=True,
)
if r.returncode != 0:
    raise AssertionError("Phase-3 regression failed: " + r.stdout + r.stderr)

new_schemas = [
    "schemas/visual-observation.schema.json",
    "schemas/recognition-result.schema.json",
    "schemas/annotation-record.schema.json",
    "schemas/visual-fixture-catalog.schema.json",
]
for rel in new_schemas:
    Draft202012Validator.check_schema(load(rel))

obs_schema = load("schemas/visual-observation.schema.json")
registry = Registry().with_resource(obs_schema["$id"], Resource.from_contents(obs_schema))
validate("schemas/recognition-result.schema.json", "examples/recognition-result.reference.json", registry)
validate("schemas/annotation-record.schema.json", "examples/annotation-record.reference.json")
validate("schemas/visual-fixture-catalog.schema.json", "data/vision/visual-fixture-catalog.v0.5.0.json")

# Every embedded observation also validates independently.
for i, observation in enumerate(load("examples/recognition-result.reference.json")["observations"]):
    errors = list(Draft202012Validator(obs_schema).iter_errors(observation))
    if errors:
        raise AssertionError(f"observation {i}: {errors[0].message}")

policy = load("data/vision/recognition-policy.v0.5.0.json")
assert policy["policyId"] == "recognition-policy-v0.5.0"
assert policy["autoConfirmation"]["enabledByDefault"] is False
assert policy["solverGate"]["unvalidatedModelRule"]
assert policy["registration"]["accepted"]["p95ResidualCellsMax"] < policy["registration"]["review"]["p95ResidualCellsMax"]
assert policy["fieldThresholds"]["glyphPattern.blackOffsets"]["autoConfirm"] >= 0.97

field_map = load("data/vision/field-gating-map.v0.5.0.json")
paths = {x["fieldPath"] for x in field_map["fields"]}
for required in [
    "image.arenaPresence",
    "arena.calibration",
    "player.currentCell",
    "pillarSet",
    "glyphPattern.blackOffsets",
    "glyphPattern.whiteOffsets",
    "spellState.actionBudget",
    "spellState.spells.*",
]:
    assert required in paths

fixtures = load("data/vision/visual-fixture-catalog.v0.5.0.json")
assert fixtures["fixtureCount"] == len(fixtures["fixtures"]) == 20
ids = [x["fixtureId"] for x in fixtures["fixtures"]]
assert len(ids) == len(set(ids)) and ids[0] == "VFX-001" and ids[-1] == "VFX-020"
assert any(x["expectedGate"] == "ready_for_solver" for x in fixtures["fixtures"])
assert any(x["expectedGate"] == "rejected" for x in fixtures["fixtures"])
assert any("MODEL-001" in x["expectedReasonCodes"] for x in fixtures["fixtures"])

metrics = load("data/vision/evaluation-targets.v0.5.0.json")
metric_by_id = {m["id"]: m for m in metrics["metrics"]}
assert metric_by_id["M-FALSE-SAFE"]["target"] == 0
assert metric_by_id["M-BLACK-SET"]["target"] == 1.0
assert metrics["autoConfirmationEntryGate"]["minimumLockedTestScreenshots"] >= 150

messages = load("data/vision/failure-message-catalog.v0.5.0.json")
message_ids = {m["id"] for m in messages["messages"]}
for required in ["IMG-002", "REG-001", "MULTI-001", "GLYPH-001", "BUDGET-001", "MODEL-001"]:
    assert required in message_ids
for m in messages["messages"]:
    assert all(m.get(lang) for lang in ["fr", "de", "en"])

turn = load("data/arena/reference-turn.manual.json")
assert turn["schemaVersion"] == "0.5.0"
assert turn["pillarSet"]["confirmed"] is True
assert turn["glyphPattern"]["blackConfirmed"] is True
assert turn["spellState"]["actionBudgetConfirmed"] is False
assert turn["visualProvenance"]["gateStatus"] == "review_required"

recognition = load("examples/recognition-result.reference.json")
assert recognition["gate"]["status"] == "review_required"
assert recognition["gate"]["autoConfirmationEnabled"] is False
assert set(recognition["gate"]["blockingReasonCodes"]) >= {"ANCHOR-001", "BUDGET-001", "SPELL-001", "MODEL-001"}

required_docs = [
    "docs/vision/SCREENSHOT_INGEST_AND_REGISTRATION.md",
    "docs/vision/OBSERVATION_EXTRACTION_CONTRACT.md",
    "docs/vision/CONFIDENCE_AND_CONFLICT_MODEL.md",
    "docs/vision/DATASET_ANNOTATION_PROTOCOL.md",
    "docs/vision/EVALUATION_AND_REGRESSION.md",
    "docs/ux/CONFIDENCE_CORRECTION_UX.md",
    "docs/ux/REJECTION_AND_FAILURE_COPY.md",
    "docs/workflow/PHASE_5_CHAT_BRIEF.md",
]
for rel in required_docs:
    p = ROOT / rel
    assert p.exists() and p.stat().st_size > 700, rel

print("PASS: Phase-3 regression plus Phase-4 recognition, confidence, UX, dataset and evaluation contracts validated.")
