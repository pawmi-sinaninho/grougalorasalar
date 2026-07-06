from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

import grougal_solver.app as app_module
from grougal_solver.session_store import SessionStore
from grougal_solver.util import SPELLS


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _rate(value: int | float, denominator: int | float) -> float:
    return round(float(value) / max(float(denominator), 1.0), 6)


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(statistics.fmean(values), 3)


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[int(0.95 * (len(ordered) - 1))], 3)


def _resolve_path(raw: str, *, base_dir: Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    if (base_dir / path).exists():
        return (base_dir / path).resolve()
    return (REPO_ROOT / path).resolve()


def _entry_id(path: Path, index: int) -> str:
    return f"{index:04d}-{path.stem}"


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError("Manifest JSON array expected")
        return [dict(item) for item in data]
    entries: list[dict[str, Any]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            entries.append(dict(json.loads(stripped)))
    return entries


def collect_entries(*, images: list[str], manifest: Path | None) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if manifest is not None:
        manifest_entries = _load_manifest(manifest)
        for index, item in enumerate(manifest_entries, start=1):
            image_value = item.get("image") or item.get("imagePath") or item.get("path")
            if not image_value:
                raise ValueError(f"Manifest entry {index} is missing image/imagePath/path")
            path = _resolve_path(str(image_value), base_dir=manifest.parent)
            item["image"] = str(path)
            item.setdefault("id", _entry_id(path, index))
            entries.append(item)

    for raw in images:
        path = _resolve_path(raw, base_dir=Path.cwd())
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.suffix.lower() in IMAGE_SUFFIXES:
                    entries.append({"id": _entry_id(child, len(entries) + 1), "image": str(child)})
        else:
            entries.append({"id": _entry_id(path, len(entries) + 1), "image": str(path)})

    return entries


def _spell_values(turn_state: dict[str, Any]) -> dict[str, int | None]:
    spells = ((turn_state.get("resources") or {}).get("spells") or {})
    return {
        spell: spells.get(spell, {}).get("value")
        if isinstance(spells.get(spell, {}).get("value"), int)
        else None
        for spell in SPELLS
    }


def _compare_expected(entry: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    expected = entry.get("expected") or {}
    if not isinstance(expected, dict) or not expected:
        return {"adjudicated": False, "checks": {}, "mismatches": []}

    checks: dict[str, bool] = {}
    mismatches: list[str] = []

    def check(name: str, actual: Any, wanted: Any) -> None:
        ok = actual == wanted
        checks[name] = ok
        if not ok:
            mismatches.append(name)

    if "player" in expected:
        check("player", observed.get("player"), expected.get("player"))
    if "pillarCount" in expected:
        check("pillarCount", observed.get("pillarCount"), expected.get("pillarCount"))
    if "blackOffsetCount" in expected:
        check("blackOffsetCount", observed.get("blackOffsetCount"), expected.get("blackOffsetCount"))
    if "whiteOffsetCount" in expected:
        check("whiteOffsetCount", observed.get("whiteOffsetCount"), expected.get("whiteOffsetCount"))
    if "charges" in expected:
        expected_charges = {spell: expected["charges"].get(spell) for spell in SPELLS}
        check("charges", observed.get("charges"), expected_charges)
    if "raceOutcome" in expected:
        check("raceOutcome", observed.get("raceOutcome"), expected.get("raceOutcome"))
    if "recommendationStatus" in expected:
        check("recommendationStatus", observed.get("recommendationStatus"), expected.get("recommendationStatus"))

    return {"adjudicated": True, "checks": checks, "mismatches": mismatches}


def _upload_one(client: TestClient, entry: dict[str, Any]) -> dict[str, Any]:
    image_path = Path(entry["image"])
    if not image_path.exists():
        return {
            "id": entry.get("id"),
            "image": str(image_path),
            "ok": False,
            "error": "IMAGE-NOT-FOUND",
        }

    created = client.post(
        "/api/v1/analyses",
        json={
            "schemaVersion": "0.8.0",
            "locale": "fr",
            "retentionConsent": "ephemeral_only",
            "qualityImprovementConsent": False,
        },
    )
    if created.status_code != 201:
        return {
            "id": entry.get("id"),
            "image": str(image_path),
            "ok": False,
            "error": f"CREATE-{created.status_code}",
            "body": created.text[:500],
        }

    created_body = created.json()
    analysis_id = created_body["session"]["analysisId"]
    token = created_body["accessToken"]
    state_version = int(created_body["session"]["stateVersion"])

    with image_path.open("rb") as handle:
        uploaded = client.post(
            f"/api/v1/analyses/{analysis_id}/image",
            headers=_headers(token),
            files={"file": (image_path.name, handle, "image/png")},
            data={"expectedStateVersion": str(state_version)},
        )

    if uploaded.status_code != 202:
        client.delete(f"/api/v1/analyses/{analysis_id}", headers=_headers(token))
        return {
            "id": entry.get("id"),
            "image": str(image_path),
            "ok": False,
            "error": f"UPLOAD-{uploaded.status_code}",
            "body": uploaded.text[:500],
        }

    envelope = uploaded.json()
    client.delete(f"/api/v1/analyses/{analysis_id}", headers=_headers(token))

    turn_state = envelope.get("turnState") or {}
    recognition = envelope.get("recognition") or {}
    recommendation = envelope.get("recommendation") or {}
    expected = recommendation.get("expected") or {}
    glyphs = turn_state.get("glyphs") or {}
    performance = envelope.get("performance") or {}

    observed = {
        "player": (turn_state.get("player") or {}).get("current"),
        "pillarCount": len(turn_state.get("pillars") or []),
        "blackOffsetCount": len(glyphs.get("blackOffsets") or []),
        "whiteOffsetCount": len(glyphs.get("whiteOffsets") or []),
        "charges": _spell_values(turn_state),
        "recognitionStatus": recognition.get("status"),
        "registrationAccepted": bool((recognition.get("registration") or {}).get("accepted")),
        "gateStatus": ((envelope.get("session") or {}).get("gate") or {}).get("status"),
        "recommendationStatus": recommendation.get("status"),
        "raceOutcome": expected.get("raceOutcome"),
        "whitePillarIds": expected.get("whitePillarIds") or [],
        "rechargedSpells": expected.get("rechargedSpells") or [],
        "serverScreenshotToStateMs": performance.get("serverScreenshotToStateMs"),
        "totalRecognitionMs": (recognition.get("metrics") or {}).get("totalRecognitionMs"),
        "ocrInvoked": bool((recognition.get("metrics") or {}).get("ocrInvoked")),
        "matchedFixtureId": recognition.get("matchedFixtureId"),
    }

    return {
        "id": entry.get("id"),
        "image": str(image_path),
        "ok": True,
        "observed": observed,
        "comparison": _compare_expected(entry, observed),
    }


def run_replay(
    entries: list[dict[str, Any]],
    *,
    out_dir: Path,
    session_dir: Path | None = None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    details_path = out_dir / "real_image_replay_details.jsonl"
    summary_path = out_dir / "real_image_replay_summary.json"

    if session_dir is None:
        temp_context = tempfile.TemporaryDirectory(prefix="grougal-real-replay-")
        session_root = Path(temp_context.name)
    else:
        temp_context = None
        session_root = session_dir
        session_root.mkdir(parents=True, exist_ok=True)

    try:
        app_module.store = SessionStore(session_root)
        client = TestClient(app_module.app)

        details: list[dict[str, Any]] = []
        with details_path.open("w", encoding="utf-8") as handle:
            for entry in entries:
                result = _upload_one(client, entry)
                details.append(result)
                handle.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    finally:
        if temp_context is not None:
            temp_context.cleanup()

    processed = [item for item in details if item.get("ok")]
    failed = [item for item in details if not item.get("ok")]

    recognition_statuses = Counter()
    gate_statuses = Counter()
    recommendation_statuses = Counter()
    race_outcomes = Counter()
    matched_fixtures = Counter()
    server_times: list[float] = []
    recognition_times: list[float] = []
    accepted = 0
    player_detected = 0
    ocr_invoked = 0
    recharge_count = 0
    white_hits_total = 0
    adjudicated = 0
    field_checks = Counter()
    field_matches = Counter()
    mismatch_entries = 0

    for item in processed:
        observed = item["observed"]
        recognition_statuses[str(observed.get("recognitionStatus"))] += 1
        gate_statuses[str(observed.get("gateStatus"))] += 1
        recommendation_statuses[str(observed.get("recommendationStatus"))] += 1
        race_outcomes[str(observed.get("raceOutcome") or "unknown")] += 1
        if observed.get("matchedFixtureId"):
            matched_fixtures[str(observed["matchedFixtureId"])] += 1

        accepted += int(bool(observed.get("registrationAccepted")))
        player_detected += int(bool(observed.get("player")))
        ocr_invoked += int(bool(observed.get("ocrInvoked")))
        recharge_count += int(bool(observed.get("rechargedSpells")))
        white_hits_total += len(observed.get("whitePillarIds") or [])

        for key in ("serverScreenshotToStateMs", "totalRecognitionMs"):
            value = observed.get(key)
            if isinstance(value, (int, float)):
                if key == "serverScreenshotToStateMs":
                    server_times.append(float(value))
                else:
                    recognition_times.append(float(value))

        comparison = item.get("comparison") or {}
        if comparison.get("adjudicated"):
            adjudicated += 1
            if comparison.get("mismatches"):
                mismatch_entries += 1
            for name, ok in (comparison.get("checks") or {}).items():
                field_checks[name] += 1
                if ok:
                    field_matches[name] += 1

    field_accuracy = {
        name: _rate(field_matches[name], count)
        for name, count in sorted(field_checks.items())
    }

    summary = {
        "images": len(entries),
        "processed": len(processed),
        "failedUploads": len(failed),
        "recognition": {
            "statuses": dict(recognition_statuses.most_common()),
            "registrationAcceptedRate": _rate(accepted, len(processed)),
            "playerDetectedRate": _rate(player_detected, len(processed)),
            "ocrInvokedRate": _rate(ocr_invoked, len(processed)),
            "matchedFixtures": dict(matched_fixtures.most_common()),
        },
        "session": {
            "gateStatuses": dict(gate_statuses.most_common()),
            "readyForSolverRate": _rate(gate_statuses["ready_for_solver"], len(processed)),
        },
        "recommendation": {
            "statuses": dict(recommendation_statuses.most_common()),
            "raceOutcomes": dict(race_outcomes.most_common()),
            "crocoburioAdvanceRate": _rate(race_outcomes["crocoburio_advance"], len(processed)),
            "dragonAdvanceRate": _rate(race_outcomes["dragon_advance"], len(processed)),
            "neutralRate": _rate(race_outcomes["neutral"], len(processed)),
            "unknownRate": _rate(race_outcomes["unknown"], len(processed)),
            "rechargeRate": _rate(recharge_count, len(processed)),
            "averageWhiteHits": round(white_hits_total / max(len(processed), 1), 3),
        },
        "adjudication": {
            "adjudicatedImages": adjudicated,
            "fieldAccuracy": field_accuracy,
            "mismatchEntries": mismatch_entries,
            "mismatchEntryRate": _rate(mismatch_entries, adjudicated),
        },
        "timingMs": {
            "serverScreenshotToStateMean": _mean(server_times),
            "serverScreenshotToStateP95": _p95(server_times),
            "totalRecognitionMean": _mean(recognition_times),
            "totalRecognitionP95": _p95(recognition_times),
        },
        "outputs": {
            "detailsJsonl": str(details_path),
            "summaryJson": str(summary_path),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay real screenshots through the API recognition + solver pipeline.")
    parser.add_argument("images", nargs="*", help="Image files or folders. Folders are scanned recursively.")
    parser.add_argument("--manifest", type=Path, help="JSON or JSONL manifest with image/path and optional expected fields.")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "stats" / "real-image-replay")
    parser.add_argument("--session-dir", type=Path, default=None)
    args = parser.parse_args()

    entries = collect_entries(images=args.images, manifest=args.manifest)
    if not entries:
        raise SystemExit("No images found. Pass image files/folders or --manifest.")

    summary = run_replay(entries, out_dir=args.out_dir, session_dir=args.session_dir)
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
