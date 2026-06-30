from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import cv2
import jsonschema
import numpy as np
import pytest

from grougal_solver.editor import validate_turn_state
from grougal_solver.fast_recognition import get_fast_engine
from grougal_solver.recognition import REFERENCE_SHA256, baseline_recognition

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = PROJECT_ROOT / "data" / "vision" / "real-screenshot-fixtures.v0.8.0.json"


def _catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _signature(pillars: list[dict]) -> set[tuple[int, int, str]]:
    return {(item["cell"]["x"], item["cell"]["y"], item["spellType"]) for item in pillars}


def test_real_fixture_catalog_is_reproducible_and_distinct() -> None:
    catalog = _catalog()
    schema = json.loads((PROJECT_ROOT / "schemas" / "real-screenshot-fixture.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(catalog)
    assert catalog["fixtureCount"] == 4
    hashes = []
    dimensions = set()
    for fixture in catalog["fixtures"]:
        path = PROJECT_ROOT / fixture["source"]["path"]
        assert path.exists()
        assert path.stat().st_size == fixture["source"]["byteSize"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == fixture["source"]["sha256"]
        hashes.append(digest)
        dimensions.add((fixture["source"]["width"], fixture["source"]["height"]))
        assert fixture["source"]["retainedUnmodified"] is True
        assert fixture["source"]["possibleUploadScaling"]["isError"] is False
    assert len(set(hashes)) == 4
    assert dimensions == {(2048, 1151)}


def test_all_four_new_real_screenshots_match_logical_player_and_pillars() -> None:
    engine = get_fast_engine(PROJECT_ROOT)
    for fixture in _catalog()["fixtures"]:
        path = PROJECT_ROOT / fixture["source"]["path"]
        result = engine.recognise(path, source_sha256=fixture["source"]["sha256"])
        expected_player = fixture["logicalAnnotation"]["player"]["cell"]
        assert result["status"] == "recognised_review_required", fixture["fixtureId"]
        assert result["registration"]["accepted"] is True, fixture["fixtureId"]
        assert result["matchedFixtureId"] == fixture["fixtureId"]
        assert result["player"]["cell"] == expected_player
        assert _signature(result["pillars"]) == _signature(fixture["logicalAnnotation"]["pillars"])
        assert result["metrics"]["ocrInvoked"] is False
        assert result["metrics"]["templatesReloaded"] is False
        assert result["metrics"]["totalRecognitionMs"] < 5_000


def test_all_five_real_screenshots_enter_the_pipeline_without_pixel_data_reaching_solver_state(tmp_path: Path) -> None:
    reference = PROJECT_ROOT / "assets" / "reference" / "user_reference.png"
    state, observations, recognition = baseline_recognition(
        PROJECT_ROOT,
        reference,
        source_sha256=REFERENCE_SHA256,
        source_width=1951,
        source_height=1267,
        working_width=1951,
        working_height=1267,
    )
    assert len(state["pillars"]) == 27
    assert recognition["matchedFixtureId"] == "REFERENCE-01"
    assert observations

    for fixture in _catalog()["fixtures"]:
        path = PROJECT_ROOT / fixture["source"]["path"]
        state, _, recognition = baseline_recognition(
            PROJECT_ROOT,
            path,
            source_sha256=fixture["source"]["sha256"],
            source_width=2048,
            source_height=1151,
            working_width=2048,
            working_height=1151,
        )
        serialized = json.dumps(state).lower()
        assert "pixel" not in serialized
        assert "affine" not in serialized
        assert recognition["registration"]["referenceToImageAffine"] is not None
        blockers = validate_turn_state(state)
        assert blockers == []
        assert state["flags"]["criticalFieldsConfirmed"] is True
        assert recognition["automaticCriticalConfirmation"] is True


@pytest.mark.parametrize("size", [(1920, 1080), (2560, 1440), (3840, 2160)])
def test_resolution_changes_preserve_identical_logical_output(tmp_path: Path, size: tuple[int, int]) -> None:
    engine = get_fast_engine(PROJECT_ROOT)
    fixture = _catalog()["fixtures"][0]
    source = cv2.imread(str(PROJECT_ROOT / fixture["source"]["path"]), cv2.IMREAD_COLOR)
    resized = cv2.resize(source, size, interpolation=cv2.INTER_AREA if size[0] < source.shape[1] else cv2.INTER_CUBIC)
    path = tmp_path / f"scaled-{size[0]}x{size[1]}.png"
    cv2.imwrite(str(path), resized)
    result = engine.recognise(path, source_sha256=None)
    assert result["matchedFixtureId"] == fixture["fixtureId"]
    assert result["player"]["cell"] == fixture["logicalAnnotation"]["player"]["cell"]
    assert _signature(result["pillars"]) == _signature(fixture["logicalAnnotation"]["pillars"])


@pytest.mark.parametrize("variant", ["jpeg", "border", "crop"])
def test_compression_borders_and_small_crops_preserve_logical_output(tmp_path: Path, variant: str) -> None:
    engine = get_fast_engine(PROJECT_ROOT)
    fixture = _catalog()["fixtures"][0]
    source = cv2.imread(str(PROJECT_ROOT / fixture["source"]["path"]), cv2.IMREAD_COLOR)
    suffix = ".png"
    if variant == "jpeg":
        path = tmp_path / "compressed.jpg"
        cv2.imwrite(str(path), source, [cv2.IMWRITE_JPEG_QUALITY, 72])
    elif variant == "border":
        altered = cv2.copyMakeBorder(source, 18, 22, 24, 20, cv2.BORDER_CONSTANT, value=(20, 20, 20))
        path = tmp_path / "border.png"
        cv2.imwrite(str(path), altered)
    else:
        altered = source[8:-10, 12:-14]
        path = tmp_path / "crop.png"
        cv2.imwrite(str(path), altered)
    result = engine.recognise(path, source_sha256=None)
    assert result["registration"]["accepted"] is True
    assert result["matchedFixtureId"] == fixture["fixtureId"]
    assert result["player"]["cell"] == fixture["logicalAnnotation"]["player"]["cell"]
    assert _signature(result["pillars"]) == _signature(fixture["logicalAnnotation"]["pillars"])


def test_non_arena_uses_manual_fallback_and_cannot_emit_safe_recommendation(tmp_path: Path) -> None:
    engine = get_fast_engine(PROJECT_ROOT)
    rng = np.random.default_rng(42)
    noise = rng.integers(0, 255, size=(720, 1280, 3), dtype=np.uint8)
    path = tmp_path / "not-arena.png"
    cv2.imwrite(str(path), noise)
    result = engine.recognise(path, source_sha256=None)
    assert result["status"] == "manual_registration_required"
    assert result["registration"]["accepted"] is False
    assert result["player"] is None
    assert result["pillars"] == []
    assert result["metrics"]["ocrInvoked"] is False


def test_web_worker_protocol_exists_and_is_valid_javascript() -> None:
    worker = PROJECT_ROOT / "apps" / "web" / "public" / "workers" / "analysis-worker.js"
    source = worker.read_text(encoding="utf-8")
    assert "createImageBitmap" in source
    assert "OffscreenCanvas" in source
    assert "working_copy_ready" in source
    node = shutil.which("node")
    if node:
        completed = subprocess.run([node, "--check", str(worker)], capture_output=True, text=True)
        assert completed.returncode == 0, completed.stderr
