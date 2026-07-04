from __future__ import annotations

import hashlib
import math
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .glyph_features import build_template, patch_features
from .pillar_completeness import scan_pillar_completeness
from .util import load_json


REFERENCE_ORIGIN = np.array([964.895, 441.7425], dtype=np.float64)
REFERENCE_BASIS_X = np.array([66.75, 33.375], dtype=np.float64)
REFERENCE_BASIS_Y = np.array([-66.75, 33.375], dtype=np.float64)
REFERENCE_BASIS = np.column_stack([REFERENCE_BASIS_X, REFERENCE_BASIS_Y])
REFERENCE_BASIS_INV = np.linalg.inv(REFERENCE_BASIS)
WORK_MIN_WIDTH = 960
WORK_MAX_WIDTH = 1280
CANONICAL_BOARD_BOTTOM = 880
CHARGE_TRACK_CENTRES = {
    "indecision": ((150, 1110), (225, 1070), (300, 1030), (370, 990), (440, 950)),
    "reflection": ((400, 1110), (470, 1070), (545, 1030), (620, 995), (695, 960)),
    "repulsion": ((1500, 1110), (1430, 1070), (1360, 1030), (1290, 990), (1220, 950)),
    "attraction": ((1765, 1110), (1700, 1070), (1630, 1030), (1560, 990), (1495, 950)),
}

INNER_CARDINAL = frozenset({(-1, 0), (0, -1), (0, 1), (1, 0)})
INNER_DIAGONAL = frozenset({(-1, -1), (-1, 1), (1, -1), (1, 1)})
OUTER_CARDINAL = frozenset(
    {(-3, 0), (-2, 0), (0, -3), (0, -2), (0, 2), (0, 3), (2, 0), (3, 0)}
)
OUTER_DIAGONAL = frozenset(
    {(-3, -3), (-3, 3), (-2, -2), (-2, 2), (2, -2), (2, 2), (3, -3), (3, 3)}
)
GLYPH_TEMPLATES = (
    ("inner-cardinal", INNER_CARDINAL, INNER_DIAGONAL),
    ("inner-diagonal", INNER_DIAGONAL, OUTER_CARDINAL),
    ("outer-cardinal", OUTER_CARDINAL, OUTER_DIAGONAL),
    ("outer-diagonal", OUTER_DIAGONAL, INNER_CARDINAL),
)


@dataclass(frozen=True)
class RegistrationResult:
    accepted: bool
    status: str
    affine_reference_to_image: np.ndarray | None
    affine_image_to_reference: np.ndarray | None
    origin_image: tuple[float, float] | None
    basis_x_image: tuple[float, float] | None
    basis_y_image: tuple[float, float] | None
    inlier_count: int
    good_match_count: int
    region_count: int
    median_residual_cell: float | None
    p95_residual_cell: float | None
    ambiguity_margin: float | None
    confidence: float
    reason_codes: tuple[str, ...]

    def public(self) -> dict[str, Any]:
        matrix = self.affine_reference_to_image.tolist() if self.affine_reference_to_image is not None else None
        inverse = self.affine_image_to_reference.tolist() if self.affine_image_to_reference is not None else None
        return {
            "status": self.status,
            "accepted": self.accepted,
            "referenceToImageAffine": matrix,
            "imageToReferenceAffine": inverse,
            "originImage": _point(self.origin_image),
            "basisXImage": _point(self.basis_x_image),
            "basisYImage": _point(self.basis_y_image),
            "inlierCount": self.inlier_count,
            "goodMatchCount": self.good_match_count,
            "spatialRegionCount": self.region_count,
            "medianResidualCell": self.median_residual_cell,
            "p95ResidualCell": self.p95_residual_cell,
            "ambiguityMargin": self.ambiguity_margin,
            "confidence": self.confidence,
            "reasonCodes": list(self.reason_codes),
        }


