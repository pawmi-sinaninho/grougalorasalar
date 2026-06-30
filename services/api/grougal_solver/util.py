from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

SPELLS = ("indecision", "reflection", "repulsion", "attraction")
SPELL_ORDER = {name: index for index, name in enumerate(SPELLS)}


def deep_copy(value: Any) -> Any:
    return copy.deepcopy(value)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cell_tuple(cell: dict[str, int] | tuple[int, int]) -> tuple[int, int]:
    if isinstance(cell, tuple):
        return cell
    return int(cell["x"]), int(cell["y"])


def cell_dict(cell: tuple[int, int] | None) -> dict[str, int] | None:
    if cell is None:
        return None
    return {"x": int(cell[0]), "y": int(cell[1])}


def add_cell(a: tuple[int, int], b: tuple[int, int]) -> tuple[int, int]:
    return a[0] + b[0], a[1] + b[1]


def sub_cell(a: tuple[int, int], b: tuple[int, int]) -> tuple[int, int]:
    return a[0] - b[0], a[1] - b[1]


def mul_cell(a: tuple[int, int], factor: int) -> tuple[int, int]:
    return a[0] * factor, a[1] * factor


def sign(value: int) -> int:
    return 0 if value == 0 else (1 if value > 0 else -1)


def canonical_action_signature(
    spell: str,
    target_kind: str,
    target_cell: tuple[int, int],
    pillar_id: str | None = None,
) -> str:
    return f"{spell}@{target_kind}:{target_cell[0]},{target_cell[1]}:{pillar_id or '-'}"


def action_sort_key(action: dict[str, Any]) -> tuple[Any, ...]:
    target = cell_tuple(action["targetCell"])
    return (
        SPELL_ORDER[action["spell"]],
        0 if action["targetKind"] == "cell" else 1,
        target[0],
        target[1],
        action.get("targetPillarId") or "",
    )


def sequence_key(actions: Iterable[dict[str, Any]]) -> str:
    return "->".join(action["canonicalSignature"] for action in actions)


def set_dotted(data: dict[str, Any], dotted: str, value: Any) -> None:
    cursor: dict[str, Any] = data
    parts = dotted.split(".")
    for part in parts[:-1]:
        next_value = cursor.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            cursor[part] = next_value
        cursor = next_value
    cursor[parts[-1]] = value


def unique_preserve(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
