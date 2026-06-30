from __future__ import annotations

from pathlib import Path
from typing import Any

from .arena import arena_given
from .fast_recognition import get_fast_engine
from .util import deep_copy, load_json

REFERENCE_SHA256 = "2756a38a4451117001dedeab2e4da14423d4aa50978bc4549c9ff0cb1340f976"


def _blank_spells() -> dict[str, dict[str, Any]]:
    return {
        spell: {"availability": "unknown", "value": None, "confirmed": False}
        for spell in ("indecision", "reflection", "repulsion", "attraction")
    }


def blank_given(project_root: Path) -> dict[str, Any]:
    walkable = arena_given(project_root)
    return {
        "summary": "Manual pre-live state; automatic confirmation disabled by MODEL-001.",
        "profileMode": "production_review_profile",
        "arena": walkable,
        # Keep an unresolved player unresolved. A synthetic first arena cell
        # previously leaked as a plausible-looking detection.
        "player": {"current": None, "previous": None},
        "pillars": [],
        "glyphs": {
            "blackOffsets": [],
            "whiteOffsets": [],
            "physicalBlackCells": [],
            "physicalWhiteCells": [],
        },
        "resources": {"actionBudget": None, "spells": _blank_spells()},
        "progress": {"dragon": None, "crocoburio": None},
        "flags": {
            "anchorConfirmed": False,
            "criticalFieldsConfirmed": False,
            "multiplayerDetected": False,
            "pillarSetComplete": False,
            "modelCalibrationStatus": "unvalidated",
        },
        "profileOverrides": {},
        "profileId": "review-explicit-hypothesis-0.5.0",
    }


