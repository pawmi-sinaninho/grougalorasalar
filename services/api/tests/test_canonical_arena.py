from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import cv2
import pytest

from grougal_solver.arena import arena_given, reference_transform
from grougal_solver.fast_recognition import (
    get_fast_engine,
    registerScreenshotToArena,
    register_screenshot_to_arena,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CELLS_PATH = PROJECT_ROOT / "data" / "arena" / "grougalorasalar.cells.json"
BOUNDARY_PATH = PROJECT_ROOT / "data" / "arena" / "grougalorasalar.boundary.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_canonical_cell_count_is_independently_reproducible() -> None:
    document = load(CELLS_PATH)
    cells = document["cells"]
    coordinates = {(cell["x"], cell["y"]) for cell in cells}
    assert document["totalCells"] == 338
    assert len(cells) == len(coordinates) == 338

    by_sum = Counter(x + y for x, y in coordinates)
    by_difference = Counter(x - y for x, y in coordinates)
    assert sum(by_sum.values()) == 338
    assert sum(by_difference.values()) == 338
    assert {str(key): value for key, value in sorted(by_sum.items())} == document["countVerification"]["byXPlusY"]
    assert {str(key): value for key, value in sorted(by_difference.items())} == document["countVerification"]["byXMinusY"]
    assert document["countVerification"]["allMethodsAgree"] is True


def test_canonical_footprint_matches_integer_inequalities() -> None:
    cells = load(CELLS_PATH)["cells"]
    actual = {(cell["x"], cell["y"]) for cell in cells}
    expected = {
        (x, y)
        for x in range(-12, 14)
        for y in range(-12, 14)
        if -11 <= x + y <= 13 and -13 <= x - y <= 13
    }
    assert actual == expected


def test_ids_are_stable_and_sorted_by_y_then_x() -> None:
    cells = load(CELLS_PATH)["cells"]
    assert [cell["id"] for cell in cells] == list(range(338))
    assert [(cell["y"], cell["x"]) for cell in cells] == sorted((cell["y"], cell["x"]) for cell in cells)
    assert [cell["stableId"] for cell in cells] == [f"C{index:03d}" for index in range(338)]


def test_every_neighbor_flips_parity_and_is_reciprocal() -> None:
    cells = load(CELLS_PATH)["cells"]
    by_id = {cell["id"]: cell for cell in cells}
    by_coordinate = {(cell["x"], cell["y"]): cell for cell in cells}
    for cell in cells:
        expected_parity = "light" if (cell["x"] + cell["y"]) % 2 == 0 else "dark"
        assert cell["parity"] == expected_parity
        for neighbor in cell["neighbors"]:
            other = by_id[neighbor["id"]]
            assert (other["x"], other["y"]) == (neighbor["x"], neighbor["y"])
            assert other["parity"] != cell["parity"]
            assert any(back["id"] == cell["id"] for back in other["neighbors"])
            assert by_coordinate[(neighbor["x"], neighbor["y"])]["id"] == neighbor["id"]


def test_boundary_authority_follows_refinement_evidence_gate() -> None:
    cells = load(CELLS_PATH)["cells"]
    allowed = {
        "visible_empty_map",
        "visible_combat_screenshot",
        "user_boundary_annotation",
        "user_hidden_cell_annotation",
        "geometric_inference",
        "parity_inference",
        "unresolved",
    }
    for cell in cells:
        assert cell["sourceAuthority"] in allowed
        if cell["boundary"]:
            validation = cell["boundaryValidation"]
            if validation["classification"] == "confirmed":
                assert validation["evidenceCount"] >= 2
                assert validation["confidence"] in {"medium", "high"}
                assert cell["sourceAuthority"] != "unresolved"
            else:
                assert validation["classification"] == "unresolved"
                assert validation["evidenceCount"] < 2
                assert validation["confidence"] == "low"
                assert cell["sourceAuthority"] == "unresolved"
                assert cell["confidence"] == 0.35
        else:
            assert cell["sourceAuthority"] != "unresolved"
        assert len(cell["referencePolygon"]) == 4
        assert 0 <= cell["referencePixelCenter"]["x"] <= 1951
        assert 0 <= cell["referencePixelCenter"]["y"] <= 1267


def test_boundary_is_one_hole_free_cycle() -> None:
    boundary = load(BOUNDARY_PATH)
    assert boundary["totalBoundaryCells"] == 50
    assert boundary["totalBoundaryEdges"] == 104
    assert boundary["holes"] == []
    assert boundary["classificationSummary"] == {"confirmed": 43, "inferred": 0, "unresolved": 7}
    assert boundary["unresolvedBoundaryCells"] == [9, 16, 25, 64, 81, 168, 193]
    assert boundary["positionOutlierCells"] == []
    vertices = boundary["exteriorLogicalVertices"]
    assert len(vertices) == 105
    assert vertices[0] == vertices[-1]


def test_csv_and_derived_assets_match_canonical_json() -> None:
    with (PROJECT_ROOT / "data" / "arena" / "grougalorasalar.cells.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 338
    for relative in [
        "assets/arena/grougalorasalar-mask.svg",
        "assets/arena/grougalorasalar-mask.png",
        "assets/arena/grougalorasalar-cell-centers.png",
        "assets/arena/grougalorasalar-cell-polygons.png",
        "assets/arena/grougalorasalar-debug-overlay.png",
        "assets/arena/grougalorasalar-boundary-debug.png",
    ]:
        assert (PROJECT_ROOT / relative).is_file()


def test_runtime_projects_338_cells_but_does_not_silently_accept_unresolved_boundary() -> None:
    arena = arena_given(PROJECT_ROOT)
    assert len(arena["walkable"]) == 331
    assert len(arena["boundaryUnverified"]) == 7
    assert arena["occludedUnknown"] == []
    transform = reference_transform(PROJECT_ROOT)
    assert transform["referenceSize"] == {"width": 1951, "height": 1267}
    assert len(get_fast_engine(PROJECT_ROOT).candidate_cells) == 338


@pytest.mark.parametrize(
    "relative_path",
    [
        "assets/reference/empty_arena.jpeg",
        "assets/reference/user_hidden_cells_annotation.png",
        "packages/fixtures/real/phase7/round-01.png",
        "packages/fixtures/real/phase7/round-02.png",
        "packages/fixtures/real/phase7/round-03.png",
        "packages/fixtures/real/phase7/round-04.png",
    ],
)
def test_canonical_mask_registers_to_all_real_evidence(relative_path: str) -> None:
    source = PROJECT_ROOT / relative_path
    image = cv2.imread(str(source), cv2.IMREAD_COLOR)
    assert image is not None
    result = register_screenshot_to_arena(image, PROJECT_ROOT)
    assert result.accepted, result.public()
    assert result.p95_residual_cell is not None
    assert result.p95_residual_cell <= 0.10
    alias = registerScreenshotToArena(image, PROJECT_ROOT)
    assert alias.accepted
