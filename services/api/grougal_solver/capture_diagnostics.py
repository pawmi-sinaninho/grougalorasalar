# capture-diagnostics-patch
"""
Capture diagnostics helpers for the GROUGALORASALAR solver.

Purpose:
- make capture failures observable
- reduce useless generic "Capture incomplète" responses
- provide reusable timing and geometry cache primitives

This module is safe to install even before the vision pipeline is fully wired to it.
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional, Tuple

try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse, Response
except Exception:  # pragma: no cover - lets tests import helpers without web deps
    BaseHTTPMiddleware = object  # type: ignore
    Request = Any  # type: ignore
    JSONResponse = None  # type: ignore
    Response = Any  # type: ignore

LOG = logging.getLogger("capture.diagnostics")

CAPTURE_DIAGNOSTICS_ENABLED = os.getenv("CAPTURE_DIAGNOSTICS", "1").lower() not in {"0", "false", "no"}
CAPTURE_SOFT_VALIDATION = os.getenv("CAPTURE_SOFT_VALIDATION", "1").lower() not in {"0", "false", "no"}
CAPTURE_DEBUG_DIR = Path(os.getenv("CAPTURE_DEBUG_DIR", ".capture-debug"))
CAPTURE_ROUTE_KEYWORDS = tuple(
    s.strip().lower()
    for s in os.getenv("CAPTURE_ROUTE_KEYWORDS", "capture,analyze,analyse,solve,solver,vision").split(",")
    if s.strip()
)

# Central thresholds. Tune here, not scattered across detector files.
MIN_GRID_COVERAGE_HARD_REJECT = float(os.getenv("CAPTURE_MIN_GRID_COVERAGE_HARD_REJECT", "0.85"))
MIN_GRID_COVERAGE_WARNING = float(os.getenv("CAPTURE_MIN_GRID_COVERAGE_WARNING", "0.95"))
MIN_PLAYER_CONFIDENCE = float(os.getenv("CAPTURE_MIN_PLAYER_CONFIDENCE", "0.55"))
MIN_GLYPH_CONFIDENCE = float(os.getenv("CAPTURE_MIN_GLYPH_CONFIDENCE", "0.50"))
MIN_PILLAR_CONFIDENCE = float(os.getenv("CAPTURE_MIN_PILLAR_CONFIDENCE", "0.50"))
MAX_IMAGE_DIMENSION_CHANGE_RATIO = float(os.getenv("CAPTURE_MAX_IMAGE_DIM_CHANGE_RATIO", "0.02"))


def now_ms() -> float:
    return time.perf_counter() * 1000.0


@dataclass
class CaptureTimings:
    marks: Dict[str, float] = field(default_factory=dict)
    durations_ms: Dict[str, float] = field(default_factory=dict)
    started_ms: float = field(default_factory=now_ms)

    def mark(self, name: str) -> None:
        self.marks[name] = now_ms()

    def span(self, name: str, start_mark: str, end_mark: Optional[str] = None) -> None:
        end = self.marks.get(end_mark, now_ms()) if end_mark else now_ms()
        start = self.marks.get(start_mark, self.started_ms)
        self.durations_ms[name] = round(max(0.0, end - start), 2)

    def add(self, name: str, duration_ms: float) -> None:
        self.durations_ms[name] = round(max(0.0, duration_ms), 2)

    def total(self) -> float:
        return round(max(0.0, now_ms() - self.started_ms), 2)

    def as_dict(self) -> Dict[str, float]:
        data = dict(self.durations_ms)
        data["total_ms"] = self.total()
        return data


class stage_timer:
    """Context manager to time one named pipeline stage."""

    def __init__(self, timings: Optional[CaptureTimings], name: str):
        self.timings = timings
        self.name = name
        self.start = 0.0

    def __enter__(self):
        self.start = now_ms()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.timings is not None:
            self.timings.add(self.name, now_ms() - self.start)
        return False


@dataclass
class CaptureDebug:
    status: str = "ok"
    reason: Optional[str] = None
    image_size: Optional[Tuple[int, int]] = None
    arena_bbox: Optional[Any] = None
    cells_expected: Optional[int] = None
    cells_detected: Optional[int] = None
    white_glyphs_detected: Optional[int] = None
    black_glyphs_detected: Optional[int] = None
    pillars_detected: Optional[int] = None
    player_detected: Optional[bool] = None
    confidence: Optional[float] = None
    warnings: list[str] = field(default_factory=list)
    overlay_path: Optional[str] = None
    timings_ms: Dict[str, float] = field(default_factory=dict)

    def warn(self, code: str) -> None:
        if code not in self.warnings:
            self.warnings.append(code)

    def reject(self, reason: str) -> None:
        self.status = "rejected"
        self.reason = reason

    def as_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v not in (None, [], {})}


class CaptureValidationError(Exception):
    def __init__(self, reason: str, debug: Optional[CaptureDebug] = None, http_status: int = 400):
        super().__init__(reason)
        self.reason = reason
        self.debug = debug or CaptureDebug(status="rejected", reason=reason)
        self.http_status = http_status


def validate_capture_state(
    *,
    cells_expected: Optional[int],
    cells_detected: Optional[int],
    arena_found: bool = True,
    player_detected: bool = True,
    player_confidence: Optional[float] = None,
    glyph_confidence: Optional[float] = None,
    pillar_confidence: Optional[float] = None,
    debug: Optional[CaptureDebug] = None,
    soft: Optional[bool] = None,
) -> CaptureDebug:
    """Central capture validation.

    Hard reject only true blockers. Minor grid/vision uncertainty becomes warnings when
    CAPTURE_SOFT_VALIDATION=1.
    """
    debug = debug or CaptureDebug()
    soft = CAPTURE_SOFT_VALIDATION if soft is None else soft
    debug.cells_expected = cells_expected
    debug.cells_detected = cells_detected
    debug.player_detected = player_detected

    if not arena_found:
        debug.reject("arena_not_found")
        raise CaptureValidationError("arena_not_found", debug)

    if not player_detected or (player_confidence is not None and player_confidence < MIN_PLAYER_CONFIDENCE):
        debug.reject("player_not_found_or_low_confidence")
        raise CaptureValidationError("player_not_found_or_low_confidence", debug)

    if cells_expected and cells_detected is not None:
        coverage = cells_detected / max(1, cells_expected)
        debug.confidence = round(coverage, 4)
        if coverage < MIN_GRID_COVERAGE_HARD_REJECT:
            debug.reject("grid_coverage_too_low")
            raise CaptureValidationError("grid_coverage_too_low", debug)
        if coverage < MIN_GRID_COVERAGE_WARNING:
            debug.warn(f"grid_coverage_warning:{cells_detected}/{cells_expected}")
            if not soft:
                debug.reject("grid_coverage_below_strict_threshold")
                raise CaptureValidationError("grid_coverage_below_strict_threshold", debug)

    if glyph_confidence is not None and glyph_confidence < MIN_GLYPH_CONFIDENCE:
        debug.warn("glyph_detection_low_confidence")
    if pillar_confidence is not None and pillar_confidence < MIN_PILLAR_CONFIDENCE:
        debug.warn("pillar_detection_low_confidence")

    debug.status = "warning" if debug.warnings else "ok"
    return debug


@dataclass
class ArenaGeometry:
    image_size: Tuple[int, int]
    arena_bbox: Any
    cell_centers: Any
    cell_polygons: Optional[Any] = None
    created_at: float = field(default_factory=time.time)

    def compatible_with(self, image_size: Tuple[int, int]) -> bool:
        old_w, old_h = self.image_size
        new_w, new_h = image_size
        if old_w <= 0 or old_h <= 0:
            return False
        dw = abs(new_w - old_w) / old_w
        dh = abs(new_h - old_h) / old_h
        return dw <= MAX_IMAGE_DIMENSION_CHANGE_RATIO and dh <= MAX_IMAGE_DIMENSION_CHANGE_RATIO


class ArenaGeometryCache:
    """In-memory session cache for arena geometry.

    Intended usage:
      cached = arena_geometry_cache.get(session_id, image_size)
      if cached: sample known cells
      else: run full grid detection, then arena_geometry_cache.set(...)
    """

    def __init__(self):
        self._cache: Dict[str, ArenaGeometry] = {}

    def get(self, session_id: str, image_size: Tuple[int, int]) -> Optional[ArenaGeometry]:
        item = self._cache.get(session_id)
        if item and item.compatible_with(image_size):
            return item
        if item:
            self._cache.pop(session_id, None)
        return None

    def set(self, session_id: str, geometry: ArenaGeometry) -> None:
        self._cache[session_id] = geometry

    def reset(self, session_id: Optional[str] = None) -> None:
        if session_id:
            self._cache.pop(session_id, None)
        else:
            self._cache.clear()


arena_geometry_cache = ArenaGeometryCache()


def get_session_id(request: Any) -> str:
    try:
        return (
            request.headers.get("x-capture-session")
            or request.headers.get("x-session-id")
            or request.client.host
            or "default"
        )
    except Exception:
        return "default"


def make_debug_payload(
    *,
    status: str,
    reason: Optional[str] = None,
    message: Optional[str] = None,
    debug: Optional[CaptureDebug] = None,
    timings: Optional[CaptureTimings] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    debug = debug or CaptureDebug(status=status, reason=reason)
    if timings is not None:
        debug.timings_ms = timings.as_dict()
    payload: Dict[str, Any] = {
        "status": status,
        "ok": status not in {"rejected", "error"},
        "message": message or reason or status,
        "debug": debug.as_dict(),
    }
    if extra:
        payload.update(extra)
    return payload


async def _response_body(response: Any) -> bytes:
    body = b""
    async for chunk in response.body_iterator:
        body += chunk
    return body


def _is_capture_route(path: str) -> bool:
    low = path.lower()
    return any(k in low for k in CAPTURE_ROUTE_KEYWORDS)


def _looks_like_incomplete_capture(payload: Any) -> bool:
    try:
        text = json.dumps(payload, ensure_ascii=False).lower()
    except Exception:
        text = str(payload).lower()
    return "capture incompl" in text or "nouvelle image complète" in text or "image complete du début" in text


class CaptureDiagnosticsMiddleware(BaseHTTPMiddleware):  # type: ignore[misc]
    async def dispatch(self, request: Any, call_next: Callable):
        if not CAPTURE_DIAGNOSTICS_ENABLED or not _is_capture_route(str(request.url.path)):
            return await call_next(request)

        timings = CaptureTimings()
        request.state.capture_timings = timings
        request.state.capture_debug = CaptureDebug()

        try:
            response = await call_next(request)
        except CaptureValidationError as exc:
            exc.debug.timings_ms = timings.as_dict()
            LOG.warning("capture rejected: %s debug=%s", exc.reason, exc.debug.as_dict())
            if JSONResponse is None:
                raise
            return JSONResponse(
                make_debug_payload(
                    status="rejected",
                    reason=exc.reason,
                    message="Capture rejected by structured validator.",
                    debug=exc.debug,
                    timings=timings,
                ),
                status_code=exc.http_status,
            )

        total = timings.total()
        try:
            response.headers["x-capture-total-ms"] = str(total)
        except Exception:
            pass

        content_type = ""
        try:
            content_type = response.headers.get("content-type", "")
        except Exception:
            pass

        # Enrich legacy generic capture errors without breaking successful responses.
        if "application/json" in content_type.lower() and getattr(response, "status_code", 200) >= 400:
            try:
                body = await _response_body(response)
                payload = json.loads(body.decode("utf-8")) if body else {}
                if _looks_like_incomplete_capture(payload):
                    debug = getattr(request.state, "capture_debug", CaptureDebug())
                    debug.reject("legacy_capture_incomplete")
                    debug.timings_ms = timings.as_dict()
                    enriched = make_debug_payload(
                        status="rejected",
                        reason="legacy_capture_incomplete",
                        message="Capture incomplète: legacy validator rejected the image. Wire concrete detector counts into CaptureDebug next.",
                        debug=debug,
                        timings=timings,
                        extra={"legacy_response": payload},
                    )
                    LOG.warning("legacy capture incomplete enriched: %s", enriched.get("debug"))
                    if JSONResponse is not None:
                        return JSONResponse(enriched, status_code=getattr(response, "status_code", 400))
                # Recreate consumed response unchanged.
                return Response(
                    content=body,
                    status_code=getattr(response, "status_code", 200),
                    headers=dict(response.headers),
                    media_type=content_type.split(";")[0] or None,
                )
            except Exception:
                LOG.exception("failed to enrich capture diagnostics response")
                return response

        LOG.info("capture route %s completed in %.2fms", request.url.path, total)
        return response


def install_capture_diagnostics(app: Any) -> None:
    """Install middleware once on a FastAPI/Starlette app."""
    if not CAPTURE_DIAGNOSTICS_ENABLED:
        return
    installed = getattr(app.state, "capture_diagnostics_installed", False)
    if installed:
        return
    app.add_middleware(CaptureDiagnosticsMiddleware)
    app.state.capture_diagnostics_installed = True
    LOG.info("capture diagnostics middleware installed")


def attach_debug_counts(
    request: Any,
    *,
    image_size: Optional[Tuple[int, int]] = None,
    arena_bbox: Optional[Any] = None,
    cells_expected: Optional[int] = None,
    cells_detected: Optional[int] = None,
    white_glyphs_detected: Optional[int] = None,
    black_glyphs_detected: Optional[int] = None,
    pillars_detected: Optional[int] = None,
    player_detected: Optional[bool] = None,
    confidence: Optional[float] = None,
) -> CaptureDebug:
    """Convenience hook for existing detector code.

    Use this inside the capture pipeline once counts are known.
    """
    debug = getattr(request.state, "capture_debug", CaptureDebug())
    for key, value in {
        "image_size": image_size,
        "arena_bbox": arena_bbox,
        "cells_expected": cells_expected,
        "cells_detected": cells_detected,
        "white_glyphs_detected": white_glyphs_detected,
        "black_glyphs_detected": black_glyphs_detected,
        "pillars_detected": pillars_detected,
        "player_detected": player_detected,
        "confidence": confidence,
    }.items():
        if value is not None:
            setattr(debug, key, value)
    request.state.capture_debug = debug
    return debug


def write_debug_overlay_placeholder(debug: CaptureDebug, prefix: str = "capture") -> Optional[str]:
    """Create a small JSON placeholder until the real image overlay is wired.

    This avoids silent failures and gives the UI/logs a concrete artifact path.
    """
    try:
        CAPTURE_DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        path = CAPTURE_DEBUG_DIR / f"{prefix}-{uuid.uuid4().hex[:10]}.json"
        path.write_text(json.dumps(debug.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        debug.overlay_path = str(path)
        return str(path)
    except Exception:
        LOG.exception("failed to write debug overlay placeholder")
        return None