class FastRecognitionEngine:
    """Cached deterministic vision path for the fixed Grougalorasalar arena.

    The engine intentionally contains no OCR and no generative model. It registers
    the fixed arena, warps to the canonical reference coordinate system and samples
    only known logical cells.
    """

    def __init__(self, project_root: Path):
        started = time.perf_counter()
        # OpenCV's automatic thread choice was materially slower and less stable
        # on shared/container CPUs. A small bounded pool keeps registration within
        # the product latency budget without spawning per-request workers.
        cv2.setNumThreads(min(4, max(1, os.cpu_count() or 1)))
        self.project_root = project_root
        self.reference_path = project_root / "assets" / "reference" / "user_reference.png"
        reference = cv2.imread(str(self.reference_path), cv2.IMREAD_COLOR)
        if reference is None:
            raise RuntimeError(f"Reference image cannot be read: {self.reference_path}")
        self.reference = reference
        self.reference_height, self.reference_width = reference.shape[:2]
        self._orb = cv2.ORB_create(
            nfeatures=5000,
            scaleFactor=1.2,
            nlevels=8,
            edgeThreshold=19,
            fastThreshold=10,
        )
        self._matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
        self._reference_work, self._reference_scale = self._working_gray(reference)
        self._reference_keypoints, self._reference_descriptors = self._orb.detectAndCompute(
            self._reference_work, None
        )
        if self._reference_descriptors is None or len(self._reference_keypoints) < 100:
            raise RuntimeError("Reference ORB feature cache is insufficient")

        canonical_cells_path = project_root / "data" / "arena" / "grougalorasalar.cells.json"
        if canonical_cells_path.exists():
            arena = load_json(canonical_cells_path)
            cells = arena["cells"]
        else:
            arena = load_json(project_root / "data" / "arena" / "arena-model.draft-v0.5.0.json")
            sets = arena["cellSets"]
            cells = (
                sets.get("walkableConfirmed", [])
                + sets.get("walkableObserved", [])
                + sets.get("boundaryUnverified", [])
            )
        self.candidate_cells = sorted(
            {(int(cell["x"]), int(cell["y"])) for cell in cells},
            key=lambda cell: (cell[0] + cell[1], cell[0], cell[1]),
        )
        self.candidate_cell_set = set(self.candidate_cells)
        if canonical_cells_path.exists():
            self.automatic_object_cells = sorted(
                {
                    (int(cell["x"]), int(cell["y"]))
                    for cell in cells
                    if cell.get("occlusion") != "architecture_or_foreground"
                },
                key=lambda cell: (cell[0] + cell[1], cell[0], cell[1]),
            )
        else:
            self.automatic_object_cells = list(self.candidate_cells)
        self.automatic_object_cell_set = set(self.automatic_object_cells)

        empty_path = project_root / "assets" / "reference" / "empty_arena.jpeg"
        empty = cv2.imread(str(empty_path), cv2.IMREAD_COLOR)
        empty_registration = self.register(empty) if empty is not None else None
        if empty_registration and empty_registration.accepted and empty_registration.affine_image_to_reference is not None:
            self.neutral_reference = cv2.warpAffine(
                empty,
                empty_registration.affine_image_to_reference,
                (self.reference_width, self.reference_height),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REPLICATE,
            )
        else:
            self.neutral_reference = self.reference.copy()
        self._black_glyph_template, self._white_glyph_template = self._build_glyph_templates()

        self.fixture_catalog = load_json(project_root / "data" / "vision" / "real-screenshot-fixtures.v0.8.0.json")
        self.glyph_appearance = load_json(
            project_root / "data" / "vision" / "glyph-appearance-reference.v1.0.0.json"
        )
        self._fixture_by_hash = {
            fixture["source"]["sha256"]: fixture for fixture in self.fixture_catalog["fixtures"]
        }
        self._fixture_fingerprints: list[tuple[dict[str, Any], np.ndarray]] = []
        self._build_fixture_fingerprints()
        self.initialisation_ms = _ms(started)

    def recognise(self, image_path: Path, *, source_sha256: str | None = None) -> dict[str, Any]:
        total_started = time.perf_counter()
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            return self._failure("VISION-DECODE-FAILED", total_started)

        registration_started = time.perf_counter()
        registration = self.register(image)
        registration_ms = _ms(registration_started)
        if not registration.accepted or registration.affine_image_to_reference is None:
            return {
                "status": "manual_registration_required",
                "registration": registration.public(),
                "player": None,
                "pillars": [],
                "glyphPattern": None,
                "matchedFixtureId": None,
                "metrics": {
                    "path": "server_fast_fallback",
                    "registrationMs": registration_ms,
                    "canonicalWarpMs": 0.0,
                    "cellSamplingMs": 0.0,
                    "fixtureMatchMs": 0.0,
                    "totalRecognitionMs": _ms(total_started),
                    "ocrInvoked": False,
                    "templatesReloaded": False,
                },
            }

        warp_started = time.perf_counter()
        canonical = cv2.warpAffine(
            image,
            registration.affine_image_to_reference,
            (self.reference_width, self.reference_height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )
        warp_ms = _ms(warp_started)

        sampling_started = time.perf_counter()
        pillar_started = time.perf_counter()
        pillars = self.detect_pillars(canonical)
        completeness = scan_pillar_completeness(
            canonical,
            self.neutral_reference,
            self.automatic_object_cells,
            {(int(item["cell"]["x"]), int(item["cell"]["y"])) for item in pillars},
            REFERENCE_ORIGIN,
            REFERENCE_BASIS_X,
            REFERENCE_BASIS_Y,
        )
        pillar_ms = _ms(pillar_started)
        # Detect the blue-based player independently before resolving cell conflicts.
        # A compressed/bordered blue base can otherwise be misread as a repulsion
        # glyph and incorrectly suppress the stronger player signal on that cell.
        player_started = time.perf_counter()
        player = self.detect_player(canonical, set())
        player_ms = _ms(player_started)
        if player is not None:
            player_cell = (int(player["cell"]["x"]), int(player["cell"]["y"]))
            pillars = [
                item
                for item in pillars
                if (int(item["cell"]["x"]), int(item["cell"]["y"])) != player_cell
            ]
        occupied_cells = {
            (int(item["cell"]["x"]), int(item["cell"]["y"])) for item in pillars
        }
        if player is not None:
            occupied_cells.add((int(player["cell"]["x"]), int(player["cell"]["y"])))
        glyph_started = time.perf_counter()
        glyph = self.detect_glyphs(canonical, occupied_cells=occupied_cells)
        charge_tracks = self.detect_charge_tracks(canonical)
        glyph_ms = _ms(glyph_started)
        sampling_ms = _ms(sampling_started)

        fixture_started = time.perf_counter()
        fixture, fixture_distance, fixture_margin = self.match_fixture(
            canonical,
            source_sha256=source_sha256,
        )
        fixture_ms = _ms(fixture_started)
        return {
            "status": "recognised_review_required",
            "registration": registration.public(),
            "player": player,
            "pillars": pillars,
            "pillarCompleteness": completeness,
            "glyphPattern": glyph,
            "chargeTracks": charge_tracks,
            "matchedFixtureId": fixture["fixtureId"] if fixture else None,
            "fixtureMatchDistance": fixture_distance,
            "fixtureMatchMargin": fixture_margin,
            "metrics": {
                "path": "server_fast_fallback",
                "registrationMs": registration_ms,
                "canonicalWarpMs": warp_ms,
                "cellSamplingMs": sampling_ms,
                "pillarMs": pillar_ms,
                "playerMs": player_ms,
                "glyphMs": glyph_ms,
                "fixtureMatchMs": fixture_ms,
                "totalRecognitionMs": _ms(total_started),
                "ocrInvoked": False,
                "templatesReloaded": False,
            },
        }

    def detect_charge_tracks(self, canonical: np.ndarray) -> dict[str, Any] | None:
        """Read the flat rail tokens; the tall value-four pillars are legends."""
        detected: dict[str, int] = {}
        details: dict[str, Any] = {}
        for spell, centres in CHARGE_TRACK_CENTRES.items():
            scores: list[float] = []
            for cx, cy in centres:
                patch = canonical[max(0, cy - 20):cy + 20, max(0, cx - 35):cx + 35]
                if not patch.size:
                    scores.append(0.0)
                    continue
                grey = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
                # Plain rail cells are smooth. The flat counter token contains
                # both a stone outline and a crisp coloured glyph, producing a
                # strong cell-local high-frequency response.
                scores.append(float(cv2.Laplacian(grey, cv2.CV_64F).var()))
            order = np.argsort(scores)[::-1]
            best = int(order[0])
            second = float(scores[int(order[1])])
            margin = float(scores[best] - second)
            confidence = min(1.0, max(0.0, 0.55 + margin / max(1.0, scores[best])))
            detected[spell] = best
            details[spell] = {"value": best, "confidence": round(confidence, 6), "scores": [round(score, 6) for score in scores]}
        return {"values": detected, "confirmed": all(item["confidence"] >= 0.72 for item in details.values()), "confidence": round(min(item["confidence"] for item in details.values()), 6), "details": details, "method": "registered_flat_charge_track_token"}

    def detect_glyphs(
        self,
        canonical: np.ndarray,
        *,
        occupied_cells: set[tuple[int, int]] | None = None,
    ) -> dict[str, Any] | None:
        """Classify the projected black/white pattern on registered logical cells.

        The Dofus overlay desaturates the underlying sandstone tile. Sampling is
        intentionally cell-local and shifted to the visual centre of the
        isometric diamond; the logical anchor itself lies near its lower tip.
        Side lobes keep the signal usable when a pillar or the player covers the
        middle of a glyph cell. Reliable black observations select one of four
        legal phases; the corresponding white positions are then derived from
        that phase instead of independently confirmed from noisy light patches.
        """
        occupied_cells = occupied_cells or set()
        policy = self.glyph_appearance["classification"]
        saturation_max = int(policy["maximumSaturationForOverlayPixel"])
        presence_min = float(policy["minimumOverlayFraction"])
        dark_value_max = float(policy["blackWhiteValueThreshold"])
        precision_min = float(policy["minimumTemplatePrecision"])
        margin_min = float(policy["minimumTemplateMargin"])
        hsv = cv2.cvtColor(canonical, cv2.COLOR_BGR2HSV)
        samples: list[dict[str, Any]] = []
        for cell in self.automatic_object_cells:
            # The physical reference pattern is contained in the seven-by-seven
            # logical centre window in every retained and observed round.
            if max(abs(cell[0]), abs(cell[1])) > 3:
                continue
            centre = REFERENCE_ORIGIN + cell[0] * REFERENCE_BASIS_X + cell[1] * REFERENCE_BASIS_Y
            cx, anchor_y = np.rint(centre).astype(int)
            cy = int(anchor_y - 17)
            if cx - 30 < 0 or cx + 31 > hsv.shape[1] or cy - 13 < 0 or cy + 14 > hsv.shape[0]:
                continue
            patch = hsv[cy - 13 : cy + 14, cx - 30 : cx + 31]
            colour_patch = canonical[cy - 13 : cy + 14, cx - 30 : cx + 31]
            neutral_patch = self.neutral_reference[cy - 13 : cy + 14, cx - 30 : cx + 31]
            yy, xx = np.mgrid[-13:14, -30:31]
            radius = np.abs(xx) / 30.0 + np.abs(yy) / 13.0
            inner = radius <= 0.74
            side_lobes = (radius <= 0.92) & (np.abs(xx) >= 14)
            inner_pixels = patch[inner]
            side_pixels = patch[side_lobes]
            if not len(inner_pixels) or not len(side_pixels):
                continue
            inner_low = inner_pixels[:, 1] < saturation_max
            side_low = side_pixels[:, 1] < saturation_max
            low_fraction = max(float(np.mean(inner_low)), float(np.mean(side_low)))
            low_pixels = np.concatenate((inner_pixels[inner_low], side_pixels[side_low]), axis=0)
            if not len(low_pixels):
                median_value = 255.0
                median_saturation = 255.0
            else:
                median_value = float(np.median(low_pixels[:, 2]))
                median_saturation = float(np.median(low_pixels[:, 1]))
            samples.append(
                {
                    "cell": cell,
                    "lowFraction": low_fraction,
                    "medianValue": median_value,
                    "medianSaturation": median_saturation,
                    "occupied": cell in occupied_cells,
                    "features": patch_features(
                        colour_patch,
                        neutral_patch,
                        self._black_glyph_template,
                        self._white_glyph_template,
                    ),
                }
            )

        by_cell = {item["cell"]: item for item in samples}
        if not by_cell:
            return None

        visible_samples = {
            cell: sample for cell, sample in by_cell.items() if not sample["occupied"]
        }
        classified: dict[tuple[int, int], tuple[str, float]] = {}
        for cell, sample in visible_samples.items():
            low_fraction = float(sample["lowFraction"])
            if low_fraction < presence_min:
                continue
            strength = min(1.0, (low_fraction - presence_min) / max(0.01, 1.0 - presence_min) + 0.45)
            features = sample["features"]
            black_evidence = (
                0.38 * features["blackTemplateSimilarity"]
                + 0.24 * max(0.0, -features["lightnessDelta"] * 4.0)
                + 0.18 * min(1.0, features["labDelta"] * 4.0)
                + 0.12 * min(1.0, features["gradientDelta"])
                + 0.08 * strength
            )
            white_evidence = (
                0.38 * features["whiteTemplateSimilarity"]
                + 0.24 * max(0.0, features["lightnessDelta"] * 4.0)
                + 0.18 * min(1.0, features["labDelta"] * 4.0)
                + 0.12 * min(1.0, features["gradientDelta"])
                + 0.08 * strength
            )
            # Appearance medians remain one weak vote, never the decision by themselves.
            if float(sample["medianValue"]) < dark_value_max:
                black_evidence += 0.28
            else:
                white_evidence += 0.28
            colour = "black" if black_evidence >= white_evidence else "white"
            classified[cell] = (colour, max(strength, black_evidence, white_evidence))

        scored_templates: list[
            tuple[
                float,
                str,
                frozenset[tuple[int, int]],
                frozenset[tuple[int, int]],
                float,
                float,
                float,
            ]
        ] = []
        for template_id, black_cells, white_cells in GLYPH_TEMPLATES:
            # The four legal black sets are disjoint, so even one reliable black
            # glyph identifies a phase. White-looking floor patches are common in
            # screenshots and must never create extra confirmed white glyphs.
            black_support = sum(
                strength
                for cell, (colour, strength) in classified.items()
                if colour == "black" and cell in black_cells
            )
            black_conflict = sum(
                strength
                for cell, (colour, strength) in classified.items()
                if colour == "black" and cell not in black_cells
            )
            if black_support == 0.0:
                continue
            observed_expected_black = sum(
                1
                for cell, (colour, _strength) in classified.items()
                if colour == "black" and cell in black_cells
            )
            black_precision = black_support / max(0.001, black_support + black_conflict)
            black_coverage = observed_expected_black / len(black_cells)
            score = black_precision * (0.80 + 0.20 * black_coverage)
            white_support = sum(
                strength
                for cell, (colour, strength) in classified.items()
                if colour == "white" and cell in white_cells
            )
            scored_templates.append(
                (
                    score,
                    template_id,
                    black_cells,
                    white_cells,
                    black_precision,
                    black_support,
                    white_support,
                )
            )

        if not scored_templates:
            return self._partial_glyph_result(classified, by_cell, dark_value_max)
        scored_templates.sort(reverse=True, key=lambda item: item[0])
        score, template_id, black_cells, white_cells, precision, black_support, white_support = scored_templates[0]
        second_score = scored_templates[1][0] if len(scored_templates) > 1 else 0.0
        margin = score - second_score
        complete = precision >= precision_min and margin >= margin_min
        unresolved = sorted((black_cells | white_cells) & occupied_cells)
        key = lambda item: (item["x"] + item["y"], item["x"], item["y"])
        black = sorted((_cell_dict(cell) for cell in black_cells), key=key)
        white = sorted((_cell_dict(cell) for cell in white_cells), key=key)
        phase_scores = [
            {"phase": item[1], "score": round(item[0], 6), "precision": round(item[4], 6)}
            for item in scored_templates
        ]
        alternatives = []
        if len(scored_templates) > 1 and margin < 0.12:
            alternative = scored_templates[1]
            alternatives.append(
                {
                    "phase": alternative[1],
                    "score": round(alternative[0], 6),
                    "blackCells": [_cell_dict(cell) for cell in sorted(alternative[2])],
                    "whiteCells": [_cell_dict(cell) for cell in sorted(alternative[3])],
                }
            )
        return {
            "anchorCell": {"x": 0, "y": 0},
            "confirmedBlackCells": black,
            "confirmedWhiteCells": white,
            "unknownCandidateCells": [_cell_dict(cell) for cell in unresolved],
            "completenessStatus": (
                "provisional_complete" if complete and not unresolved else "review_required"
            ),
            "classifier": "background_normalised_multifeature_phase_v4",
            "templateId": template_id,
            "confidence": round(
                min(
                    0.995 if complete else 0.89,
                    0.70 + 0.20 * precision + 0.10 * min(margin / 0.20, 1.0),
                ),
                6,
            ),
            "templateScore": round(score, 6),
            "templateMargin": round(margin, 6),
            "clusterSeparation": round(dark_value_max, 3),
            "observedBlackCells": [
                _cell_dict(cell) for cell, item in classified.items() if item[0] == "black"
            ],
            "observedWhiteCells": [
                _cell_dict(cell) for cell, item in classified.items() if item[0] == "white"
            ],
            "occludedCells": [_cell_dict(cell) for cell in unresolved],
            "cellScores": [
                {"cell": _cell_dict(cell), **sample["features"], "visibility": "partial" if sample["occupied"] else "visible"}
                for cell, sample in sorted(by_cell.items())
            ],
            "phaseScores": phase_scores,
            "selectedPhase": template_id,
            "secondBestPhase": scored_templates[1][1] if len(scored_templates) > 1 else None,
            "scoreMargin": round(margin, 6),
            "alternatives": alternatives,
            "methods": [
                "neutral_cell_lab_delta",
                "neutral_cell_saturation_delta",
                "gradient_structure",
                "reference_patch_template_similarity",
                "global_phase_scoring",
                "occlusion_masking",
            ],
            "reasonCodes": [
                "GLYPH-BLACK-DRIVEN-PHASE",
                "GLYPH-WHITE-GEOMETRY-DERIVED",
                *([] if complete else ["GLYPH-PHASE-TEMPLATE-RECONSTRUCTED"]),
            ],
        }

    def _build_glyph_templates(self) -> tuple[np.ndarray | None, np.ndarray | None]:
        reference_turn = load_json(self.project_root / "data" / "arena" / "reference-turn.manual.json")
        pattern = reference_turn["glyphPattern"]

        def patches(cells: list[dict[str, int]]) -> list[tuple[np.ndarray, np.ndarray]]:
            result: list[tuple[np.ndarray, np.ndarray]] = []
            for cell in cells:
                centre = REFERENCE_ORIGIN + int(cell["x"]) * REFERENCE_BASIS_X + int(cell["y"]) * REFERENCE_BASIS_Y
                cx, anchor_y = np.rint(centre).astype(int)
                cy = int(anchor_y - 17)
                current = self.reference[cy - 13 : cy + 14, cx - 30 : cx + 31]
                neutral = self.neutral_reference[cy - 13 : cy + 14, cx - 30 : cx + 31]
                if current.shape == (27, 61, 3) and neutral.shape == current.shape:
                    result.append((current, neutral))
            return result

        return (
            build_template(patches(pattern["physicalBlackCells"])),
            build_template(patches(pattern["physicalWhiteCells"])),
        )

    @staticmethod
    def _partial_glyph_result(
        classified: dict[tuple[int, int], tuple[str, float]],
        samples: dict[tuple[int, int], dict[str, Any]],
        dark_value_max: float,
        *,
        template_id: str | None = None,
        template_score: float = 0.0,
        template_margin: float = 0.0,
    ) -> dict[str, Any] | None:
        if not classified:
            return None
        key = lambda item: (item["x"] + item["y"], item["x"], item["y"])
        black = sorted(
            (_cell_dict(cell) for cell, item in classified.items() if item[0] == "black"),
            key=key,
        )
        white = sorted(
            (_cell_dict(cell) for cell, item in classified.items() if item[0] == "white"),
            key=key,
        )
        confidence = float(np.mean([item[1] for item in classified.values()]))
        return {
            "anchorCell": {"x": 0, "y": 0},
            "confirmedBlackCells": black,
            "confirmedWhiteCells": white,
            "unknownCandidateCells": sorted(
                (_cell_dict(cell) for cell, sample in samples.items() if sample["occupied"]),
                key=key,
            ),
            "completenessStatus": "review_required",
            "classifier": "registered_cell_appearance_v3",
            "templateId": template_id,
            "confidence": round(min(0.89, confidence), 6),
            "templateScore": round(template_score, 6),
            "templateMargin": round(template_margin, 6),
            "clusterSeparation": round(dark_value_max, 3),
            "observedBlackCells": black,
            "observedWhiteCells": white,
        }

    def register(self, image: np.ndarray) -> RegistrationResult:
        target_work, target_scale = self._working_gray(image)
        keypoints, descriptors = self._orb.detectAndCompute(target_work, None)
        if descriptors is None or len(keypoints) < 80:
            return self._registration_failure("VISION-REGISTRATION-FEATURES")

        pairs = self._matcher.knnMatch(self._reference_descriptors, descriptors, k=2)
        good = [first for first, second in pairs if first.distance < 0.72 * second.distance]
        if len(good) < 60:
            return self._registration_failure("VISION-REGISTRATION-MATCHES", good_matches=len(good))

        source_work = np.float32([self._reference_keypoints[item.queryIdx].pt for item in good])
        target_points_work = np.float32([keypoints[item.trainIdx].pt for item in good])
        affine_work, inlier_mask = cv2.estimateAffinePartial2D(
            source_work,
            target_points_work,
            method=cv2.RANSAC,
            ransacReprojThreshold=2.5,
            maxIters=3000,
            confidence=0.995,
            refineIters=20,
        )
        if affine_work is None or inlier_mask is None:
            return self._registration_failure("VISION-REGISTRATION-AFFINE", good_matches=len(good))

        inliers = inlier_mask.ravel().astype(bool)
        inlier_count = int(inliers.sum())
        if inlier_count < 40:
            return self._registration_failure(
                "VISION-REGISTRATION-INLIERS", good_matches=len(good), inliers=inlier_count
            )

        predicted = cv2.transform(source_work[None, :, :], affine_work)[0]
        residual_px = np.linalg.norm(predicted - target_points_work, axis=1)[inliers]
        reference_basis_work = REFERENCE_BASIS * self._reference_scale
        target_basis_work = affine_work[:, :2] @ reference_basis_work
        cell_scale_work = float(np.mean(np.linalg.norm(target_basis_work, axis=0)))
        residual_cell = residual_px / max(cell_scale_work, 1e-6)
        median_cell = float(np.median(residual_cell))
        p95_cell = float(np.percentile(residual_cell, 95))

        region_count = self._spatial_region_count(source_work[inliers])
        second_inliers = self._second_hypothesis_inliers(source_work, target_points_work, inliers)
        ambiguity_margin = 1.0 - (second_inliers / max(inlier_count, 1))

        affine_original = self._to_original_affine(affine_work, target_scale)
        inverse_original = cv2.invertAffineTransform(affine_original)
        linear = affine_original[:, :2]
        scale = math.sqrt(abs(float(np.linalg.det(linear))))
        rotation_deg = math.degrees(math.atan2(float(linear[1, 0]), float(linear[0, 0])))

        origin = _apply_affine(affine_original, REFERENCE_ORIGIN)
        basis_x_endpoint = _apply_affine(affine_original, REFERENCE_ORIGIN + REFERENCE_BASIS_X)
        basis_y_endpoint = _apply_affine(affine_original, REFERENCE_ORIGIN + REFERENCE_BASIS_Y)
        basis_x = basis_x_endpoint - origin
        basis_y = basis_y_endpoint - origin

        reason_codes: list[str] = []
        if region_count < 3:
            reason_codes.append("VISION-REGISTRATION-DISTRIBUTION")
        if p95_cell > 0.16:
            reason_codes.append("VISION-REGISTRATION-RESIDUAL")
        if ambiguity_margin < 0.15:
            reason_codes.append("VISION-REGISTRATION-AMBIGUOUS")
        if not 0.45 <= scale <= 1.60:
            reason_codes.append("VISION-REGISTRATION-SCALE")
        if abs(rotation_deg) > 3.0:
            reason_codes.append("VISION-REGISTRATION-ROTATION")

        confidence = min(
            0.995,
            0.70
            + min(inlier_count / 250.0, 1.0) * 0.12
            + min(region_count / 6.0, 1.0) * 0.08
            + max(0.0, 1.0 - p95_cell / 0.16) * 0.08,
        )
        if ambiguity_margin < 0.25:
            confidence = min(confidence, 0.79)
        accepted = not reason_codes
        status = "accepted_review_required" if accepted else "manual_registration_required"
        return RegistrationResult(
            accepted=accepted,
            status=status,
            affine_reference_to_image=affine_original,
            affine_image_to_reference=inverse_original,
            origin_image=(float(origin[0]), float(origin[1])),
            basis_x_image=(float(basis_x[0]), float(basis_x[1])),
            basis_y_image=(float(basis_y[0]), float(basis_y[1])),
            inlier_count=inlier_count,
            good_match_count=len(good),
            region_count=region_count,
            median_residual_cell=round(median_cell, 6),
            p95_residual_cell=round(p95_cell, 6),
            ambiguity_margin=round(float(ambiguity_margin), 6),
            confidence=round(confidence, 6),
            reason_codes=tuple(reason_codes),
        )

    def detect_pillars(self, canonical: np.ndarray) -> list[dict[str, Any]]:
        board_x0, board_x1 = 100, min(canonical.shape[1], 1850)
        board_y1 = min(canonical.shape[0], CANONICAL_BOARD_BOTTOM)
        hsv = cv2.cvtColor(canonical[:board_y1, board_x0:board_x1], cv2.COLOR_BGR2HSV)
        # Calibrated once against the retained reference. Centroid offsets are
        # expressed in canonical pixels relative to the logical cell centre.
        parameters = {
            "indecision": ((60, 70, 70), (95, 255, 255), np.array([0.48, -43.43]), 250, 1300, 650.0),
            "reflection": ((35, 150, 60), (65, 255, 255), np.array([-0.42, -42.66]), 700, 2200, 1300.0),
            "repulsion": ((23, 180, 100), (35, 255, 255), np.array([1.89, -43.02]), 600, 2200, 1060.0),
            "attraction": ((0, 160, 70), (14, 255, 255), np.array([-0.76, -41.06]), 650, 2200, 1160.0),
        }
        proposals: dict[tuple[int, int], list[dict[str, Any]]] = {}
        for spell_type, (lower, upper, offset, area_min, area_max, expected_area) in parameters.items():
            mask = cv2.inRange(hsv, np.array(lower, np.uint8), np.array(upper, np.uint8))
            mask = cv2.morphologyEx(
                mask,
                cv2.MORPH_CLOSE,
                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)),
            )
            mask = cv2.dilate(mask, np.ones((3, 3), np.uint8))
            count, _, stats, centroids = cv2.connectedComponentsWithStats(mask)
            for index in range(1, count):
                area = int(stats[index, cv2.CC_STAT_AREA])
                width = int(stats[index, cv2.CC_STAT_WIDTH])
                height = int(stats[index, cv2.CC_STAT_HEIGHT])
                if not area_min <= area <= area_max or width > 100 or height > 85:
                    continue
                canonical_centroid = centroids[index] + np.array([board_x0, 0.0])
                cell_center = canonical_centroid - offset
                logical = REFERENCE_BASIS_INV @ (cell_center - REFERENCE_ORIGIN)
                snapped = np.rint(logical).astype(int)
                cell = (int(snapped[0]), int(snapped[1]))
                residual = float(np.linalg.norm(logical - snapped))
                if cell not in self.automatic_object_cell_set or residual > 0.25:
                    continue
                area_error = abs(math.log(max(area, 1) / expected_area))
                selection_score = residual + area_error * 0.05
                confidence = max(0.55, min(0.995, 0.995 - residual * 0.9 - area_error * 0.08))
                proposals.setdefault(cell, []).append(
                    {
                        "cell": {"x": cell[0], "y": cell[1]},
                        "spellType": spell_type,
                        "confidence": round(confidence, 6),
                        "snapResidualCell": round(residual, 6),
                        "componentArea": area,
                        "selectionScore": selection_score,
                    }
                )

        selected: list[dict[str, Any]] = []
        for cell, candidates in proposals.items():
            winner = min(candidates, key=lambda item: (item["selectionScore"], item["spellType"]))
            selected.append(winner)
        selected.sort(key=lambda item: (item["cell"]["x"] + item["cell"]["y"], item["cell"]["x"], item["cell"]["y"]))
        for index, item in enumerate(selected, start=1):
            item["id"] = f"P{index:02d}"
            item.pop("selectionScore", None)
        return selected

    def detect_player(self, canonical: np.ndarray, pillar_cells: set[tuple[int, int]]) -> dict[str, Any] | None:
        hsv = cv2.cvtColor(canonical, cv2.COLOR_BGR2HSV)
        scores: list[tuple[float, tuple[int, int], int]] = []
        for cell in self.automatic_object_cells:
            if cell in pillar_cells:
                continue
            centre = REFERENCE_ORIGIN + cell[0] * REFERENCE_BASIS_X + cell[1] * REFERENCE_BASIS_Y
            cx, cy = np.rint(centre).astype(int)
            patch = hsv[max(0, cy - 15) : min(hsv.shape[0], cy + 28), max(0, cx - 48) : min(hsv.shape[1], cx + 48)]
            if patch.size == 0:
                continue
            hue, saturation, value = cv2.split(patch)
            mask = (hue >= 85) & (hue <= 115) & (saturation >= 80) & (value >= 65)
            count = int(mask.sum())
            score = float(count + 0.01 * saturation[mask].sum()) if count else 0.0
            scores.append((score, cell, count))
        if not scores:
            return None
        scores.sort(reverse=True)
        best_score, best_cell, best_count = scores[0]
        second_score = scores[1][0] if len(scores) > 1 else 0.0
        ratio = best_score / max(second_score, 1.0)
        if best_count < 150 or ratio < 2.0:
            return None
        confidence = min(0.995, 0.82 + min(best_count / 700.0, 1.0) * 0.10 + min((ratio - 2.0) / 6.0, 1.0) * 0.07)
        return {
            "cell": {"x": best_cell[0], "y": best_cell[1]},
            "confidence": round(confidence, 6),
            "blueBasePixelCount": best_count,
            "separationRatio": round(ratio, 6),
        }

    def match_fixture(
        self,
        canonical: np.ndarray,
        *,
        source_sha256: str | None,
    ) -> tuple[dict[str, Any] | None, float | None, float | None]:
        if source_sha256 and source_sha256 in self._fixture_by_hash:
            return self._fixture_by_hash[source_sha256], 0.0, 1.0
        fingerprint = self._fingerprint(canonical)
        distances = sorted(
            ((float(np.mean(np.abs(fingerprint - stored))), fixture) for fixture, stored in self._fixture_fingerprints),
            key=lambda item: item[0],
        )
        if not distances:
            return None, None, None
        best_distance, best_fixture = distances[0]
        second_distance = distances[1][0] if len(distances) > 1 else 1.0
        margin = second_distance - best_distance
        if best_distance > 0.18 or margin < 0.018:
            return None, round(best_distance, 6), round(margin, 6)
        return best_fixture, round(best_distance, 6), round(margin, 6)

    def _build_fixture_fingerprints(self) -> None:
        for fixture in self.fixture_catalog["fixtures"]:
            path = self.project_root / fixture["source"]["path"]
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if image is None:
                continue
            registration = self.register(image)
            if not registration.accepted or registration.affine_image_to_reference is None:
                continue
            canonical = cv2.warpAffine(
                image,
                registration.affine_image_to_reference,
                (self.reference_width, self.reference_height),
                flags=cv2.INTER_AREA,
                borderMode=cv2.BORDER_REPLICATE,
            )
            self._fixture_fingerprints.append((fixture, self._fingerprint(canonical)))

    @staticmethod
    def _fingerprint(canonical: np.ndarray) -> np.ndarray:
        board = canonical[0:CANONICAL_BOARD_BOTTOM, 180:1770]
        gray = cv2.cvtColor(board, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (80, 44), interpolation=cv2.INTER_AREA).astype(np.float32)
        small = cv2.GaussianBlur(small, (3, 3), 0)
        return (small - float(small.mean())) / max(float(small.std()), 1.0)

    def _working_gray(self, image: np.ndarray) -> tuple[np.ndarray, float]:
        height, width = image.shape[:2]
        target_width = min(WORK_MAX_WIDTH, max(WORK_MIN_WIDTH, width))
        scale = target_width / width
        if abs(scale - 1.0) < 1e-6:
            resized = image
        else:
            resized = cv2.resize(image, (target_width, max(1, round(height * scale))), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY) if resized.ndim == 3 else resized
        return gray, scale

    def _to_original_affine(self, affine_work: np.ndarray, target_scale: float) -> np.ndarray:
        original = affine_work.astype(np.float64).copy()
        original[:, :2] *= self._reference_scale / target_scale
        original[:, 2] /= target_scale
        return original

    def _spatial_region_count(self, points: np.ndarray) -> int:
        if len(points) == 0:
            return 0
        height, width = self._reference_work.shape[:2]
        occupied = set()
        for x, y in points:
            column = min(2, max(0, int(x / max(width, 1) * 3)))
            row = min(2, max(0, int(y / max(height, 1) * 3)))
            occupied.add((column, row))
        return len(occupied)

    @staticmethod
    def _second_hypothesis_inliers(source: np.ndarray, target: np.ndarray, first_inliers: np.ndarray) -> int:
        outlier_mask = ~first_inliers
        if int(outlier_mask.sum()) < 40:
            return 0
        _, mask = cv2.estimateAffinePartial2D(
            source[outlier_mask],
            target[outlier_mask],
            method=cv2.RANSAC,
            ransacReprojThreshold=2.5,
            maxIters=1200,
            confidence=0.99,
            refineIters=10,
        )
        return int(mask.sum()) if mask is not None else 0

    @staticmethod
    def _registration_failure(
        code: str,
        *,
        good_matches: int = 0,
        inliers: int = 0,
    ) -> RegistrationResult:
        return RegistrationResult(
            accepted=False,
            status="manual_registration_required",
            affine_reference_to_image=None,
            affine_image_to_reference=None,
            origin_image=None,
            basis_x_image=None,
            basis_y_image=None,
            inlier_count=inliers,
            good_match_count=good_matches,
            region_count=0,
            median_residual_cell=None,
            p95_residual_cell=None,
            ambiguity_margin=None,
            confidence=0.0,
            reason_codes=(code,),
        )

    @staticmethod
    def _failure(code: str, started: float) -> dict[str, Any]:
        return {
            "status": "manual_registration_required",
            "registration": FastRecognitionEngine._registration_failure(code).public(),
            "player": None,
            "pillars": [],
            "glyphPattern": None,
            "matchedFixtureId": None,
            "metrics": {
                "path": "server_fast_fallback",
                "registrationMs": 0.0,
                "canonicalWarpMs": 0.0,
                "cellSamplingMs": 0.0,
                "fixtureMatchMs": 0.0,
                "totalRecognitionMs": _ms(started),
                "ocrInvoked": False,
                "templatesReloaded": False,
            },
        }