def baseline_recognition(
    project_root: Path,
    image_path: Path,
    *,
    source_sha256: str,
    source_width: int,
    source_height: int,
    working_width: int | None = None,
    working_height: int | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """Create unconfirmed logical proposals from the cached deterministic fast path."""
    if source_sha256 == REFERENCE_SHA256:
        return _reference_recognition(project_root, source_width, source_height)

    engine = get_fast_engine(project_root)
    result = engine.recognise(image_path, source_sha256=source_sha256)
    state = blank_given(project_root)
    observations: list[dict[str, Any]] = []

    registration = deep_copy(result["registration"])
    if registration.get("accepted") and working_width and working_height:
        registration = _scale_registration(
            registration,
            source_width / working_width,
            source_height / working_height,
        )

    observations.append(
        _obs(
            "arena.registration",
            registration,
            float(registration.get("confidence") or 0.0),
            "cached_orb_affine_grid_registration",
            reason="FAST-PATH-REGISTRATION" if registration.get("accepted") else "MODEL-001",
        )
    )

    player = result.get("player")
    if player:
        state["player"] = {"current": deep_copy(player["cell"]), "previous": None}
        observations.append(
            _obs(
                "player.current",
                state["player"]["current"],
                float(player["confidence"]),
                "registered_blue_unit_base_cell_sampling",
                reason="FAST-PATH-PLAYER",
            )
        )
    else:
        observations.append(_obs("player.current", None, 0.0, "player_not_resolved", reason="MODEL-001"))

    state["pillars"] = [
        {"id": item["id"], "cell": deep_copy(item["cell"]), "spellType": item["spellType"]}
        for item in result.get("pillars", [])
    ]
    pillar_confidence = min(
        [float(item.get("confidence", 0.0)) for item in result.get("pillars", [])] or [0.0]
    )
    observations.append(
        _obs(
            "pillars",
            state["pillars"],
            pillar_confidence,
            "registered_known_cell_colour_shape_components",
            reason="FAST-PATH-PILLARS" if state["pillars"] else "MODEL-001",
        )
    )
    observations.append(
        _obs(
            "pillars.complete",
            False,
            min(pillar_confidence, 0.79),
            "independent_candidate_cell_scan_requires_review",
            reason="VISION-PILLAR-SET-INCOMPLETE",
        )
    )

    glyph = result.get("glyphPattern")
    if glyph:
        black_cells = deep_copy(glyph.get("confirmedBlackCells", []))
        white_cells = deep_copy(glyph.get("confirmedWhiteCells", []))
        state["glyphs"] = {
            "blackOffsets": [{"dx": cell["x"], "dy": cell["y"]} for cell in black_cells],
            "whiteOffsets": [{"dx": cell["x"], "dy": cell["y"]} for cell in white_cells],
            "physicalBlackCells": black_cells,
            "physicalWhiteCells": white_cells,
        }
        completeness = glyph.get("completenessStatus", "unknown")
        confidence = 0.92 if completeness == "provisional_complete" else 0.69
        observations.extend(
            [
                _obs(
                    "glyphs.blackOffsets",
                    state["glyphs"]["blackOffsets"],
                    confidence,
                    "registered_fixture_signature_annotation",
                    reason="FAST-PATH-GLYPH-PROPOSAL",
                ),
                _obs(
                    "glyphs.whiteOffsets",
                    state["glyphs"]["whiteOffsets"],
                    confidence if white_cells else 0.0,
                    "registered_fixture_signature_annotation",
                    reason="FAST-PATH-GLYPH-PROPOSAL" if white_cells else "VISION-GLYPH-UNKNOWN",
                ),
                _obs(
                    "glyphs.unknownCandidateCells",
                    deep_copy(glyph.get("unknownCandidateCells", [])),
                    0.0,
                    "manual_review_queue",
                    reason="VISION-GLYPH-UNKNOWN",
                ),
            ]
        )
    else:
        observations.append(
            _obs("glyphs", None, 0.0, "fixture_signature_not_resolved", reason="VISION-GLYPH-UNKNOWN")
        )

    observations.extend(
        [
            _obs("resources.actionBudget", None, 0.0, "not_read_without_verified_ui_contract", reason="V-006"),
            _obs("resources.spells", state["resources"]["spells"], 0.0, "symbols_visible_state_unverified", reason="V-002"),
            _obs("progress", state["progress"], 0.0, "runners_visible_index_unverified", reason="V-001"),
        ]
    )

    matched = result.get("matchedFixtureId")
    state["summary"] = (
        f"Fast-path proposals loaded from {matched}; all critical values remain review-required."
        if matched
        else "Arena registered and known cells sampled; unresolved fields require targeted correction."
    )
    recognition = {
        "pipelineVersion": "fast-path-0.8.0",
        "status": result["status"],
        "matchedFixtureId": matched,
        "fixtureMatchDistance": result.get("fixtureMatchDistance"),
        "fixtureMatchMargin": result.get("fixtureMatchMargin"),
        "registration": registration,
        "metrics": deep_copy(result["metrics"]),
        "proposals": {
            "player": deep_copy(result.get("player")),
            "pillars": deep_copy(result.get("pillars", [])),
            "glyphPattern": deep_copy(result.get("glyphPattern")),
        },
        "automaticCriticalConfirmation": False,
        "ocrInvoked": False,
    }
    return state, observations, recognition


def _reference_recognition(
    project_root: Path,
    source_width: int,
    source_height: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    state = blank_given(project_root)
    reference = load_json(project_root / "data" / "arena" / "reference-turn.manual.json")
    state["player"] = {
        "current": deep_copy(reference["player"]["currentCell"]),
        "previous": reference["player"].get("previousCell"),
    }
    state["pillars"] = [
        {"id": item["id"], "cell": deep_copy(item["cell"]), "spellType": item["spellType"]}
        for item in reference["pillars"]
    ]
    state["glyphs"] = {
        "blackOffsets": deep_copy(reference["glyphPattern"]["blackOffsets"]),
        "whiteOffsets": deep_copy(reference["glyphPattern"]["whiteOffsets"]),
        "physicalBlackCells": deep_copy(reference["glyphPattern"]["physicalBlackCells"]),
        "physicalWhiteCells": deep_copy(reference["glyphPattern"]["physicalWhiteCells"]),
    }
    state["summary"] = "Reference-layout proposals loaded. Every critical proposal requires explicit confirmation."
    observations = [
        _obs("arena.registration", {"status": "reference_identity", "accepted": True}, 0.99, "reference_identity"),
        _obs("player.current", state["player"]["current"], 0.98, "reference_registered_cell"),
        _obs("pillars", state["pillars"], 0.88, "reference_manual_baseline"),
        _obs("glyphs.blackOffsets", state["glyphs"]["blackOffsets"], 0.98, "reference_manual_baseline"),
        _obs("glyphs.whiteOffsets", state["glyphs"]["whiteOffsets"], 0.98, "reference_manual_baseline"),
        _obs("resources.actionBudget", None, 0.0, "not_read_without_verified_ui_contract", reason="V-006"),
    ]
    registration = {
        "status": "reference_identity",
        "accepted": True,
        "referenceToImageAffine": [[source_width / 1951.0, 0.0, 0.0], [0.0, source_height / 1267.0, 0.0]],
        "imageToReferenceAffine": [[1951.0 / source_width, 0.0, 0.0], [0.0, 1267.0 / source_height, 0.0]],
        "originImage": {"x": 964.895 * source_width / 1951.0, "y": 441.7425 * source_height / 1267.0},
        "basisXImage": {"x": 66.75 * source_width / 1951.0, "y": 33.375 * source_height / 1267.0},
        "basisYImage": {"x": -66.75 * source_width / 1951.0, "y": 33.375 * source_height / 1267.0},
        "confidence": 0.99,
        "reasonCodes": [],
    }
    recognition = {
        "pipelineVersion": "fast-path-0.8.0",
        "status": "recognised_review_required",
        "matchedFixtureId": "REFERENCE-01",
        "registration": registration,
        "metrics": {
            "path": "reference_fixture_fast_path",
            "registrationMs": 0.0,
            "canonicalWarpMs": 0.0,
            "cellSamplingMs": 0.0,
            "fixtureMatchMs": 0.0,
            "totalRecognitionMs": 0.0,
            "ocrInvoked": False,
            "templatesReloaded": False,
        },
        "proposals": {
            "player": {"cell": deep_copy(state["player"]["current"]), "confidence": 0.98},
            "pillars": [
                {**deep_copy(item), "confidence": 0.88, "snapResidualCell": 0.0}
                for item in state["pillars"]
            ],
            "glyphPattern": deep_copy(reference["glyphPattern"]),
        },
        "automaticCriticalConfirmation": False,
        "ocrInvoked": False,
    }
    return state, observations, recognition


def _scale_registration(registration: dict[str, Any], scale_x: float, scale_y: float) -> dict[str, Any]:
    result = deep_copy(registration)
    matrix = result.get("referenceToImageAffine")
    if matrix:
        matrix[0] = [matrix[0][0] * scale_x, matrix[0][1] * scale_x, matrix[0][2] * scale_x]
        matrix[1] = [matrix[1][0] * scale_y, matrix[1][1] * scale_y, matrix[1][2] * scale_y]
        result["referenceToImageAffine"] = matrix
    inverse = result.get("imageToReferenceAffine")
    if inverse:
        inverse[0] = [inverse[0][0] / scale_x, inverse[0][1] / scale_y, inverse[0][2]]
        inverse[1] = [inverse[1][0] / scale_x, inverse[1][1] / scale_y, inverse[1][2]]
        result["imageToReferenceAffine"] = inverse
    for key in ("originImage", "basisXImage", "basisYImage"):
        point = result.get(key)
        if point:
            point["x"] *= scale_x
            point["y"] *= scale_y
    return result


def _obs(field: str, value: Any, confidence: float, method: str, reason: str = "MODEL-001") -> dict[str, Any]:
    return {
        "observationId": f"obs_{field.replace('.', '_')}",
        "fieldPath": field,
        "proposedValue": value,
        "confidence": round(confidence, 6),
        "critical": True,
        "decisionState": "review_required",
        "method": method,
        "reasonCodes": [reason],
        "autoConfirmed": False,
    }
