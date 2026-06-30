from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

import cv2
import numpy as np

from services.api.grougal_solver.fast_recognition import get_fast_engine


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * p))))
    return ordered[index]


def summary(values: list[float]) -> dict[str, float | int]:
    return {
        "samples": len(values),
        "medianMs": round(statistics.median(values), 3),
        "p95Ms": round(percentile(values, 0.95), 3),
        "maxMs": round(max(values), 3),
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    engine = get_fast_engine(root)
    cells = json.loads((root / "data/arena/grougalorasalar.cells.json").read_text(encoding="utf-8"))["cells"]
    logical = np.array([[cell["x"], cell["y"]] for cell in cells], dtype=np.float64)
    paths = [
        root / "assets/reference/empty_arena.jpeg",
        root / "assets/reference/user_hidden_cells_annotation.png",
        *[root / f"packages/fixtures/real/phase7/round-0{i}.png" for i in range(1, 5)],
    ]
    images = [cv2.imread(str(path), cv2.IMREAD_COLOR) for path in paths]
    assert all(image is not None for image in images)
    grays = [cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) for image in images]

    # One warm-up across all image variants.
    for image in images:
        assert engine.register(image).accepted

    registration_ms: list[float] = []
    projection_ms: list[float] = []
    sampling_ms: list[float] = []
    total_ms: list[float] = []
    for image, gray in zip(images, grays):
        for _ in range(4):
            total_start = time.perf_counter()
            start = time.perf_counter()
            registration = engine.register(image)
            registration_ms.append((time.perf_counter() - start) * 1000)
            assert registration.accepted
            origin = np.array(registration.origin_image, dtype=np.float64)
            basis = np.column_stack(
                [np.array(registration.basis_x_image), np.array(registration.basis_y_image)]
            )
            start = time.perf_counter()
            centres = logical @ basis.T + origin
            projection_ms.append((time.perf_counter() - start) * 1000)
            start = time.perf_counter()
            rounded = np.rint(centres).astype(np.int32)
            valid = (
                (rounded[:, 0] >= 0)
                & (rounded[:, 0] < gray.shape[1])
                & (rounded[:, 1] >= 0)
                & (rounded[:, 1] < gray.shape[0])
            )
            sampled = gray[rounded[valid, 1], rounded[valid, 0]]
            assert sampled.size > 0
            sampling_ms.append((time.perf_counter() - start) * 1000)
            total_ms.append((time.perf_counter() - total_start) * 1000)

    report = {
        "schemaVersion": "0.9.0",
        "environment": "shared_container_warm_process_opencv_threads_4",
        "engineeringTargets": {
            "registrationP95MsMax": 400,
            "projectionAllCellsMsMax": 20,
            "cellSamplingP95MsMax": 500,
            "totalFastPathP95MsMax": 1200,
        },
        "results": {
            "registration": summary(registration_ms),
            "projection338Centres": summary(projection_ms),
            "basicCellSampling": summary(sampling_ms),
            "registrationProjectionSampling": summary(total_ms),
        },
        "targetStatus": {},
        "claims": "Engineering sample only; not supported-browser or clean-machine validation.",
    }
    report["targetStatus"] = {
        "registration": report["results"]["registration"]["p95Ms"] <= 400,
        "projection338Centres": report["results"]["projection338Centres"]["p95Ms"] <= 20,
        "basicCellSampling": report["results"]["basicCellSampling"]["p95Ms"] <= 500,
        "registrationProjectionSampling": report["results"]["registrationProjectionSampling"]["p95Ms"] <= 1200,
    }
    output = root / "reports/performance-canonical-arena-v0.9.0.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
