from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from services.api.grougal_solver.fast_recognition import register_screenshot_to_arena


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def apply_affine(matrix: np.ndarray, points: np.ndarray) -> np.ndarray:
    return points @ matrix[:, :2].T + matrix[:, 2]


def render(project_root: Path, source: Path, output: Path, *, identity: bool = False) -> dict:
    image = cv2.imread(str(source), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"Cannot read {source}")
    if identity:
        matrix = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64)
        registration = {
            "status": "canonical_identity",
            "accepted": True,
            "medianResidualCell": 0.0,
            "p95ResidualCell": 0.0,
            "confidence": 1.0,
            "inlierCount": None,
            "spatialRegionCount": None,
            "reasonCodes": [],
        }
    else:
        result = register_screenshot_to_arena(image, project_root)
        registration = result.public()
        if not result.accepted or result.affine_reference_to_image is None:
            raise RuntimeError(f"Registration failed for {source}: {registration}")
        matrix = result.affine_reference_to_image

    cells = load_json(project_root / "data" / "arena" / "grougalorasalar.cells.json")["cells"]
    overlay = image.copy()
    translucent = image.copy()
    for cell in cells:
        polygon_ref = np.array([[p["x"], p["y"]] for p in cell["referencePolygon"]], dtype=np.float64)
        polygon = np.rint(apply_affine(matrix, polygon_ref)).astype(np.int32)
        center_ref = np.array([[cell["referencePixelCenter"]["x"], cell["referencePixelCenter"]["y"]]], dtype=np.float64)
        center = np.rint(apply_affine(matrix, center_ref)[0]).astype(np.int32)
        colour = (0, 165, 255) if cell["boundary"] else ((50, 230, 50) if cell["parity"] == "light" else (230, 150, 40))
        cv2.polylines(overlay, [polygon], True, colour, 1, cv2.LINE_AA)
        cv2.circle(overlay, tuple(center), 2, colour, -1, cv2.LINE_AA)
        cv2.putText(
            overlay,
            str(cell["id"]),
            (int(center[0] - 7), int(center[1] + 3)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.20,
            colour,
            1,
            cv2.LINE_AA,
        )
        if cell["boundary"]:
            cv2.fillPoly(translucent, [polygon], (0, 180, 255))
    overlay = cv2.addWeighted(translucent, 0.12, overlay, 0.88, 0)
    header = (
        f"cells=338 boundary=50 status={registration['status']} "
        f"median={registration.get('medianResidualCell')}cell p95={registration.get('p95ResidualCell')}cell"
    )
    cv2.rectangle(overlay, (8, 8), (min(image.shape[1] - 8, 970), 44), (0, 0, 0), -1)
    cv2.putText(overlay, header, (18, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), overlay)
    return {
        "source": str(source.relative_to(project_root)),
        "output": str(output.relative_to(project_root)),
        "width": image.shape[1],
        "height": image.shape[0],
        "registration": registration,
    }


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    jobs = [
        (project_root / "assets/reference/user_reference.png", "canonical-reference", True),
        (project_root / "assets/reference/empty_arena.jpeg", "empty-arena", False),
        (project_root / "assets/reference/user_hidden_cells_annotation.png", "user-hidden-cells", False),
        *[
            (project_root / f"packages/fixtures/real/phase7/round-0{index}.png", f"round-0{index}", False)
            for index in range(1, 5)
        ],
    ]
    report = []
    for source, stem, identity in jobs:
        report.append(
            render(
                project_root,
                source,
                project_root / "assets" / "arena" / "validation" / f"{stem}.overlay.png",
                identity=identity,
            )
        )
    report_path = project_root / "reports" / "canonical-arena-registration.v0.9.0.json"
    report_path.write_text(json.dumps({"schemaVersion": "0.9.0", "images": report}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"overlays": len(report), "report": str(report_path)}, indent=2))


if __name__ == "__main__":
    main()
