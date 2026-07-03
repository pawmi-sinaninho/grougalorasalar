from __future__ import annotations
from pathlib import Path
from datetime import datetime
import re
import shutil

ROOT = Path.cwd()
BACKUP_DIR = ROOT / '.patch_backups' / f"spell_rules_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def backup(path: Path) -> None:
    target = BACKUP_DIR / path.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)

def apply_change(rel_path: str, label: str, mode: str, old: str, new: str) -> None:
    path = ROOT / rel_path
    if not path.exists():
        raise SystemExit(f'Missing expected file: {rel_path}')
    text = path.read_text(encoding='utf-8')
    original = text
    if mode == 'exact':
        count = text.count(old)
        if count != 1:
            raise SystemExit(f'{label}: expected exactly 1 occurrence in {rel_path}, found {count}')
        text = text.replace(old, new, 1)
    elif mode == 'all':
        count = text.count(old)
        if count == 0:
            return
        text = text.replace(old, new)
    elif mode == 'regex':
        text, count = re.subn(old, new, text, count=1, flags=re.S)
        if count != 1:
            raise SystemExit(f'{label}: expected exactly 1 regex replacement in {rel_path}, found {count}')
    else:
        raise SystemExit(f'Unknown replacement mode: {mode}')
    if text != original:
        backup(path)
        path.write_text(text, encoding='utf-8')
        print(f'updated: {rel_path} — {label}')

