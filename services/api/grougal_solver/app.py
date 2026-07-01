from __future__ import annotations

import hashlib
import os
import secrets
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .api_models import CreateAnalysisRequest, SolveRequest
from .editor import CommandRejected, apply_command, validate_turn_state
from .fixtures import get_fixture, load_fixture_catalog
from .fast_recognition import get_fast_engine
from .fight_state import reconcile_round_start, resource_state, stage_transition
from .image_ingest import UploadRejected, normalise_image
from .overlay import render_annotated
from .recognition import baseline_recognition
from .session_store import SessionError, SessionStore
from .solver import CapacityExceeded, DeterministicSolver
from .util import load_json

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_ROOT = Path(os.environ.get("GS_SESSION_ROOT", PROJECT_ROOT / "runtime" / "sessions"))
FIXTURE_MODE = os.environ.get("GS_FIXTURE_MODE", "0") == "1"
ENVIRONMENT = os.environ.get("GS_ENV", "development")
if FIXTURE_MODE and ENVIRONMENT in {"preview", "production"}:
    raise RuntimeError("GS_FIXTURE_MODE is forbidden outside development/test")

store = SessionStore(RUNTIME_ROOT)
solver = DeterministicSolver(PROJECT_ROOT)
fast_engine = get_fast_engine(PROJECT_ROOT)
app = FastAPI(title="Grougalorasalar Solver API", version="0.9.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin for origin in os.environ.get("GS_ALLOWED_ORIGINS", "http://localhost:3000").split(",") if origin],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Analysis-Token"],
)

PUBLIC_DIR = PROJECT_ROOT / "apps" / "web" / "public"
if PUBLIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=PUBLIC_DIR), name="static")


@app.middleware("http")
async def response_headers(request: Request, call_next):
    request_id = f"req_{secrets.token_urlsafe(12)}"
    try:
        response = await call_next(request)
    except Exception:
        raise
    response.headers["X-Request-Id"] = request_id
    if request.url.path.startswith("/api/v1/analyses"):
        response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(SessionError)
async def session_error_handler(request: Request, exc: SessionError):
    status = 401 if exc.code.startswith("API-AUTH") else 409
    if exc.code == "API-STATE-EXPIRED":
        status = 410
    return _api_error(request, status, exc.code, str(exc), {"currentStateVersion": exc.current_version})


@app.exception_handler(CommandRejected)
async def command_error_handler(request: Request, exc: CommandRejected):
    return _api_error(request, 422, exc.code, str(exc))


@app.exception_handler(UploadRejected)
async def upload_error_handler(request: Request, exc: UploadRejected):
    return _api_error(request, 422, exc.code, str(exc))


def _api_error(request: Request, status: int, code: str, message: str, details: dict[str, Any] | None = None):
    request_id = request.headers.get("X-Request-Id", f"req_{secrets.token_urlsafe(12)}")
    return JSONResponse(
        status_code=status,
        content={
            "schemaVersion": "0.6.0",
            "error": {
                "code": code,
                "httpStatus": status,
                "messageKey": f"errors.{code.lower().replace('-', '_')}",
                "requestId": request_id,
                "retryable": code.startswith("API-CAPACITY"),
                "fieldErrors": [],
                "details": {k: v for k, v in (details or {}).items() if v is not None},
            },
        },
    )


def _token(authorization: str | None, x_analysis_token: str | None) -> str:
    if x_analysis_token:
        return x_analysis_token
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    raise SessionError("API-AUTH-TOKEN", "Analysis token is required")


def _envelope(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "session": store.public_session(document),
        "turnState": document.get("turnState"),
        "observations": document.get("observations", []),
        "recommendation": document.get("recommendation"),
        "fight": document.get("fight"),
        "recognition": document.get("recognition"),
        "performance": document.get("performance", {}),
        "audit": document.get("audit", [])[-20:],
    }


@app.get("/", response_class=HTMLResponse)
def root():
    fallback = PUBLIC_DIR / "prelive.html"
    if fallback.exists():
        return fallback.read_text(encoding="utf-8")
    return "<h1>Grougalorasalar Solver API</h1>"


@app.get("/api/v1/health/live")
def live():
    return {"status": "ok", "version": "0.9.0"}