_ENGINE_LOCK = threading.Lock()
_ENGINES: dict[str, FastRecognitionEngine] = {}


def get_fast_engine(project_root: Path) -> FastRecognitionEngine:
    key = str(project_root.resolve())
    with _ENGINE_LOCK:
        if key not in _ENGINES:
            _ENGINES[key] = FastRecognitionEngine(project_root)
        return _ENGINES[key]


def register_screenshot_to_arena(
    image: np.ndarray | Path | str,
    project_root: Path,
) -> RegistrationResult:
    """Register an arbitrary screenshot to the fixed canonical arena.

    This is the public fast-path contract used by tests and future browser/API
    adapters. It returns geometry only; no pixel data enters the tactical solver.
    """
    if isinstance(image, (str, Path)):
        decoded = cv2.imread(str(image), cv2.IMREAD_COLOR)
        if decoded is None:
            return FastRecognitionEngine._registration_failure("VISION-DECODE-FAILED")
    else:
        decoded = image
    return get_fast_engine(project_root).register(decoded)


def registerScreenshotToArena(
    image: np.ndarray | Path | str,
    project_root: Path,
) -> RegistrationResult:
    """Compatibility alias matching the cross-runtime contract name."""
    return register_screenshot_to_arena(image, project_root)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _apply_affine(matrix: np.ndarray, point: np.ndarray) -> np.ndarray:
    return matrix[:, :2] @ point + matrix[:, 2]


def _point(value: tuple[float, float] | None) -> dict[str, float] | None:
    if value is None:
        return None
    return {"x": round(value[0], 6), "y": round(value[1], 6)}


def _cell_dict(value: tuple[int, int]) -> dict[str, int]:
    return {"x": int(value[0]), "y": int(value[1])}


def _ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000.0, 3)
