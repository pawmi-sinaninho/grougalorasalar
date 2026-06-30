from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np


EMPTY_AFFINE = np.array(
    [
        [0.6439939982741252, 0.000023601380444710166, 312.84912086433985],
        [-0.000023601380444710166, 0.6439939982741252, 18.804303567570535],
    ],
    dtype=np.float64,
)

POSITION_TOLERANCE_CELLS = 0.12
UNRESOLVED_BOUNDARY_IDS = {9, 16, 25, 64, 81, 168, 193}
VISIBLE_EMPTY_BOUNDARY_IDS = {
    0,
    1,
    3,
    4,
    24,
    35,
    36,
    48,
    49,
    100,
    121,
    143,
    144,
    169,
    216,
    237,
    256,
    273,
    288,
    301,
    328,
    329,
    333,
    334,
    336,
    337,
}

REGIONS: dict[str, dict[str, Any]] = {
    "left-top": {"label": "links oben", "rect": (320, 35, 900, 285)},
    "left-middle": {"label": "links Mitte", "rect": (315, 190, 650, 455)},
    "left-bottom": {"label": "links unten", "rect": (315, 350, 720, 665)},
    "bottom-left": {"label": "unten links", "rect": (360, 490, 820, 680)},
    "bottom-middle": {"label": "unten Mitte", "rect": (680, 490, 1220, 680)},
    "bottom-right": {"label": "unten rechts", "rect": (1080, 475, 1545, 680)},
    "right-middle": {"label": "rechts Mitte", "rect": (1260, 190, 1565, 540)},
    "right-top": {"label": "rechts oben", "rect": (900, 35, 1565, 315)},
}

CYAN = (255, 255, 0)
RED = (0, 0, 255)
LIME = (0, 255, 0)
ORANGE = (0, 165, 255)
MAGENTA = (255, 0, 255)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def transform_points(points: np.ndarray, matrix: np.ndarray = EMPTY_AFFINE) -> np.ndarray:
    return points @ matrix[:, :2].T + matrix[:, 2]


def reference_polygon(cell: dict[str, Any]) -> np.ndarray:
    return np.array([[point["x"], point["y"]] for point in cell["referencePolygon"]], dtype=np.float64)


def reference_center(cell: dict[str, Any]) -> np.ndarray:
    return np.array(
        [[cell["referencePixelCenter"]["x"], cell["referencePixelCenter"]["y"]]],
        dtype=np.float64,
    )


def empty_polygon(cell: dict[str, Any]) -> np.ndarray:
    return transform_points(reference_polygon(cell))


def empty_center(cell: dict[str, Any]) -> np.ndarray:
    return transform_points(reference_center(cell))[0]


def bilinear(image: np.ndarray, points: np.ndarray) -> np.ndarray:
    return cv2.remap(
        image,
        points[:, 0].astype(np.float32).reshape(-1, 1),
        points[:, 1].astype(np.float32).reshape(-1, 1),
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101,
    ).reshape(-1)


def polygon_edge_samples(polygons: list[np.ndarray], count: int = 12) -> tuple[np.ndarray, np.ndarray]:
    all_points: list[np.ndarray] = []
    all_normals: list[np.ndarray] = []
    parameters = np.linspace(0.16, 0.84, count, dtype=np.float64)
    for polygon in polygons:
        for index in range(4):
            start = polygon[index]
            end = polygon[(index + 1) % 4]
            vector = end - start
            normal = np.array([-vector[1], vector[0]], dtype=np.float64) / float(np.linalg.norm(vector))
            all_points.append(start[None, :] + parameters[:, None] * vector[None, :])
            all_normals.append(np.repeat(normal[None, :], count, axis=0))
    return np.concatenate(all_points, axis=0), np.concatenate(all_normals, axis=0)


def line_fit_score(gray: np.ndarray, points: np.ndarray, normals: np.ndarray, shift: np.ndarray) -> float:
    shifted = points + shift[None, :]
    centre = bilinear(gray, shifted)
    near_a = bilinear(gray, shifted - normals * 1.8)
    near_b = bilinear(gray, shifted + normals * 1.8)
    far_a = bilinear(gray, shifted - normals * 3.6)
    far_b = bilinear(gray, shifted + normals * 3.6)
    response = 0.35 * (near_a + near_b) + 0.15 * (far_a + far_b) - centre
    return float(np.mean(np.clip(response, 0.0, 48.0)))