@app.get("/api/v1/health/ready")
def ready():
    required = [
        PROJECT_ROOT / "data" / "rule-catalog.json",
        PROJECT_ROOT / "data" / "arena" / "grougalorasalar.cells.json",
        PROJECT_ROOT / "data" / "vision" / "recognition-policy.v0.5.0.json",
        PROJECT_ROOT / "schemas" / "turn-state.schema.json",
    ]
    missing = [str(path.relative_to(PROJECT_ROOT)) for path in required if not path.exists()]
    if missing:
        raise HTTPException(status_code=503, detail={"missing": missing})
    load_json(required[0])
    load_json(required[1])
    manifest_path = PROJECT_ROOT / "data" / "runtime" / "runtime-manifest.v0.9.0.json"
    manifest = load_json(manifest_path)
    mismatches = []
    for item in manifest["files"]:
        path = PROJECT_ROOT / item["path"]
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        if actual != item["sha256"]:
            mismatches.append(item["path"])
    if mismatches:
        raise HTTPException(status_code=503, detail={"manifestMismatch": mismatches})
    return {
        "status": "ready",
        "releaseVersion": "0.9.0",
        "modelCalibrationStatus": "unvalidated",
        "automaticCriticalConfirmation": False,
        "fixtureMode": FIXTURE_MODE,
        "fastEngineInitialisationMs": fast_engine.initialisation_ms,
    }


@app.get("/api/v1/meta")
def meta():
    return {
        "schemaVersion": "0.8.0",
        "releaseVersion": "0.9.0",
        "supportedLocales": ["fr", "de", "en"],
        "modelCalibrationStatus": "unvalidated",
        "automaticCriticalConfirmation": False,
        "fixtureMode": FIXTURE_MODE,
        "retention": {"idleMinutes": 60, "hardHours": 6},
    }


