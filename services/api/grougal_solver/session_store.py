from __future__ import annotations

import hashlib
import hmac
import secrets
import shutil
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from .editor import validate_turn_state
from .fight_state import new_fight_state
from .util import deep_copy, dump_json, load_json


class SessionError(ValueError):
    def __init__(self, code: str, message: str, *, current_version: int | None = None):
        super().__init__(message)
        self.code = code
        self.current_version = current_version


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


class SessionStore:
    def __init__(self, root: Path, idle_minutes: int = 60, hard_hours: int = 6):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.idle_minutes = idle_minutes
        self.hard_hours = hard_hours
        self._lock = threading.RLock()

    def create(self, locale: str, quality_improvement: bool = False) -> tuple[dict[str, Any], str]:
        now = utc_now()
        analysis_id = f"ana_{secrets.token_urlsafe(18)}"
        token = secrets.token_urlsafe(32)
        document = {
            "schemaVersion": "0.8.0",
            "analysisId": analysis_id,
            "tokenHash": self._hash(token),
            "state": "created",
            "stateVersion": 0,
            "locale": locale,
            "consent": {
                "retention": "ephemeral_only",
                "qualityImprovement": bool(quality_improvement),
            },
            "createdAt": iso(now),
            "lastActivityAt": iso(now),
            "hardExpiresAt": iso(now + timedelta(hours=self.hard_hours)),
            "expiresAt": iso(now + timedelta(minutes=self.idle_minutes)),
            "assets": {},
            "observations": [],
            "turnState": None,
            "fight": new_fight_state(),
            "history": [],
            "future": [],
            "audit": [],
            "recommendation": None,
            "recommendationInvalidated": False,
            "idempotency": {},
            "deleted": False,
        }
        path = self._dir(analysis_id)
        path.mkdir(parents=True)
        self._write(document)
        return deep_copy(document), token

    def read(self, analysis_id: str, token: str, *, touch: bool = True) -> dict[str, Any]:
        with self._lock:
            document = self._read_existing(analysis_id)
            self._authorise(document, token)
            self._assert_not_expired(document)
            if touch:
                self._touch(document)
                self._write(document)
            return deep_copy(document)

    def mutate(
        self,
        analysis_id: str,
        token: str,
        expected_version: int,
        operation: Callable[[dict[str, Any]], dict[str, Any]],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            document = self._read_existing(analysis_id)
            self._authorise(document, token)
            self._assert_not_expired(document)
            if idempotency_key and idempotency_key in document.get("idempotency", {}):
                return deep_copy(document)
            if document["stateVersion"] != expected_version:
                raise SessionError(
                    "API-STATE-VERSION-CONFLICT",
                    "State version conflict",
                    current_version=document["stateVersion"],
                )
            updated = operation(deep_copy(document))
            updated["stateVersion"] = document["stateVersion"] + 1
            self._touch(updated)
            if idempotency_key:
                updated.setdefault("idempotency", {})[idempotency_key] = updated["stateVersion"]
                updated["idempotency"] = dict(list(updated["idempotency"].items())[-100:])
            self._write(updated)
            return deep_copy(updated)

    def delete(self, analysis_id: str, token: str) -> None:
        with self._lock:
            path = self._dir(analysis_id)
            if not path.exists():
                return
            document = self._read_existing(analysis_id)
            self._authorise(document, token)
            shutil.rmtree(path, ignore_errors=True)

    def cleanup_expired(self) -> int:
        removed = 0
        with self._lock:
            for directory in self.root.glob("ana_*"):
                try:
                    document = load_json(directory / "session.json")
                    self._assert_not_expired(document)
                except (SessionError, FileNotFoundError, ValueError):
                    shutil.rmtree(directory, ignore_errors=True)
                    removed += 1
        return removed

    def asset_path(self, analysis_id: str, name: str) -> Path:
        return self._dir(analysis_id) / "assets" / name

    def public_session(self, document: dict[str, Any]) -> dict[str, Any]:
        blocking = validate_turn_state(document["turnState"]) if document.get("turnState") else ["UPLOAD_REQUIRED"]
        gate_status = "ready_for_solver" if not blocking else "review_required"
        recommendation = document.get("recommendation")
        state = document["state"]
        if recommendation:
            status = recommendation["status"]
            if status in {"solved", "confirmation_required", "no_safe_solution"}:
                state = status
            elif status == "blocked_unverified_rule":
                state = "rules_blocked"
        return {
            "schemaVersion": "0.6.0",
            "analysisId": document["analysisId"],
            "state": state,
            "stateVersion": document["stateVersion"],
            "locale": document["locale"],
            "consent": document["consent"],
            "createdAt": document["createdAt"],
            "lastActivityAt": document["lastActivityAt"],
            "expiresAt": document["expiresAt"],
            "gate": {"status": gate_status, "blockingReasonCodes": blocking},
            "assets": [
                {"kind": kind, "available": bool(value)}
                for kind, value in sorted(document.get("assets", {}).items())
                if kind in {"normalised", "thumbnail", "annotated"}
            ],
            "review": {
                "unresolvedCount": len(blocking),
                "conflictCount": 0,
                "recommendationInvalidated": bool(document.get("recommendationInvalidated")),
            },
            "recognitionResultId": f"rec_{document['analysisId'][4:]}" if document.get("turnState") else None,
            "manualEditorSessionId": f"edit_{document['analysisId'][4:]}" if document.get("turnState") else None,
            "recommendation": None
            if recommendation is None
            else {"status": recommendation["status"], "candidateId": recommendation.get("candidateId")},
        }

    def _read_existing(self, analysis_id: str) -> dict[str, Any]:
        path = self._dir(analysis_id) / "session.json"
        if not path.exists():
            raise SessionError("API-AUTH-NOT-FOUND", "Analysis not found")
        return load_json(path)

    def _write(self, document: dict[str, Any]) -> None:
        dump_json(self._dir(document["analysisId"]) / "session.json", document)

    def _touch(self, document: dict[str, Any]) -> None:
        now = utc_now()
        hard = datetime.fromisoformat(document["hardExpiresAt"].replace("Z", "+00:00"))
        idle = min(now + timedelta(minutes=self.idle_minutes), hard)
        document["lastActivityAt"] = iso(now)
        document["expiresAt"] = iso(idle)

    def _assert_not_expired(self, document: dict[str, Any]) -> None:
        now = utc_now()
        expiry = datetime.fromisoformat(document["expiresAt"].replace("Z", "+00:00"))
        hard = datetime.fromisoformat(document["hardExpiresAt"].replace("Z", "+00:00"))
        if now >= expiry or now >= hard:
            raise SessionError("API-STATE-EXPIRED", "Analysis expired")

    @staticmethod
    def _authorise(document: dict[str, Any], token: str) -> None:
        if not token or not hmac.compare_digest(document["tokenHash"], SessionStore._hash(token)):
            raise SessionError("API-AUTH-TOKEN", "Invalid analysis token")

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _dir(self, analysis_id: str) -> Path:
        if not analysis_id.startswith("ana_") or any(ch in analysis_id for ch in "/\\."):
            raise SessionError("API-AUTH-NOT-FOUND", "Analysis not found")
        return self.root / analysis_id