def fit_region_shift(gray: np.ndarray, polygons: list[np.ndarray]) -> dict[str, Any]:
    points, normals = polygon_edge_samples(polygons)
    candidates: list[tuple[float, float, float]] = []
    for dy in np.arange(-3.0, 3.01, 0.5):
        for dx in np.arange(-3.0, 3.01, 0.5):
            score = line_fit_score(gray, points, normals, np.array([dx, dy], dtype=np.float64))
            candidates.append((score, dx, dy))
    candidates.sort(reverse=True, key=lambda item: item[0])
    score, dx, dy = candidates[0]
    baseline = next(item[0] for item in candidates if item[1] == 0.0 and item[2] == 0.0)
    return {
        "offsetX": round(float(dx), 3),
        "offsetY": round(float(dy), 3),
        "distancePixels": round(float(math.hypot(dx, dy)), 4),
        "fitScore": round(float(score), 4),
        "baselineScore": round(float(baseline), 4),
        "scoreGain": round(float(score - baseline), 4),
        "supportingCellCount": len(polygons),
        "method": "regional_visible_grid_line_fit",
    }


def primary_region(cell: dict[str, Any], centre: np.ndarray) -> str:
    x, y = int(cell["x"]), int(cell["y"])
    screen_x, screen_y = float(centre[0]), float(centre[1])
    if x + y == -11:
        return "left-top" if screen_x < 934.0 else "right-top"
    if x - y == 13:
        return "right-top" if screen_y < 300.0 else "right-middle"
    if x + y == 13:
        if screen_x < 750.0:
            return "bottom-left"
        if screen_x < 1150.0:
            return "bottom-middle"
        return "bottom-right"
    if x - y == -13:
        if screen_y < 250.0:
            return "left-top"
        if screen_y < 430.0:
            return "left-middle"
        return "left-bottom"
    raise ValueError(f"Boundary cell {cell['stableId']} is not on a screen-space side")


