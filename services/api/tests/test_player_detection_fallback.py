from __future__ import annotations

import numpy as np

from grougal_solver import fast_recognition
from grougal_solver.fast_recognition import REFERENCE_BASIS_X, REFERENCE_BASIS_Y, REFERENCE_ORIGIN


def _recognizer_for_unit_test():
    cls = getattr(fast_recognition, "FastRecognitionEngine")
    recognizer = object.__new__(cls)
    # Keep the unit test constructor-free. detect_player only needs this cell
    # list, and using object.__new__ avoids depending on fixture setup.
    recognizer.automatic_object_cells = [(0, 0), (5, 5)]
    return recognizer


def test_player_detector_fallback_accepts_split_low_blue_base() -> None:
    canonical = np.zeros((1267, 1951, 3), dtype=np.uint8)
    cell = (0, 0)
    centre = REFERENCE_ORIGIN + cell[0] * REFERENCE_BASIS_X + cell[1] * REFERENCE_BASIS_Y
    cx, cy = np.rint(centre).astype(int)

    # Sparse blue fragments below the cell centre: too weak for the strict
    # 150-pixel gate, but representative of a partially covered live unit base.
    canonical[cy + 14 : cy + 20, cx - 14 : cx - 4] = (210, 110, 20)
    canonical[cy + 18 : cy + 25, cx + 5 : cx + 14] = (210, 110, 20)

    result = _recognizer_for_unit_test().detect_player(canonical, set())

    assert result is not None
    assert result["cell"] == {"x": 0, "y": 0}
    assert result.get("fallback") is True
    assert result["method"] == "loose_blue_unit_base_cell_sampling"
