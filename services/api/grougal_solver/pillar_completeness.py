from __future__ import annotations

from typing import Iterable

import cv2
import numpy as np


def scan_pillar_completeness(
    canonical: np.ndarray,
    neutral: np.ndarray,
    cells: Iterable[tuple[int, int]],
    detected_cells: set[tuple[int, int]],
    origin: np.ndarray,
    basis_x: np.ndarray,
    basis_y: np.ndarray,
) -> dict:
    """Cross-check the component detector with an independent per-cell scan."""
    scores: list[dict] = []
    possible_missing: list[dict[str, int]] = []
    for cell in cells:
        centre = origin + cell[0] * basis_x + cell[1] * basis_y
        cx, cy = np.rint(centre).astype(int)
        # Pillar icon and pedestal occupy the region above the logical anchor.
        y0, y1 = cy - 82, cy + 8
        x0, x1 = cx - 34, cx + 35
        if y0 < 0 or x0 < 0 or y1 > canonical.shape[0] or x1 > canonical.shape[1]:
            continue
        current = canonical[y0:y1, x0:x1]
        background = neutral[y0:y1, x0:x1]
        current_lab = cv2.cvtColor(current, cv2.COLOR_BGR2LAB).astype(np.float32)
        background_lab = cv2.cvtColor(background, cv2.COLOR_BGR2LAB).astype(np.float32)
        delta_e = np.linalg.norm(current_lab - background_lab, axis=2)
        edge_current = cv2.Canny(current, 70, 150)
        edge_background = cv2.Canny(background, 70, 150)
        change = float(np.mean(delta_e > 24.0))
        edge_gain = float(np.mean(edge_current > edge_background))
        score = 0.72 * change + 0.28 * edge_gain
        scores.append({"cell": {"x": cell[0], "y": cell[1]}, "objectScore": round(score, 6)})
        if cell not in detected_cells and score >= 0.72:
            possible_missing.append({"x": cell[0], "y": cell[1]})
    confidence = max(0.0, 0.93 - 0.18 * len(possible_missing))
    return {
        "detectedPillarCells": [{"x": x, "y": y} for x, y in sorted(detected_cells)],
        "possibleMissingPillars": possible_missing[:4],
        "possibleFalsePositives": [],
        "pillarSetCompletenessConfidence": round(confidence, 6),
        "method": "neutral_background_cell_structure_scan_v1",
        "cellScores": scores,
    }