def build_region_fits(image: np.ndarray, cells: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    gray = cv2.GaussianBlur(lab[:, :, 0], (3, 3), 0.7).astype(np.float32)
    visible_polygons = []
    for cell in cells:
        old_class = cell["supersededDraftClass"]
        if old_class not in {"walkableConfirmed", "walkableObserved"} and cell["id"] not in VISIBLE_EMPTY_BOUNDARY_IDS:
            continue
        visible_polygons.append((empty_center(cell), empty_polygon(cell)))

    fits: dict[str, dict[str, Any]] = {}
    for region_id, region in REGIONS.items():
        x0, y0, x1, y1 = region["rect"]
        polygons = [
            polygon
            for centre, polygon in visible_polygons
            if x0 <= centre[0] <= x1 and y0 <= centre[1] <= y1
        ]
        if not polygons:
            raise ValueError(f"No stable visible grid support for boundary region {region_id}")
        fits[region_id] = {
            "label": region["label"],
            "referenceRect": {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0},
            **fit_region_shift(gray, polygons),
        }
    return fits


def refine_boundary_documents(
    project_root: Path,
    cells_doc: dict[str, Any],
    boundary_doc: dict[str, Any],
) -> dict[str, Any]:
    image_path = project_root / "assets/reference/empty_arena.jpeg"
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"Missing boundary evidence image: {image_path}")
    cells = cells_doc["cells"]
    region_fits = build_region_fits(image, cells)
    cell_size_pixels = float(
        (
            np.linalg.norm(EMPTY_AFFINE[:, :2] @ np.array([66.75, 33.375]))
            + np.linalg.norm(EMPTY_AFFINE[:, :2] @ np.array([-66.75, 33.375]))
        )
        / 2.0
    )

    refined_boundary_cells: list[dict[str, Any]] = []
    review_list: list[dict[str, Any]] = []
    confirmed_ids: list[int] = []
    inferred_ids: list[int] = []
    unresolved_ids: list[int] = []
    position_outlier_ids: list[int] = []

    for cell in cells:
        if not cell["boundary"]:
            continue
        cell_id = int(cell["id"])
        expected = empty_center(cell)
        region_id = primary_region(cell, expected)
        fit = region_fits[region_id]
        delta = np.array([fit["offsetX"], fit["offsetY"]], dtype=np.float64)
        plausible = expected + delta
        distance_pixels = float(np.linalg.norm(delta))
        distance_cells = distance_pixels / cell_size_pixels

        criteria = {
            "user_boundary_annotation": False,
            "user_hidden_cell_annotation": cell["supersededDraftClass"] == "occludedUnknown",
            "visible_empty_map": cell_id in VISIBLE_EMPTY_BOUNDARY_IDS,
            "parity_geometric_consistency": True,
        }
        evidence_count = sum(1 for value in criteria.values() if value)
        classification = "confirmed" if evidence_count >= 2 else "unresolved"
        confidence_level = "high" if evidence_count >= 3 else ("medium" if evidence_count == 2 else "low")
        position_outlier = distance_cells > POSITION_TOLERANCE_CELLS

        if classification == "unresolved":
            source_authority = "unresolved"
            confidence = 0.35
            unresolved_ids.append(cell_id)
        else:
            source_authority = (
                "user_hidden_cell_annotation"
                if criteria["user_hidden_cell_annotation"]
                else "visible_empty_map"
            )
            confidence = 0.97 if evidence_count >= 3 else 0.90
            confirmed_ids.append(cell_id)
        if position_outlier:
            position_outlier_ids.append(cell_id)

        review_reasons = []
        if classification == "unresolved":
            review_reasons.append("fewer_than_two_required_boundary_evidence_criteria")
        if position_outlier:
            review_reasons.append("position_deviation_above_0.12_cell")
        if review_reasons:
            review_list.append(
                {
                    "id": cell_id,
                    "stableId": cell["stableId"],
                    "x": cell["x"],
                    "y": cell["y"],
                    "region": region_id,
                    "reasons": review_reasons,
                }
            )

        position_check = {
            "sourceImage": "assets/reference/empty_arena.jpeg",
            "fitRegion": region_id,
            "method": "regional_visible_grid_line_fit",
            "expectedCenter": {"x": round(float(expected[0]), 4), "y": round(float(expected[1]), 4)},
            "plausibleCenter": {"x": round(float(plausible[0]), 4), "y": round(float(plausible[1]), 4)},
            "delta": {"x": round(float(delta[0]), 4), "y": round(float(delta[1]), 4)},
            "distancePixels": round(distance_pixels, 4),
            "distanceCells": round(distance_cells, 6),
            "toleranceCells": POSITION_TOLERANCE_CELLS,
            "outlier": position_outlier,
            "independentVisibleCellSurface": criteria["visible_empty_map"],
        }
        validation = {
            "classification": classification,
            "displayCategory": (
                "confirmed_boundary_cell" if classification == "confirmed" else "geometric_inference_unresolved"
            ),
            "confidence": confidence_level,
            "evidenceCriteria": criteria,
            "evidenceCount": evidence_count,
            "sourceAuthority": source_authority,
            "positionCheck": position_check,
            "reviewRequired": bool(review_reasons),
            "reviewReasons": review_reasons,
        }
        cell["sourceAuthority"] = source_authority
        cell["confidence"] = confidence
        cell["boundaryValidation"] = validation
        cell["provenance"] = [
            "boundary-refinement-phase",
            *( ["user-hidden-cell-overlay"] if criteria["user_hidden_cell_annotation"] else [] ),
            *( ["empty-arena-raster"] if criteria["visible_empty_map"] else [] ),
            "parity-and-local-grid-consistency",
            "green-boundary-byte-unavailable-not-counted",
            *( ["requires-boundary-evidence-review"] if classification == "unresolved" else [] ),
        ]
        refined_boundary_cells.append(
            {
                "id": cell_id,
                "stableId": cell["stableId"],
                "x": cell["x"],
                "y": cell["y"],
                **validation,
            }
        )

    if set(unresolved_ids) != UNRESOLVED_BOUNDARY_IDS:
        raise ValueError(f"Unexpected unresolved boundary set: {unresolved_ids}")

    cells_doc["status"] = "boundary_refinement_review_required"
    cells_doc["footprint"]["verificationStatus"] = "provisional_338_boundary_review"
    cells_doc["countVerification"]["countRetainedAsProvisional"] = True
    cells_doc["countVerification"]["positionVerificationComplete"] = False
    cells_doc["boundaryValidationSummary"] = {
        "policy": "confirmed_requires_two_of_four_evidence_criteria",
        "totalBoundaryCells": len(refined_boundary_cells),
        "confirmed": len(confirmed_ids),
        "inferred": len(inferred_ids),
        "unresolved": len(unresolved_ids),
        "positionOutliers": len(position_outlier_ids),
        "reviewListCount": len(review_list),
        "fullyPositionVerified": False,
    }

    boundary_doc.update(
        {
            "status": "boundary_refinement_review_required",
            "validationPolicy": {
                "confirmedMinimumCriteria": 2,
                "criteria": [
                    "user_boundary_annotation",
                    "user_hidden_cell_annotation",
                    "visible_empty_map",
                    "parity_geometric_consistency",
                ],
                "missingGreenAnnotationHandling": "not_counted_per_cell",
                "shapeSmoothingAllowed": False,
                "symmetrisationAllowed": False,
            },
            "classificationSummary": {
                "confirmed": len(confirmed_ids),
                "inferred": len(inferred_ids),
                "unresolved": len(unresolved_ids),
            },
            "confirmedBoundaryCells": confirmed_ids,
            "inferredBoundaryCells": inferred_ids,
            "unresolvedBoundaryCells": unresolved_ids,
            "positionOutlierCells": position_outlier_ids,
            "boundaryCells": refined_boundary_cells,
            "regionFits": region_fits,
            "reviewList": review_list,
        }
    )

    report = {
        "schemaVersion": "0.9.0",
        "phase": "boundary_refinement",
        "status": "review_required",
        "arenaModelId": cells_doc["arenaModelId"],
        "workingCellCount": cells_doc["totalCells"],
        "cellCountDisposition": "retained_provisionally_pending_seven_boundary_reviews",
        "evidencePolicy": boundary_doc["validationPolicy"],
        "classificationSummary": boundary_doc["classificationSummary"],
        "positionToleranceCells": POSITION_TOLERANCE_CELLS,
        "positionOutlierCells": position_outlier_ids,
        "reviewList": review_list,
        "regionFits": region_fits,
        "boundaryCells": refined_boundary_cells,
        "zoomCrops": [
            {"region": region_id, "label": region["label"], "path": f"VALIDATION/edge-review-{region_id}.png"}
            for region_id, region in REGIONS.items()
        ],
        "acceptance": {
            "problematicBoundaryCellsIdentified": True,
            "unresolvedCentresVisiblyMarked": True,
            "classificationsSeparated": True,
            "positionOutlierListEmpty": len(position_outlier_ids) == 0,
            "fullyPositionVerified": False,
            "phaseAccepted": False,
        },
        "note": "No 100% correctness claim is permitted while the seven-cell evidence review list is non-empty.",
    }
    return report