CHANGES = [
    ('services/api/grougal_solver/solver.py', 'solver diagonal alignment handling', 'exact', '            if required == "cardinal" and alignment != "cardinal":\n                return None\n            if required == "cardinal_or_diagonal" and alignment not in {"cardinal", "diagonal"}:\n                return None\n            if required == "unknown":\n                rules.append("R-041" if spell == "reflection" else "R-017")', '            if required == "cardinal" and alignment != "cardinal":\n                return None\n            if required == "diagonal" and alignment != "diagonal":\n                return None\n            if required == "cardinal_or_diagonal" and alignment not in {"cardinal", "diagonal"}:\n                return None\n            if required == "unknown":\n                rules.append("R-041" if spell == "reflection" else "R-017")'),
    ('services/api/grougal_solver/solver.py', 'solver repulsion movement formula', 'regex', '        elif spell == "repulsion":\n            unit = self\\._normalised_direction\\(source\\[0\\] - target\\[0\\], source\\[1\\] - target\\[1\\]\\)\n            if unit is None:\n                return None\n            final_distance_key = \\(\n                "cardinalFinalDistanceFromPillar"\n                if alignment == "cardinal"\n                else "diagonalFinalDistanceFromPillar"\n            \\)\n            final_distance = cfg\\.get\\(final_distance_key\\)\n            target_distance = self\\._aligned_steps\\(target\\[0\\] - source\\[0\\], target\\[1\\] - source\\[1\\]\\)\n            if final_distance is None or target_distance is None:\n                rules\\.append\\("R-014"\\)\n                final_distance = cfg\\.get\\("distance", 3\\)\n                target_distance = 0\n            # Rejet places the player at a fixed radius from the target pillar;\n            # it does not add that radius to the player\'s current distance\\.\n            move_distance = max\\(0, final_distance - target_distance\\)\n            destination = source\\[0\\] \\+ move_distance \\* unit\\[0\\], source\\[1\\] \\+ move_distance \\* unit\\[1\\]', '        elif spell == "repulsion":\n            unit = self._normalised_direction(source[0] - target[0], source[1] - target[1])\n            if unit is None:\n                return None\n            distance_key = "cardinalDistance" if alignment == "cardinal" else "diagonalDistance"\n            move_distance = cfg.get(distance_key)\n            if move_distance is None:\n                rules.append("R-014")\n                move_distance = 3 if alignment == "cardinal" else 2\n            # Rejet uses the targeted pillar only to define a valid direction.\n            # The movement distance is always measured from the current player\n            # cell: 3 cells on a cardinal line, 2 diagonal steps on a diagonal.\n            destination = source[0] + move_distance * unit[0], source[1] + move_distance * unit[1]'),
    ('services/api/grougal_solver/solver.py', 'solver repulsion zero-displacement comment', 'regex', '        if spell == "repulsion" and destination == source:\n            # A diagonal range-two target already places the player at the\n            # verified two-cell final radius\\. The cast is mechanically legal,\n            # but does not satisfy the mandatory movement for ending the turn\\.\n            return action', '        if spell == "repulsion" and destination == source:\n            # Rejet normally displaces from the current player cell. Keep this\n            # defensive branch for malformed profiles or manually overridden\n            # fixtures without converting it into an end-turn movement.\n            return action'),
    ('services/api/grougal_solver/profiles.py', 'profiles reflection alignment', 'exact', '            "reflection": {\n                "targetPillarType": "any_pillar",\n                "rangeMetric": "manhattan",\n                "minRange": 2,\n                "maxRange": 2,\n                "alignment": "cardinal_or_diagonal",\n                "destinationOccupancy": "invalid",\n            },', '            "reflection": {\n                "targetPillarType": "any_pillar",\n                "rangeMetric": "manhattan",\n                "minRange": 2,\n                "maxRange": 2,\n                "alignment": "diagonal",\n                "destinationOccupancy": "invalid",\n            },'),
    ('services/api/grougal_solver/profiles.py', 'profiles repulsion distance keys', 'exact', '            "repulsion": {\n                "targetPillarType": "any_pillar",\n                "rangeMetric": "aligned_steps",\n                "minRange": 1,\n                "maxRange": 2,\n                "cardinalFinalDistanceFromPillar": 3,\n                "diagonalFinalDistanceFromPillar": 2,\n                "pathMode": "fail_if_blocked",\n                "edgeMode": "invalid",\n                "destinationOccupancy": "invalid",\n            },', '            "repulsion": {\n                "targetPillarType": "any_pillar",\n                "rangeMetric": "aligned_steps",\n                "minRange": 1,\n                "maxRange": 2,\n                "cardinalDistance": 3,\n                "diagonalDistance": 2,\n                "pathMode": "fail_if_blocked",\n                "edgeMode": "invalid",\n                "destinationOccupancy": "invalid",\n            },'),
    ('examples/rules-profile.verified.json', 'profile json reflection alignment', 'exact', '    "alignment": "cardinal_or_diagonal",', '    "alignment": "diagonal",'),
    ('examples/rules-profile.verified.json', 'profile json cleanup cardinal final distance', 'all', '"cardinalFinalDistanceFromPillar": 3', '"cardinalDistance": 3'),
    ('examples/rules-profile.verified.json', 'profile json cleanup diagonal final distance', 'all', '"diagonalFinalDistanceFromPillar": 2', '"diagonalDistance": 2'),
    ('services/api/tests/test_spell_targeting_geometry.py', 'tests reflection profile expected alignment', 'all', '    assert reflection["alignment"] == "cardinal_or_diagonal"', '    assert reflection["alignment"] == "diagonal"'),
    ('services/api/tests/test_spell_targeting_geometry.py', 'tests repulsion profile expected keys', 'all', '    assert repulsion["cardinalFinalDistanceFromPillar"] == 3\n\n    assert repulsion["diagonalFinalDistanceFromPillar"] == 2', '    assert repulsion["cardinalDistance"] == 3\n\n    assert repulsion["diagonalDistance"] == 2'),
    ('services/api/tests/test_spell_targeting_geometry.py', 'tests repulsion override key', 'all', '  ("movement.repulsion.diagonalFinalDistanceFromPillar", 3),', '  ("movement.repulsion.diagonalDistance", 3),'),
    ('services/api/tests/test_spell_targeting_geometry.py', 'tests reflection target geometry', 'regex', 'def test_reflet_targets_exactly_the_eight_radius_two_pillar_cells\\(\\) -> None:\n.*?\ndef test_reflet_rejects_wrong_range_and_non_aligned_pillars\\(\\) -> None:', 'def test_reflet_targets_only_adjacent_diagonal_pillar_cells() -> None:\n\n    expected = {(-1, -1), (-1, 1), (1, -1), (1, 1)}\n\n    pillars = [\n\n        _pillar(f"P{index:02d}", cell, "attraction")\n\n        for index, cell in enumerate(sorted(expected), start=1)\n\n    ]\n\n    actions = _actions_for("reflection", pillars)\n\n    assert len(actions) == 4\n\n    assert _target_cells(actions) == expected\n\n    assert all(action["targetKind"] == "pillar" for action in actions)\n\n    assert all(\n\n        _destination(action)\n\n        == (\n\n            2 * action["targetCell"]["x"],\n\n            2 * action["targetCell"]["y"],\n\n        )\n\n        for action in actions\n\n    )\n\n\ndef test_reflet_rejects_wrong_range_and_non_aligned_pillars() -> None:'),
    ('services/api/tests/test_spell_targeting_geometry.py', 'tests reflection rejection cases', 'exact', '    pillars = [\n\n    _pillar("P_NEAR", (1, 0), "attraction"),\n\n    _pillar("P_FAR", (3, 0), "attraction"),\n\n    _pillar("P_OFF_AXIS", (2, 1), "attraction"),\n\n    ]\n\n    assert _actions_for("reflection", pillars) == []', '    pillars = [\n\n    _pillar("P_CARDINAL_RANGE_TWO", (2, 0), "attraction"),\n\n    _pillar("P_FAR_DIAGONAL", (2, 2), "attraction"),\n\n    _pillar("P_OFF_AXIS", (2, 1), "attraction"),\n\n    _pillar("P_CARDINAL_NEAR", (1, 0), "attraction"),\n\n    ]\n\n    assert _actions_for("reflection", pillars) == []'),
    ('services/api/tests/test_spell_targeting_geometry.py', 'tests repulsion destination matrix', 'exact', '    assert all(action["targetKind"] == "pillar" for action in actions)\n\n\ndef test_rejet_rejects_radius_three_and_non_aligned_pillars() -> None:', '    assert all(action["targetKind"] == "pillar" for action in actions)\n\n\n@pytest.mark.parametrize(\n    ("target", "expected_destination"),\n    (\n        ((-1, 0), (3, 0)),\n        ((-2, 0), (3, 0)),\n        ((1, 0), (-3, 0)),\n        ((2, 0), (-3, 0)),\n        ((0, -1), (0, 3)),\n        ((0, -2), (0, 3)),\n        ((0, 1), (0, -3)),\n        ((0, 2), (0, -3)),\n        ((-1, -1), (2, 2)),\n        ((-2, -2), (2, 2)),\n        ((1, 1), (-2, -2)),\n        ((2, 2), (-2, -2)),\n    ),\n)\ndef test_rejet_moves_from_current_position_not_from_pillar_radius(\n    target: tuple[int, int],\n    expected_destination: tuple[int, int],\n) -> None:\n\n    actions = _actions_for("repulsion", [_pillar("P_TARGET", target, "reflection")])\n\n    assert len(actions) == 1\n\n    assert _destination(actions[0]) == expected_destination\n\n\ndef test_rejet_rejects_radius_three_and_non_aligned_pillars() -> None:'),
]

for change in CHANGES:
    apply_change(*change)

print('')
print('Applied verified Reflet/Rejet spell rules patch.')
print(f'Backups written to: {BACKUP_DIR.relative_to(ROOT)}')
