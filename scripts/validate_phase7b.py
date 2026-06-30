from __future__ import annotations

import json
import subprocess

import jsonschema
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(path: str) -> Path:
    target = ROOT / path
    if not target.exists():
        raise AssertionError(f"Missing required artefact: {path}")
    return target


def main() -> None:
    required = [
        "data/arena/grougalorasalar.cells.json",
        "data/arena/grougalorasalar.cells.csv",
        "data/arena/grougalorasalar.boundary.json",
        "data/arena/grougalorasalar.registration.json",
        "data/arena/grougalorasalar.landmarks.json",
        "schemas/canonical-arena-cells.schema.json",
        "schemas/canonical-arena-boundary.schema.json",
        "assets/arena/grougalorasalar-mask.svg",
        "assets/arena/grougalorasalar-mask.png",
        "assets/arena/grougalorasalar-cell-centers.png",
        "assets/arena/grougalorasalar-cell-polygons.png",
        "assets/arena/grougalorasalar-debug-overlay.png",
        "assets/arena/grougalorasalar-boundary-debug.png",
        "VALIDATION/edge-review.overlay.png",
        "VALIDATION/edge-review-report.json",
        "VALIDATION/edge-review-zooms.png",
        "reports/canonical-arena-registration.v0.9.0.json",
        "docs/arena/CANONICAL_ARENA_MASK.md",
        "docs/testing/PHASE_7B_CANONICAL_MASK_REPORT.md",
    ]
    for path in required:
        require(path)

    cells_doc = json.loads(require("data/arena/grougalorasalar.cells.json").read_text(encoding="utf-8"))
    cells_schema = json.loads(require("schemas/canonical-arena-cells.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(cells_schema).validate(cells_doc)
    assert cells_doc["totalCells"] == 338
    assert cells_doc["countVerification"]["allMethodsAgree"] is True
    assert len(cells_doc["cells"]) == 338
    boundary_cells = [cell for cell in cells_doc["cells"] if cell["boundary"]]
    unresolved = [cell for cell in boundary_cells if cell["boundaryValidation"]["classification"] == "unresolved"]
    confirmed = [cell for cell in boundary_cells if cell["boundaryValidation"]["classification"] == "confirmed"]
    assert len(confirmed) == 43
    assert [cell["id"] for cell in unresolved] == [9, 16, 25, 64, 81, 168, 193]
    assert all(cell["sourceAuthority"] == "unresolved" for cell in unresolved)
    assert all(cell["confidence"] == 0.35 for cell in unresolved)
    assert all(cell["boundaryValidation"]["confidence"] == "low" for cell in unresolved)
    assert all(cell["boundaryValidation"]["evidenceCount"] < 2 for cell in unresolved)
    assert all(cell["boundaryValidation"]["evidenceCount"] >= 2 for cell in confirmed)

    boundary = json.loads(require("data/arena/grougalorasalar.boundary.json").read_text(encoding="utf-8"))
    boundary_schema = json.loads(require("schemas/canonical-arena-boundary.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(boundary_schema).validate(boundary)
    assert boundary["totalBoundaryCells"] == 50
    assert boundary["totalBoundaryEdges"] == 104
    assert boundary["holes"] == []
    assert boundary["classificationSummary"] == {"confirmed": 43, "inferred": 0, "unresolved": 7}
    assert boundary["positionOutlierCells"] == []
    assert len(boundary["reviewList"]) == 7

    edge_report = json.loads(require("VALIDATION/edge-review-report.json").read_text(encoding="utf-8"))
    assert edge_report["workingCellCount"] == 338
    assert edge_report["acceptance"]["phaseAccepted"] is False
    assert edge_report["acceptance"]["fullyPositionVerified"] is False
    assert edge_report["positionOutlierCells"] == []
    assert len(edge_report["reviewList"]) == 7

    registration = json.loads(require("reports/canonical-arena-registration.v0.9.0.json").read_text(encoding="utf-8"))
    assert len(registration["images"]) == 7
    for image in registration["images"]:
        assert image["registration"]["accepted"] is True
        p95 = image["registration"].get("p95ResidualCell")
        assert p95 is not None and p95 <= 0.10

    generated_paths = [
        ROOT / "data/arena/grougalorasalar.cells.json",
        ROOT / "data/arena/grougalorasalar.cells.csv",
        ROOT / "data/arena/grougalorasalar.boundary.json",
        ROOT / "data/arena/grougalorasalar.registration.json",
        ROOT / "data/arena/grougalorasalar.landmarks.json",
        ROOT / "assets/arena/grougalorasalar-mask.svg",
        ROOT / "assets/arena/grougalorasalar-mask.png",
        ROOT / "assets/arena/grougalorasalar-cell-centers.png",
        ROOT / "assets/arena/grougalorasalar-cell-polygons.png",
        ROOT / "assets/arena/grougalorasalar-debug-overlay.png",
        ROOT / "assets/arena/grougalorasalar-boundary-debug.png",
        ROOT / "VALIDATION/edge-review.overlay.png",
        ROOT / "VALIDATION/edge-review-report.json",
        ROOT / "VALIDATION/edge-review-zooms.png",
        *[ROOT / f"VALIDATION/edge-review-{region}.png" for region in [
            "left-top", "left-middle", "left-bottom", "bottom-left",
            "bottom-middle", "bottom-right", "right-middle", "right-top",
        ]],
    ]
    before = {path: path.read_bytes() for path in generated_paths}
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_canonical_arena.py"), "--project-root", str(ROOT)],
        check=True,
    )
    for path in generated_paths:
        assert path.read_bytes() == before[path], f"Non-deterministic generated artefact: {path.relative_to(ROOT)}"
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_canonical_arena.py"), "--check", "--project-root", str(ROOT)],
        check=True,
    )
    print("Phase 7B boundary-refinement validation passed with seven explicitly unresolved cells.")


if __name__ == "__main__":
    main()