@app.post("/api/v1/analyses", status_code=201)
def create_analysis(payload: CreateAnalysisRequest, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    document, access_token = store.create(payload.locale, payload.qualityImprovementConsent)
    return {"session": store.public_session(document), "accessToken": access_token}


@app.post("/api/v1/analyses/{analysis_id}/image", status_code=202)
async def upload_image(
    analysis_id: str,
    file: UploadFile = File(...),
    expectedStateVersion: int = Form(...),
    authorization: str | None = Header(default=None),
    x_analysis_token: str | None = Header(default=None, alias="X-Analysis-Token"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    token = _token(authorization, x_analysis_token)
    raw = await file.read()

    def operation(document: dict[str, Any]) -> dict[str, Any]:
        assets_dir = store.asset_path(analysis_id, "normalised.png").parent
        details = normalise_image(raw, assets_dir)
        state, observations, recognition = baseline_recognition(
            PROJECT_ROOT,
            Path(details["working"]),
            source_sha256=details["sha256"],
            source_width=details["width"],
            source_height=details["height"],
            working_width=details["workingWidth"],
            working_height=details["workingHeight"],
        )
        fight = reconcile_round_start(
            document["fight"],
            (state.get("player") or {}).get("current"),
        )
        state["resources"] = resource_state(fight["charges"])
        observations.append(
            {
                "observationId": f"obs_fight_resources_r{fight['round']}",
                "fieldPath": "resources",
                "proposedValue": state["resources"],
                "confidence": 1.0,
                "critical": True,
                "decisionState": "auto_confirmed",
                "method": "stateful_fight_transition",
                "reasonCodes": ["FIGHT-STATE-SYNCHRONISED"],
                "autoConfirmed": True,
            }
        )
        if fight["syncStatus"] == "player_mismatch":
            state["flags"]["criticalFieldsConfirmed"] = False
            recognition["stateContinuity"] = {
                "status": "player_mismatch",
                "expected": fight["pendingTransition"]["expectedFinalCell"],
                "detected": fight.get("detectedStartCell"),
            }
        else:
            recognition["stateContinuity"] = {
                "status": fight["syncStatus"],
                "round": fight["round"],
            }
        document["state"] = "board_review"
        document["assets"] = {"normalised": True, "thumbnail": True, "annotated": False}
        document["image"] = {
            "width": details["width"],
            "height": details["height"],
            "sha256": details["sha256"],
            "workingWidth": details["workingWidth"],
            "workingHeight": details["workingHeight"],
        }
        document["turnState"] = state
        document["observations"] = observations
        document["recognition"] = recognition
        document["fight"] = fight
        document["performance"] = {
            "engineeringTargets": True,
            "ingest": details["metrics"],
            "recognition": recognition["metrics"],
            "serverScreenshotToStateMs": round(
                details["metrics"]["totalIngestMs"] + recognition["metrics"]["totalRecognitionMs"], 3
            ),
        }
        document["recommendation"] = None
        document["recommendationInvalidated"] = False
        return document

    document = store.mutate(
        analysis_id,
        token,
        expectedStateVersion,
        operation,
        idempotency_key=idempotency_key,
    )
    return _envelope(document)


@app.get("/api/v1/analyses/{analysis_id}")
def get_analysis(
    analysis_id: str,
    authorization: str | None = Header(default=None),
    x_analysis_token: str | None = Header(default=None, alias="X-Analysis-Token"),
):
    document = store.read(analysis_id, _token(authorization, x_analysis_token))
    return _envelope(document)


@app.post("/api/v1/analyses/{analysis_id}/commands")
def command(
    analysis_id: str,
    payload: dict[str, Any],
    authorization: str | None = Header(default=None),
    x_analysis_token: str | None = Header(default=None, alias="X-Analysis-Token"),
):
    token = _token(authorization, x_analysis_token)
    required = {"schemaVersion", "commandId", "analysisId", "expectedStateVersion", "type", "payload", "issuedAt"}
    if not required.issubset(payload) or payload.get("analysisId") != analysis_id:
        raise CommandRejected("API-CONTRACT-COMMAND", "Malformed editor command")

    def operation(document: dict[str, Any]) -> dict[str, Any]:
        if document.get("turnState") is None:
            raise CommandRejected("API-STATE-UPLOAD-REQUIRED", "Upload an image first")
        updated = apply_command(document, payload)
        blockers = validate_turn_state(updated["turnState"])
        updated["state"] = "ready_for_solver" if not blockers else "board_review"
        return updated

    document = store.mutate(
        analysis_id,
        token,
        int(payload["expectedStateVersion"]),
        operation,
        idempotency_key=payload["commandId"],
    )
    return _envelope(document)


@app.post("/api/v1/analyses/{analysis_id}/solve")
def solve(
    analysis_id: str,
    payload: SolveRequest,
    authorization: str | None = Header(default=None),
    x_analysis_token: str | None = Header(default=None, alias="X-Analysis-Token"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    token = _token(authorization, x_analysis_token)

    def operation(document: dict[str, Any]) -> dict[str, Any]:
        if document.get("turnState") is None:
            raise CommandRejected("API-STATE-UPLOAD-REQUIRED", "Upload an image first")
        blockers = validate_turn_state(document["turnState"])
        if blockers:
            raise CommandRejected(
                "API-STATE-INCOMPLETE",
                "Review all detected fields before solving",
            )
        document["state"] = "solving"
        import time
        solver_started = time.perf_counter()
        try:
            recognition = document.get("recognition") or {}
            retained_fixture_proof = (
                payload.mode == "review"
                and str(recognition.get("matchedFixtureId") or "").startswith("REAL-P7-")
                and recognition.get("fixtureMatchDistance") == 0.0
            )
            result = solver.solve_given(
                document["turnState"],
                fixture_mode=retained_fixture_proof,
            )
            result["evidenceMode"] = (
                "retained_fixture_proof" if retained_fixture_proof else "review_profile"
            )
        except CapacityExceeded as exc:
            raise SessionError("API-CAPACITY-SOLVER", str(exc)) from exc
        solver_ms = round((time.perf_counter() - solver_started) * 1000.0, 3)
        document.setdefault("performance", {})["solverMs"] = solver_ms
        document["recommendation"] = result
        document["fight"] = stage_transition(document["fight"], result)
        document["recommendationInvalidated"] = False
        document["state"] = {
            "solved": "solved",
            "confirmation_required": "confirmation_required",
            "no_safe_solution": "no_safe_solution",
            "blocked_unverified_rule": "rules_blocked",
            "invalid_state": "rejected",
        }[result["status"]]
        source = store.asset_path(analysis_id, "normalised.png")
        if source.exists():
            annotated = store.asset_path(analysis_id, "annotated.png")
            render_annotated(
                PROJECT_ROOT,
                source,
                annotated,
                document["turnState"],
                result,
                registration=(document.get("recognition") or {}).get("registration"),
            )
            document.setdefault("assets", {})["annotated"] = True
        return document

    document = store.mutate(
        analysis_id,
        token,
        payload.expectedStateVersion,
        operation,
        idempotency_key=idempotency_key,
    )
    return _envelope(document)


@app.get("/api/v1/analyses/{analysis_id}/asset/{asset_kind}")
def get_asset(
    analysis_id: str,
    asset_kind: str,
    authorization: str | None = Header(default=None),
    x_analysis_token: str | None = Header(default=None, alias="X-Analysis-Token"),
):
    store.read(analysis_id, _token(authorization, x_analysis_token))
    names = {"normalised": "normalised.png", "thumbnail": "thumbnail.webp", "annotated": "annotated.png"}
    if asset_kind not in names:
        raise HTTPException(status_code=404)
    path = store.asset_path(analysis_id, names[asset_kind])
    if not path.exists():
        raise HTTPException(status_code=404)
    media = "image/webp" if path.suffix == ".webp" else "image/png"
    return FileResponse(path, media_type=media, headers={"Content-Disposition": "inline", "Cache-Control": "no-store"})


@app.get("/api/v1/analyses/{analysis_id}/overlay")
def get_overlay(
    analysis_id: str,
    authorization: str | None = Header(default=None),
    x_analysis_token: str | None = Header(default=None, alias="X-Analysis-Token"),
):
    document = store.read(analysis_id, _token(authorization, x_analysis_token))
    return {
        "schemaVersion": "0.6.0",
        "analysisId": analysis_id,
        "recommendationInvalidated": document.get("recommendationInvalidated", False),
        "player": document.get("turnState", {}).get("player"),
        "pillars": document.get("turnState", {}).get("pillars", []),
        "glyphs": document.get("turnState", {}).get("glyphs"),
        "actions": [] if document.get("recommendationInvalidated") else (document.get("recommendation") or {}).get("actions", []),
        "finalCell": None if document.get("recommendationInvalidated") else (document.get("recommendation") or {}).get("expected", {}).get("finalCell"),
    }


@app.delete("/api/v1/analyses/{analysis_id}", status_code=204)
def delete_analysis(
    analysis_id: str,
    authorization: str | None = Header(default=None),
    x_analysis_token: str | None = Header(default=None, alias="X-Analysis-Token"),
):
    store.delete(analysis_id, _token(authorization, x_analysis_token))
    return Response(status_code=204)


if FIXTURE_MODE:
    @app.get("/api/v1/fixtures")
    def fixtures():
        catalogue = load_fixture_catalog(PROJECT_ROOT)
        return [{"fixtureId": item["fixtureId"], "title": item["title"]} for item in catalogue["fixtures"]]

    @app.post("/api/v1/fixtures/{fixture_id}/load")
    def load_fixture(fixture_id: str, locale: str = "fr"):
        fixture = get_fixture(PROJECT_ROOT, fixture_id)
        document, access_token = store.create(locale)

        def operation(current: dict[str, Any]) -> dict[str, Any]:
            current["turnState"] = fixture["given"]
            current["observations"] = []
            current["state"] = "ready_for_solver"
            return current

        document = store.mutate(document["analysisId"], access_token, 0, operation)
        return {"session": store.public_session(document), "turnState": document["turnState"], "accessToken": access_token}

    @app.get("/api/v1/diagnostics/contracts")
    def contracts():
        return {
            "solverFixtureCount": load_fixture_catalog(PROJECT_ROOT)["fixtureCount"],
            "visualFixtureCount": load_json(PROJECT_ROOT / "data" / "vision" / "visual-fixture-catalog.v0.5.0.json")["fixtureCount"],
            "automaticCriticalConfirmation": False,
        }