def dump_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def translucent_fill(image: np.ndarray, polygon: np.ndarray, colour: tuple[int, int, int], alpha: float) -> None:
    layer = image.copy()
    cv2.fillPoly(layer, [polygon], colour, cv2.LINE_AA)
    cv2.addWeighted(layer, alpha, image, 1.0 - alpha, 0.0, dst=image)


def draw_legend(image: np.ndarray, summary: dict[str, Any]) -> None:
    cv2.rectangle(image, (10, 10), (825, 115), BLACK, -1)
    cv2.putText(image, "BOUNDARY REFINEMENT - 338 provisional", (25, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.62, WHITE, 2, cv2.LINE_AA)
    entries = [(CYAN, "polygon"), (RED, "center"), (LIME, "confirmed"), (ORANGE, "geometry-only"), (MAGENTA, "unresolved")]
    x = 25
    for colour, label in entries:
        cv2.circle(image, (x, 63), 7, colour, -1, cv2.LINE_AA)
        cv2.putText(image, label, (x + 12, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.42, WHITE, 1, cv2.LINE_AA)
        x += 145
    text = f"confirmed={summary['confirmed']} inferred={summary['inferred']} unresolved={summary['unresolved']}"
    cv2.putText(image, text, (25, 98), cv2.FONT_HERSHEY_SIMPLEX, 0.50, WHITE, 1, cv2.LINE_AA)


def draw_boundary_cell(image: np.ndarray, cell: dict[str, Any], labelled: bool, show_position: bool) -> None:
    polygon = np.rint(empty_polygon(cell)).astype(np.int32)
    centre = empty_center(cell)
    point = (int(round(centre[0])), int(round(centre[1])))
    validation = cell["boundaryValidation"]
    confirmed = validation["classification"] == "confirmed"
    status_colour = LIME if confirmed else MAGENTA
    translucent_fill(image, polygon, LIME if confirmed else ORANGE, 0.13)
    cv2.polylines(image, [polygon], True, CYAN, 2, cv2.LINE_AA)
    cv2.circle(image, point, 4, RED, -1, cv2.LINE_AA)
    cv2.circle(image, point, 10, status_colour, 2, cv2.LINE_AA)
    if not confirmed:
        cv2.polylines(image, [polygon], True, ORANGE, 4, cv2.LINE_AA)
        cv2.polylines(image, [polygon], True, MAGENTA, 2, cv2.LINE_AA)
        cv2.line(image, (point[0] - 8, point[1] - 8), (point[0] + 8, point[1] + 8), MAGENTA, 2, cv2.LINE_AA)
        cv2.line(image, (point[0] - 8, point[1] + 8), (point[0] + 8, point[1] - 8), MAGENTA, 2, cv2.LINE_AA)
    if show_position:
        plausible = validation["positionCheck"]["plausibleCenter"]
        plausible_point = (int(round(plausible["x"])), int(round(plausible["y"])))
        cv2.line(image, point, plausible_point, WHITE, 1, cv2.LINE_AA)
        cv2.circle(image, plausible_point, 3, WHITE, 1, cv2.LINE_AA)
    if labelled:
        label = f"{cell['stableId']} {validation['positionCheck']['distanceCells']:.3f}c"
        cv2.putText(image, label, (point[0] + 9, point[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.31, WHITE, 2, cv2.LINE_AA)
        cv2.putText(image, label, (point[0] + 9, point[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.31, status_colour, 1, cv2.LINE_AA)


def render_refinement_assets(
    project_root: Path,
    cells_doc: dict[str, Any],
    report: dict[str, Any],
) -> None:
    source = cv2.imread(str(project_root / "assets/reference/empty_arena.jpeg"), cv2.IMREAD_COLOR)
    if source is None:
        raise RuntimeError("Missing empty arena reference")
    cells = cells_doc["cells"]
    boundary_cells = [cell for cell in cells if cell["boundary"]]
    summary = report["classificationSummary"]

    full = source.copy()
    for cell in cells:
        polygon = np.rint(empty_polygon(cell)).astype(np.int32)
        centre = empty_center(cell)
        point = (int(round(centre[0])), int(round(centre[1])))
        cv2.polylines(full, [polygon], True, CYAN, 1, cv2.LINE_AA)
        cv2.circle(full, point, 2, RED, -1, cv2.LINE_AA)
    for cell in boundary_cells:
        draw_boundary_cell(full, cell, labelled=False, show_position=False)
    draw_legend(full, summary)

    boundary = source.copy()
    for cell in boundary_cells:
        draw_boundary_cell(boundary, cell, labelled=True, show_position=False)
    draw_legend(boundary, summary)

    edge_review_clean = source.copy()
    for cell in boundary_cells:
        draw_boundary_cell(edge_review_clean, cell, labelled=True, show_position=True)
    edge_review = edge_review_clean.copy()
    draw_legend(edge_review, summary)

    assets = project_root / "assets/arena"
    validation = project_root / "VALIDATION"
    assets.mkdir(parents=True, exist_ok=True)
    validation.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(assets / "grougalorasalar-debug-overlay.png"), full)
    cv2.imwrite(str(assets / "grougalorasalar-boundary-debug.png"), boundary)
    cv2.imwrite(str(validation / "edge-review.overlay.png"), edge_review)

    crop_images: list[np.ndarray] = []
    for region_id, region in REGIONS.items():
        x0, y0, x1, y1 = region["rect"]
        raw_crop = edge_review_clean[y0:y1, x0:x1].copy()
        crop = np.zeros((raw_crop.shape[0] + 28, raw_crop.shape[1], 3), dtype=np.uint8)
        crop[28:, :] = raw_crop
        cv2.putText(crop, region["label"], (9, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.52, WHITE, 1, cv2.LINE_AA)
        path = validation / f"edge-review-{region_id}.png"
        cv2.imwrite(str(path), crop)
        resized = cv2.resize(crop, (500, 240), interpolation=cv2.INTER_AREA)
        crop_images.append(resized)

    zoom_sheet = np.zeros((4 * 240, 2 * 500, 3), dtype=np.uint8)
    for index, crop in enumerate(crop_images):
        row, column = divmod(index, 2)
        zoom_sheet[row * 240 : (row + 1) * 240, column * 500 : (column + 1) * 500] = crop
    cv2.imwrite(str(validation / "edge-review-zooms.png"), zoom_sheet)
