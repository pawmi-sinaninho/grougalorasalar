from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path
from urllib import request

API_URL = "http://127.0.0.1:8000/api/v1"
CANDIDATE_ENDPOINTS = ["/analysis", "/analyze", "/arena/analyze", "/recommend", "/recommendations", "/solve"]


def post_json(url: str, payload: dict) -> tuple[int, bytes, dict[str, str]]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with request.urlopen(req, timeout=120) as res:
        return res.status, res.read(), dict(res.headers.items())


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python tools/benchmark_recommendation_perf.py payload.json [endpoint]")
        return 2
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    endpoint = sys.argv[2] if len(sys.argv) >= 3 else None
    endpoints = [endpoint] if endpoint else CANDIDATE_ENDPOINTS
    found = None
    for ep in endpoints:
        try:
            status, body, headers = post_json(f"{API_URL}{ep}", payload)
            if status == 200:
                found = ep
                print(f"Endpoint OK: {ep} | bytes={len(body)} | perf={headers.get('X-Grougal-Perf')}")
                break
        except Exception as exc:
            print(f"Skip {ep}: {exc}")
    if not found:
        print("No candidate endpoint worked. Pass the exact endpoint as second argument.")
        return 1
    durations = []
    for i in range(8):
        start = time.perf_counter()
        status, body, headers = post_json(f"{API_URL}{found}", payload)
        duration_ms = (time.perf_counter() - start) * 1000
        durations.append(duration_ms)
        print(f"{i + 1:02d}: {duration_ms:8.1f} ms | status={status} | bytes={len(body)} | {headers.get('X-Grougal-Perf')}")
    print(f"median_ms={statistics.median(durations):.1f}")
    print(f"min_ms={min(durations):.1f}")
    print(f"max_ms={max(durations):.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
