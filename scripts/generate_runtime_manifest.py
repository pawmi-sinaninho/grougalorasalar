#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "data/rule-catalog.json",
    "data/arena/grougalorasalar.cells.json",
    "data/arena/grougalorasalar.boundary.json",
    "data/arena/grougalorasalar.registration.json",
    "data/arena/grougalorasalar.landmarks.json",
    "data/solver/ranking-policy.v0.5.0.json",
    "data/solver/rule-dependency-map.v0.5.0.json",
    "data/solver/status-precedence.v0.5.0.json",
    "data/vision/recognition-policy.v0.5.0.json",
    "data/vision/glyph-appearance-reference.v1.0.0.json",
    "data/vision/real-screenshot-fixtures.v0.8.0.json",
    "schemas/real-screenshot-fixture.schema.json",
    "packages/contracts/schema-manifest.json",
    "assets/reference/empty_arena.jpeg",
    "assets/reference/user_hidden_cells_annotation.png",
    "packages/fixtures/real/phase7/round-01.png",
    "packages/fixtures/real/phase7/round-02.png",
    "packages/fixtures/real/phase7/round-03.png",
    "packages/fixtures/real/phase7/round-04.png",
]
manifest = {"schemaVersion": "1.0.0", "releaseVersion": "1.0.0", "files": []}
for rel in FILES:
    raw = (ROOT / rel).read_bytes()
    manifest["files"].append({"path": rel, "sha256": hashlib.sha256(raw).hexdigest()})
output = ROOT / "data/runtime/runtime-manifest.v1.0.0.json"
output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"generated {output.relative_to(ROOT)} with {len(FILES)} files")

if "--refresh-historical" in sys.argv:
    for historical_path in sorted((ROOT / "data" / "runtime").glob("runtime-manifest.v*.json")):
        if historical_path == output:
            continue
        historical = json.loads(historical_path.read_text(encoding="utf-8"))
        for item in historical["files"]:
            path = ROOT / item["path"]
            if path.exists():
                item["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        historical_path.write_text(
            json.dumps(historical, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"refreshed {historical_path.relative_to(ROOT)}")
