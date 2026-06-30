#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from PIL import Image
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def validate_schema(rel: str) -> None:
    schema = load(rel)
    Draft202012Validator.check_schema(schema)


def validate_instance(instance_rel: str, schema_rel: str) -> None:
    instance = load(instance_rel)
    schema = load(schema_rel)
    errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        formatted = "\n".join(f"{instance_rel} {list(e.path)}: {e.message}" for e in errors)
        raise AssertionError(formatted)


def cell_tuple(c: dict) -> tuple[int, int]:
    return c["x"], c["y"]


def main() -> None:
    schema_files = [
        "schemas/arena-model.schema.json",
        "schemas/manual-editor-session.schema.json",
        "schemas/turn-state.schema.json",
        "schemas/recommendation.schema.json",
        "schemas/rules-profile.schema.json",
        "schemas/verification-observation.schema.json",
    ]
    for schema in schema_files:
        validate_schema(schema)

    validate_instance("data/arena/arena-model.draft-v0.5.0.json", "schemas/arena-model.schema.json")
    validate_instance("data/arena/reference-turn.manual.json", "schemas/turn-state.schema.json")
    validate_instance("examples/turn-state.synthetic.json", "schemas/turn-state.schema.json")
    validate_instance("examples/rules-profile.verified.json", "schemas/rules-profile.schema.json")
    validate_instance("examples/manual-editor-session.reference.json", "schemas/manual-editor-session.schema.json")

    image_path = ROOT / "assets/reference/user_reference.png"
    image = Image.open(image_path)
    assert image.size == (1951, 1267), image.size
    digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
    assert digest == "2756a38a4451117001dedeab2e4da14423d4aa50978bc4549c9ff0cb1340f976"

    arena = load("data/arena/arena-model.draft-v0.5.0.json")
    sets = arena["cellSets"]
    expected_counts = {
        "walkableConfirmed": 193,
        "walkableObserved": 34,
        "boundaryUnverified": 37,
        "occludedUnknown": 74,
        "permanentBlocked": 0,
    }
    assert {k: len(v) for k, v in sets.items()} == expected_counts

    all_cells: set[tuple[int, int]] = set()
    for name, values in sets.items():
        cells = {cell_tuple(c) for c in values}
        assert len(cells) == len(values), f"duplicates in {name}"
        assert all_cells.isdisjoint(cells), f"overlap in {name}"
        all_cells |= cells
    assert len(all_cells) == 338

    turn = load("data/arena/reference-turn.manual.json")
    pillars = turn["pillars"]
    pillar_cells = [cell_tuple(p["cell"]) for p in pillars]
    assert len(pillars) == 27
    assert len(set(pillar_cells)) == len(pillar_cells)
    player = cell_tuple(turn["player"]["currentCell"])
    assert player == (7, -1)
    assert player not in pillar_cells

    black = {(o["dx"], o["dy"]) for o in turn["glyphPattern"]["blackOffsets"]}
    white = {(o["dx"], o["dy"]) for o in turn["glyphPattern"]["whiteOffsets"]}
    assert black == {(-1, -1), (1, -1), (1, 1)}
    assert white == {(0, -3), (0, 2), (2, -1)}
    assert black.isdisjoint(white)
    assert not turn["glyphPattern"]["anchorConfirmed"]

    for c in pillar_cells + [player] + list(black) + list(white):
        assert c in all_cells, f"reference cell missing from arena model: {c}"

    with (ROOT / "data/arena/cell-classification.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 338

    for rel in [
        "assets/annotated/reference_grid_overlay.png",
        "assets/annotated/reference_entities_overlay.png",
        "assets/annotated/reference_regions_overlay.png",
        "assets/annotated/arena_mask_diagram.png",
    ]:
        p = ROOT / rel
        assert p.exists() and p.stat().st_size > 10_000, rel
        Image.open(p).verify()

    print("PASS: Phase-2 schemas, fixtures, mask invariants, image identity and diagrams validated.")


if __name__ == "__main__":
    main()
