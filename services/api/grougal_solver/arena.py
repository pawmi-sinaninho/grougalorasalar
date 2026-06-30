from __future__ import annotations

from pathlib import Path
from typing import Any

from .util import load_json


def _canonical_cells_path(project_root: Path) -> Path:
    return project_root / "data" / "arena" / "grougalorasalar.cells.json"


def arena_given(project_root: Path) -> dict[str, list[dict[str, int]]]:
    canonical_path = _canonical_cells_path(project_root)
    if canonical_path.exists():
        model = load_json(canonical_path)
        unresolved = [
            cell
            for cell in model["cells"]
            if cell.get("boundaryValidation", {}).get("classification") == "unresolved"
        ]
        unresolved_ids = {int(cell["id"]) for cell in unresolved}
        return {
            "walkable": [
                {"x": int(cell["x"]), "y": int(cell["y"])}
                for cell in model["cells"]
                if int(cell["id"]) not in unresolved_ids
            ],
            "boundaryUnverified": [
                {"x": int(cell["x"]), "y": int(cell["y"])} for cell in unresolved
            ],
            "occludedUnknown": [],
            "permanentBlocked": [],
        }

    # Compatibility fallback for archives predating the canonical v0.9.0 mask.
    model = load_json(project_root / "data" / "arena" / "arena-model.draft-v0.5.0.json")
    sets = model["cellSets"]
    return {
        "walkable": sets.get("walkableConfirmed", []) + sets.get("walkableObserved", []),
        "boundaryUnverified": sets.get("boundaryUnverified", []),
        "occludedUnknown": sets.get("occludedUnknown", []),
        "permanentBlocked": model.get("permanentBlockedCells", []),
    }


def reference_transform(project_root: Path) -> dict[str, Any]:
    canonical_path = _canonical_cells_path(project_root)
    if canonical_path.exists():
        model = load_json(canonical_path)
        coordinates = model["coordinateSystem"]
        return {
            "origin": coordinates["originPixel"],
            "basisX": coordinates["basisX"],
            "basisY": coordinates["basisY"],
            "referenceSize": coordinates["referenceSize"],
        }

    model = load_json(project_root / "data" / "arena" / "arena-model.draft-v0.5.0.json")
    coordinates = model["coordinateSystem"]
    return {
        "origin": coordinates["originPixel"],
        "basisX": coordinates["xAxis"]["basisPixel"],
        "basisY": coordinates["yAxis"]["basisPixel"],
        "referenceSize": model["screenshotLayout"]["canonicalReferenceSize"],
    }


def project_cell(transform: dict[str, Any], cell: dict[str, int], image_size: tuple[int, int]) -> tuple[float, float]:
    ref = transform["referenceSize"]
    sx = image_size[0] / ref["width"]
    sy = image_size[1] / ref["height"]
    x = (
        transform["origin"]["x"]
        + cell["x"] * transform["basisX"]["x"]
        + cell["y"] * transform["basisY"]["x"]
    ) * sx
    y = (
        transform["origin"]["y"]
        + cell["x"] * transform["basisX"]["y"]
        + cell["y"] * transform["basisY"]["y"]
    ) * sy
    return x, y
