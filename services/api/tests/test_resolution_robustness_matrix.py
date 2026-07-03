from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from grougal_solver.fast_recognition import get_fast_engine

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = PROJECT_ROOT / "data" / "vision" / "real-screenshot-fixtures.v0.8.0.json"


def _catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _signature(pillars: list[dict]) -> set[tuple[int, int, str]]:
    return {(item["cell"]["x"], item["cell"]["y"], item["spellType"]) for item in pillars}


def _fixture_source() -> tuple[dict, np.ndarray]:
    fixture = _catalog()["fixtures"][0]
    source = cv2.imread(str(PROJECT_ROOT / fixture["source"]["path"]), cv2.IMREAD_COLOR)
    assert source is not None
    return fixture, source


def _recognise_variant(tmp_path: Path, name: str, image: np.ndarray) -> dict:
    path = tmp_path / name
    assert cv2.imwrite(str(path), image)
    engine = get_fast_engine(PROJECT_ROOT)
    return engine.recognise(path, source_sha256=None)


@pytest.mark.parametrize(
    "size",
    [
        (1280, 720),
        (1366, 768),
        (1600, 900),
        (1920, 1080),
        (2560, 1440),
        (3840, 2160),
    ],
)
def test_common_fullscreen_resolutions_preserve_logical_state(tmp_path: Path, size: tuple[int, int]) -> None:
    fixture, source = _fixture_source()
    interpolation = cv2.INTER_AREA if size[0] < source.shape[1] else cv2.INTER_CUBIC
    variant = cv2.resize(source, size, interpolation=interpolation)

    result = _recognise_variant(tmp_path, f"fullscreen-{size[0]}x{size[1]}.png", variant)

    assert result["registration"]["accepted"] is True, result["registration"]
    assert result["player"]["cell"] == fixture["logicalAnnotation"]["player"]["cell"]
    assert _signature(result["pillars"]) == _signature(fixture["logicalAnnotation"]["pillars"])
    assert result["glyphPattern"] is not None


@pytest.mark.parametrize("size", [(2560, 1080), (3440, 1440), (3840, 1600)])
def test_ultrawide_letterboxed_capture_preserves_logical_state(tmp_path: Path, size: tuple[int, int]) -> None:
    fixture, source = _fixture_source()
    target_w, target_h = size
    scale = min(target_w / source.shape[1], target_h / source.shape[0])
    resized_w = max(1, round(source.shape[1] * scale))
    resized_h = max(1, round(source.shape[0] * scale))
    resized = cv2.resize(source, (resized_w, resized_h), interpolation=cv2.INTER_CUBIC)
    canvas = np.full((target_h, target_w, 3), 18, dtype=np.uint8)
    x0 = (target_w - resized_w) // 2
    y0 = (target_h - resized_h) // 2
    canvas[y0 : y0 + resized_h, x0 : x0 + resized_w] = resized

    result = _recognise_variant(tmp_path, f"ultrawide-{target_w}x{target_h}.png", canvas)

    assert result["registration"]["accepted"] is True, result["registration"]
    assert result["player"]["cell"] == fixture["logicalAnnotation"]["player"]["cell"]
    assert _signature(result["pillars"]) == _signature(fixture["logicalAnnotation"]["pillars"])


def test_windowed_capture_with_os_border_preserves_logical_state(tmp_path: Path) -> None:
    fixture, source = _fixture_source()
    border = cv2.copyMakeBorder(
        source,
        top=44,
        bottom=18,
        left=9,
        right=9,
        borderType=cv2.BORDER_CONSTANT,
        value=(28, 28, 28),
    )
    cv2.rectangle(border, (0, 0), (border.shape[1] - 1, 43), (42, 42, 42), -1)
    cv2.circle(border, (22, 22), 7, (70, 70, 70), -1)
    cv2.circle(border, (46, 22), 7, (70, 70, 70), -1)
    cv2.circle(border, (70, 22), 7, (70, 70, 70), -1)

    result = _recognise_variant(tmp_path, "windowed-with-border.png", border)

    assert result["registration"]["accepted"] is True, result["registration"]
    assert result["player"]["cell"] == fixture["logicalAnnotation"]["player"]["cell"]
    assert _signature(result["pillars"]) == _signature(fixture["logicalAnnotation"]["pillars"])


def test_tiny_scale_then_reencoded_jpeg_still_registers_or_fails_safe(tmp_path: Path) -> None:
    fixture, source = _fixture_source()
    tiny = cv2.resize(source, (1152, 648), interpolation=cv2.INTER_AREA)
    path = tmp_path / "tiny-reencoded.jpg"
    assert cv2.imwrite(str(path), tiny, [cv2.IMWRITE_JPEG_QUALITY, 68])
    result = get_fast_engine(PROJECT_ROOT).recognise(path, source_sha256=None)

    # This is intentionally a hard edge case. It may pass, but if it fails it
    # must stay in manual-registration mode and never emit a fake player/pillar set.
    if result["registration"]["accepted"]:
        assert result["player"]["cell"] == fixture["logicalAnnotation"]["player"]["cell"]
        assert _signature(result["pillars"]) == _signature(fixture["logicalAnnotation"]["pillars"])
    else:
        assert result["status"] == "manual_registration_required"
        assert result["player"] is None
        assert result["pillars"] == []
