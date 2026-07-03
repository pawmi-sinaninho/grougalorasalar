from __future__ import annotations

from pathlib import Path
import re
import textwrap

ROOT = Path.cwd()
FAST = ROOT / "services" / "api" / "grougal_solver" / "fast_recognition.py"
TEST = ROOT / "services" / "api" / "tests" / "test_resolution_robustness_matrix.py"
DOC = ROOT / "docs" / "vision" / "RESOLUTION_ROBUSTNESS.md"


def fail(message: str) -> None:
    raise SystemExit(f"[resolution-robustness patch] {message}")


def read(path: Path) -> str:
    if not path.exists():
        fail(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"updated {path.relative_to(ROOT)}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"Expected exactly one match for {label}, found {count}")
    return text.replace(old, new, 1)


def patch_fast_recognition() -> None:
    source = read(FAST)
    if "WORK_MULTI_SCALE_WIDTHS" in source:
        print("fast_recognition.py already contains multi-scale registration constants; skipping core patch")
        return

    source = replace_once(
        source,
        "WORK_MAX_WIDTH = 1280\n",
        "WORK_MAX_WIDTH = 1280\n"
        "WORK_EXTRA_MAX_WIDTH = 1792\n"
        "WORK_MULTI_SCALE_WIDTHS = (960, 1152, 1280, 1536, 1792)\n",
        "working-width constants",
    )

    source = replace_once(
        source,
        "        if self._reference_descriptors is None or len(self._reference_keypoints) < 100:\n"
        "            raise RuntimeError(\"Reference ORB feature cache is insufficient\")\n",
        "        if self._reference_descriptors is None or len(self._reference_keypoints) < 100:\n"
        "            raise RuntimeError(\"Reference ORB feature cache is insufficient\")\n"
        "        self._registration_variant_cache: dict[int, tuple[Any, float, Any, Any]] = {\n"
        "            int(round(self.reference_width * self._reference_scale)): (\n"
        "                self._reference_work,\n"
        "                self._reference_scale,\n"
        "                self._reference_keypoints,\n"
        "                self._reference_descriptors,\n"
        "            )\n"
        "        }\n",
        "registration variant cache",
    )

    source = replace_once(
        source,
        "    def register(self, image: np.ndarray) -> RegistrationResult:\n"
        "        target_work, target_scale = self._working_gray(image)\n",
        "    def register(self, image: np.ndarray) -> RegistrationResult:\n"
        "        \"\"\"Register a screenshot against the canonical arena using resolution retries.\n\n"
        "        Different players capture Dofus at different desktop/window sizes. ORB is\n"
        "        scale-tolerant, but one downscaled working width can still lose the exact\n"
        "        features needed for this arena. We therefore try a small bounded set of\n"
        "        width-normalised registrations and keep the geometrically best accepted\n"
        "        affine transform. Solver input remains pixel-free.\n"
        "        \"\"\"\n"
        "        height, width = image.shape[:2]\n"
        "        attempts: list[tuple[int, RegistrationResult]] = []\n"
        "        for target_width in self._registration_width_candidates(width):\n"
        "            reference_work, reference_scale, reference_keypoints, reference_descriptors = (\n"
        "                self._registration_variant(target_width)\n"
        "            )\n"
        "            result = self._register_once(\n"
        "                image,\n"
        "                target_width=target_width,\n"
        "                reference_work=reference_work,\n"
        "                reference_scale=reference_scale,\n"
        "                reference_keypoints=reference_keypoints,\n"
        "                reference_descriptors=reference_descriptors,\n"
        "            )\n"
        "            attempts.append((target_width, result))\n\n"
        "        accepted = [(width, item) for width, item in attempts if item.accepted]\n"
        "        if accepted:\n"
        "            accepted.sort(\n"
        "                key=lambda pair: (\n"
        "                    pair[1].p95_residual_cell if pair[1].p95_residual_cell is not None else 999.0,\n"
        "                    pair[1].median_residual_cell if pair[1].median_residual_cell is not None else 999.0,\n"
        "                    -pair[1].inlier_count,\n"
        "                    -pair[1].confidence,\n"
        "                    pair[0],\n"
        "                )\n"
        "            )\n"
        "            return accepted[0][1]\n\n"
        "        if attempts:\n"
        "            attempts.sort(\n"
        "                key=lambda pair: (\n"
        "                    -pair[1].confidence,\n"
        "                    -pair[1].inlier_count,\n"
        "                    pair[1].p95_residual_cell if pair[1].p95_residual_cell is not None else 999.0,\n"
        "                    pair[0],\n"
        "                )\n"
        "            )\n"
        "            return attempts[0][1]\n\n"
        "        return self._registration_failure(\"VISION-REGISTRATION-NO-VARIANTS\")\n\n"
        "    def _register_once(\n"
        "        self,\n"
        "        image: np.ndarray,\n"
        "        *,\n"
        "        target_width: int | None = None,\n"
        "        reference_work: np.ndarray | None = None,\n"
        "        reference_scale: float | None = None,\n"
        "        reference_keypoints: Any | None = None,\n"
        "        reference_descriptors: np.ndarray | None = None,\n"
        "    ) -> RegistrationResult:\n"
        "        target_work, target_scale = self._working_gray(image, target_width=target_width)\n"
        "        reference_work = self._reference_work if reference_work is None else reference_work\n"
        "        reference_scale = self._reference_scale if reference_scale is None else reference_scale\n"
        "        reference_keypoints = self._reference_keypoints if reference_keypoints is None else reference_keypoints\n"
        "        reference_descriptors = self._reference_descriptors if reference_descriptors is None else reference_descriptors\n",
        "register wrapper",
    )

    source = replace_once(
        source,
        "        pairs = self._matcher.knnMatch(self._reference_descriptors, descriptors, k=2)\n",
        "        pairs = self._matcher.knnMatch(reference_descriptors, descriptors, k=2)\n",
        "matcher descriptors",
    )
    source = replace_once(
        source,
        "        source_work = np.float32([self._reference_keypoints[item.queryIdx].pt for item in good])\n",
        "        source_work = np.float32([reference_keypoints[item.queryIdx].pt for item in good])\n",
        "reference keypoints",
    )
    source = replace_once(
        source,
        "        reference_basis_work = REFERENCE_BASIS * self._reference_scale\n",
        "        reference_basis_work = REFERENCE_BASIS * reference_scale\n",
        "reference basis scale",
    )
    source = replace_once(
        source,
        "        region_count = self._spatial_region_count(source_work[inliers])\n",
        "        region_count = self._spatial_region_count(source_work[inliers], reference_work.shape[:2])\n",
        "spatial region shape",
    )
    source = replace_once(
        source,
        "        affine_original = self._to_original_affine(affine_work, target_scale)\n",
        "        affine_original = self._to_original_affine(affine_work, target_scale, reference_scale)\n",
        "affine scale conversion",
    )

    methods = '''\n    def _registration_width_candidates(self, source_width: int) -> tuple[int, ...]:\n        if source_width <= 0:\n            return (WORK_MIN_WIDTH,)\n        default_width = min(WORK_MAX_WIDTH, max(WORK_MIN_WIDTH, source_width))\n        upper = min(WORK_EXTRA_MAX_WIDTH, max(WORK_MIN_WIDTH, source_width))\n        candidates: list[int] = [default_width]\n        for width in WORK_MULTI_SCALE_WIDTHS:\n            if WORK_MIN_WIDTH <= width <= upper:\n                candidates.append(width)\n        if upper not in candidates:\n            candidates.append(upper)\n        unique: list[int] = []\n        for width in candidates:\n            normalized = int(width)\n            if normalized not in unique:\n                unique.append(normalized)\n        return tuple(unique)\n\n    def _registration_variant(self, target_width: int) -> tuple[np.ndarray, float, Any, np.ndarray]:\n        target_width = int(target_width)\n        cached = self._registration_variant_cache.get(target_width)\n        if cached is not None:\n            return cached\n        reference_work, reference_scale = self._working_gray(self.reference, target_width=target_width)\n        keypoints, descriptors = self._orb.detectAndCompute(reference_work, None)\n        if descriptors is None or len(keypoints) < 100:\n            # Fall back to the boot-time cache rather than letting one weak\n            # reference scale make all registration fail.\n            return (\n                self._reference_work,\n                self._reference_scale,\n                self._reference_keypoints,\n                self._reference_descriptors,\n            )\n        cached = (reference_work, reference_scale, keypoints, descriptors)\n        self._registration_variant_cache[target_width] = cached\n        return cached\n'''
    source = replace_once(
        source,
        "    def _working_gray(self, image: np.ndarray) -> tuple[np.ndarray, float]:\n",
        methods + "\n    def _working_gray(self, image: np.ndarray, target_width: int | None = None) -> tuple[np.ndarray, float]:\n",
        "registration helper methods",
    )
    source = replace_once(
        source,
        "        target_width = min(WORK_MAX_WIDTH, max(WORK_MIN_WIDTH, width))\n",
        "        if target_width is None:\n"
        "            target_width = min(WORK_MAX_WIDTH, max(WORK_MIN_WIDTH, width))\n"
        "        else:\n"
        "            target_width = max(1, int(target_width))\n",
        "working gray target width",
    )
    source = replace_once(
        source,
        "    def _to_original_affine(self, affine_work: np.ndarray, target_scale: float) -> np.ndarray:\n"
        "        original = affine_work.astype(np.float64).copy()\n"
        "        original[:, :2] *= self._reference_scale / target_scale\n",
        "    def _to_original_affine(\n"
        "        self,\n"
        "        affine_work: np.ndarray,\n"
        "        target_scale: float,\n"
        "        reference_scale: float | None = None,\n"
        "    ) -> np.ndarray:\n"
        "        original = affine_work.astype(np.float64).copy()\n"
        "        reference_scale = self._reference_scale if reference_scale is None else reference_scale\n"
        "        original[:, :2] *= reference_scale / target_scale\n",
        "to original affine signature",
    )
    source = replace_once(
        source,
        "    def _spatial_region_count(self, points: np.ndarray) -> int:\n"
        "        if len(points) == 0:\n"
        "            return 0\n"
        "        height, width = self._reference_work.shape[:2]\n",
        "    def _spatial_region_count(\n"
        "        self,\n"
        "        points: np.ndarray,\n"
        "        work_shape: tuple[int, int] | None = None,\n"
        "    ) -> int:\n"
        "        if len(points) == 0:\n"
        "            return 0\n"
        "        height, width = work_shape if work_shape is not None else self._reference_work.shape[:2]\n",
        "spatial region count signature",
    )

    write(FAST, source)


def write_tests() -> None:
    test_source = r'''
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
'''.lstrip()
    write(TEST, test_source)


def write_docs() -> None:
    doc = r'''
# Resolution Robustness Contract

This release treats screenshot resolution as a registration problem, not as a UI-size assumption.

## Implemented strategy

1. Decode the captured image exactly as received.
2. Try several bounded ORB working widths instead of relying on one downscaled size.
3. Estimate a limited affine arena transform per attempt with RANSAC.
4. Keep the accepted transform with the lowest p95 residual, then warp the image to the canonical reference frame.
5. Detect player, pillars, glyphs and charge tracks only in canonical coordinates.
6. If registration cannot pass the geometry gate, return `manual_registration_required` instead of inventing a result.

## Why this matters

Players may use 1280x720, 1366x768, 1920x1080, 2560x1440, 3840x2160, ultrawide monitors, window borders, browser/GPU scaling or compressed capture streams. The board must be normalized before object detection; raw pixel positions cannot be trusted.

## Current validation matrix

The automated matrix now covers:

- 1280x720
- 1366x768
- 1600x900
- 1920x1080
- 2560x1440
- 3840x2160
- 2560x1080 ultrawide letterbox
- 3440x1440 ultrawide letterbox
- 3840x1600 ultrawide letterbox
- windowed capture with OS-like border
- small, JPEG-compressed edge case with fail-safe assertion

## Boundary

This improves resolution tolerance. It does not prove universal recognition for all Dofus clients yet. The remaining proof requires screenshots from independent players, ideally grouped by:

- resolution
- fullscreen/windowed
- UI scale
- graphics quality
- language/client version
- capture method

Each new screenshot should be retained as a fixture only if the player consents.
'''.lstrip()
    write(DOC, doc)


def main() -> None:
    patch_fast_recognition()
    write_tests()
    write_docs()
    print("\nDone. Run: python -m pytest services/api/tests/test_fast_recognition.py services/api/tests/test_resolution_robustness_matrix.py -q")


if __name__ == "__main__":
    main()
