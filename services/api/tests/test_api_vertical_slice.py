from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
import json

import grougal_solver.app as app_module
from grougal_solver.session_store import SessionStore

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _command(client: TestClient, analysis_id: str, token: str, version: int, kind: str, payload: dict) -> dict:
    response = client.post(
        f"/api/v1/analyses/{analysis_id}/commands",
        headers={**_headers(token), "Content-Type": "application/json"},
        json={
            "schemaVersion": "0.6.0",
            "commandId": f"cmd_{kind}_{version}",
            "analysisId": analysis_id,
            "expectedStateVersion": version,
            "type": kind,
            "payload": payload,
            "issuedAt": "2026-06-28T12:00:00Z",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_reference_upload_manual_review_solve_annotate_delete(tmp_path: Path) -> None:
    app_module.store = SessionStore(tmp_path / "sessions")
    client = TestClient(app_module.app)

    created = client.post(
        "/api/v1/analyses",
        json={
            "schemaVersion": "0.7.0",
            "locale": "fr",
            "retentionConsent": "ephemeral_only",
            "qualityImprovementConsent": False,
        },
    )
    assert created.status_code == 201
    body = created.json()
    session_schema = json.loads((PROJECT_ROOT / "schemas" / "analysis-session.schema.json").read_text())
    Draft202012Validator(session_schema).validate(body["session"])
    analysis_id = body["session"]["analysisId"]
    token = body["accessToken"]
    version = body["session"]["stateVersion"]

    reference = PROJECT_ROOT / "assets" / "reference" / "user_reference.png"
    with reference.open("rb") as handle:
        uploaded = client.post(
            f"/api/v1/analyses/{analysis_id}/image",
            headers=_headers(token),
            files={"file": ("capture.png", handle, "image/png")},
            data={"expectedStateVersion": str(version)},
        )
    assert uploaded.status_code == 202, uploaded.text
    envelope = uploaded.json()
    assert len(envelope["turnState"]["pillars"]) == 27
    assert envelope["session"]["gate"]["status"] == "review_required"
    version = envelope["session"]["stateVersion"]

    for kind, payload in [
        ("accept_detection", {}),
        ("set_projection_anchor_confirmation", {"confirmed": True}),
        ("set_pillar_set_complete", {"complete": True}),
        ("set_action_budget", {"value": 3}),
    ]:
        envelope = _command(client, analysis_id, token, version, kind, payload)
        version = envelope["session"]["stateVersion"]
    for spell in ("indecision", "reflection", "repulsion", "attraction"):
        envelope = _command(
            client,
            analysis_id,
            token,
            version,
            "set_spell_state",
            {"spell": spell, "availability": "available", "value": None, "confirmed": True},
        )
        version = envelope["session"]["stateVersion"]

    assert envelope["session"]["gate"]["status"] == "ready_for_solver"
    solved = client.post(
        f"/api/v1/analyses/{analysis_id}/solve",
        headers={**_headers(token), "Content-Type": "application/json"},
        json={
            "schemaVersion": "0.7.0",
            "expectedStateVersion": version,
            "mode": "review",
            "confirmedSingleSourceRuleIds": [],
            "maxAlternatives": 2,
        },
    )
    assert solved.status_code == 200, solved.text
    solved_body = solved.json()
    assert solved_body["recommendation"]["status"] in {"solved", "confirmation_required", "blocked_unverified_rule", "no_safe_solution"}
    assert solved_body["session"]["assets"]

    annotated = client.get(f"/api/v1/analyses/{analysis_id}/asset/annotated", headers=_headers(token))
    assert annotated.status_code == 200
    assert annotated.headers["content-type"] == "image/png"

    stale = _command_response(client, analysis_id, token, 0)
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "API-STATE-VERSION-CONFLICT"

    deleted = client.delete(f"/api/v1/analyses/{analysis_id}", headers=_headers(token))
    assert deleted.status_code == 204
    assert not (tmp_path / "sessions" / analysis_id).exists()


def _command_response(client: TestClient, analysis_id: str, token: str, version: int):
    return client.post(
        f"/api/v1/analyses/{analysis_id}/commands",
        headers={**_headers(token), "Content-Type": "application/json"},
        json={
            "schemaVersion": "0.6.0",
            "commandId": "cmd_stale",
            "analysisId": analysis_id,
            "expectedStateVersion": version,
            "type": "set_action_budget",
            "payload": {"value": 3},
            "issuedAt": "2026-06-28T12:00:00Z",
        },
    )


def test_real_round_upload_runs_fast_registration_pipeline(tmp_path: Path) -> None:
    app_module.store = SessionStore(tmp_path / "sessions")
    client = TestClient(app_module.app)
    created = client.post(
        "/api/v1/analyses",
        json={
            "schemaVersion": "0.8.0",
            "locale": "fr",
            "retentionConsent": "ephemeral_only",
            "qualityImprovementConsent": False,
        },
    ).json()
    analysis_id = created["session"]["analysisId"]
    token = created["accessToken"]
    source = PROJECT_ROOT / "packages" / "fixtures" / "real" / "phase7" / "round-01.png"
    with source.open("rb") as handle:
        response = client.post(
            f"/api/v1/analyses/{analysis_id}/image",
            headers=_headers(token),
            files={"file": ("round-01.png", handle, "image/png")},
            data={"expectedStateVersion": "0"},
        )
    assert response.status_code == 202, response.text
    envelope = response.json()
    assert envelope["recognition"]["status"] == "recognised_review_required"
    assert envelope["recognition"]["matchedFixtureId"] == "REAL-P7-01"
    assert envelope["recognition"]["registration"]["accepted"] is True
    assert envelope["turnState"]["player"]["current"] == {"x": 1, "y": -1}
    assert len(envelope["turnState"]["pillars"]) == 24
    assert len(envelope["turnState"]["glyphs"]["blackOffsets"]) == 3
    assert len(envelope["turnState"]["glyphs"]["whiteOffsets"]) == 3
    assert envelope["recognition"]["proposals"]["player"]["cell"] == {"x": 1, "y": -1}
    assert len(envelope["recognition"]["proposals"]["pillars"]) == 24
    assert envelope["performance"]["serverScreenshotToStateMs"] < 5_000
    assert envelope["recognition"]["metrics"]["ocrInvoked"] is False
    assert envelope["session"]["gate"]["status"] == "review_required"


def test_real_round_confirmed_player_flow_returns_concrete_recommendation(tmp_path: Path) -> None:
    app_module.store = SessionStore(tmp_path / "sessions")
    client = TestClient(app_module.app)
    created = client.post(
        "/api/v1/analyses",
        json={
            "schemaVersion": "0.8.0",
            "locale": "fr",
            "retentionConsent": "ephemeral_only",
            "qualityImprovementConsent": False,
        },
    ).json()
    analysis_id = created["session"]["analysisId"]
    token = created["accessToken"]
    source = PROJECT_ROOT / "packages" / "fixtures" / "real" / "phase7" / "round-01.png"
    with source.open("rb") as handle:
        uploaded = client.post(
            f"/api/v1/analyses/{analysis_id}/image",
            headers=_headers(token),
            files={"file": ("round-01.png", handle, "image/png")},
            data={"expectedStateVersion": "0"},
        ).json()

    version = uploaded["session"]["stateVersion"]
    for kind, payload in [
        ("accept_detection", {}),
        ("set_projection_anchor_confirmation", {"confirmed": True}),
        ("set_pillar_set_complete", {"complete": True}),
        ("set_action_budget", {"value": 1}),
    ]:
        uploaded = _command(client, analysis_id, token, version, kind, payload)
        version = uploaded["session"]["stateVersion"]
    for spell in ("indecision", "reflection", "repulsion", "attraction"):
        uploaded = _command(
            client,
            analysis_id,
            token,
            version,
            "set_spell_state",
            {"spell": spell, "availability": "available", "value": None, "confirmed": True},
        )
        version = uploaded["session"]["stateVersion"]

    assert uploaded["session"]["gate"]["status"] == "ready_for_solver"
    solved = client.post(
        f"/api/v1/analyses/{analysis_id}/solve",
        headers={**_headers(token), "Content-Type": "application/json"},
        json={
            "schemaVersion": "0.8.0",
            "expectedStateVersion": version,
            "mode": "review",
            "confirmedSingleSourceRuleIds": [],
            "maxAlternatives": 2,
        },
    )
    assert solved.status_code == 200, solved.text
    recommendation = solved.json()["recommendation"]
    assert recommendation["status"] in {"solved", "no_safe_solution"}, recommendation
    assert recommendation["status"] != "blocked_unverified_rule"
    assert recommendation["evidenceMode"] == "retained_fixture_proof"
