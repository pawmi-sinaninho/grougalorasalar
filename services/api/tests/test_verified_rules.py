from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from grougal_solver.profiles import RuleAuthority, compile_profile
from grougal_solver.fixtures import get_fixture, run_fixture
from grougal_solver.solver import (
    ArenaSets,
    DeterministicSolver,
    SearchNode,
    resolve_next_charges,
)
from grougal_solver.spellbar import recognise_spell_bar

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SPELLS = ("indecision", "reflection", "repulsion", "attraction")


def _profile() -> dict:
    return compile_profile(PROJECT_ROOT)


def _arena(cells: set[tuple[int, int]], blocked: set[tuple[int, int]] | None = None) -> ArenaSets:
    return ArenaSets(frozenset(cells), frozenset(), frozenset(), frozenset(blocked or set()))


def _given(value: int = 2) -> dict:
    return {
        "resources": {
            "actionBudget": 12,
            "spells": {
                spell: {
                    "availability": "available" if value else "unavailable",
                    "value": value,
                    "confirmed": True,
                }
                for spell in SPELLS
            },
        }
    }


def test_profile_has_twelve_ap_one_ap_cost_and_two_to_four_charges() -> None:
    profile = _profile()
    assert profile["resources"]["actionBudgetPerTurn"] == 12
    assert profile["resources"]["movementActionCost"] == 1
    assert set(profile["resources"]["initialCharges"].values()) == {2}
    assert set(profile["resources"]["maxCharges"].values()) == {4}
    assert set(profile["resources"]["chargeCostPerCast"].values()) == {1}


def test_active_solver_fixture_catalog_contains_only_verified_rules() -> None:
    catalog = json.loads((PROJECT_ROOT / "data/solver/verified-rules-fixtures.v1.0.0.json").read_text(encoding="utf-8"))
    assert catalog["catalogId"] == "verified-rules-2026-06-30"
    assert catalog["fixtureCount"] == len(catalog["fixtures"]) == 1
    assert len(catalog["indecision"]["legalOffsets"]) == 4
    assert len(catalog["indecision"]["illegalDiagonalOffsets"]) == 4


def test_solver_spends_one_ap_per_cast_from_the_twelve_ap_budget() -> None:
    result = run_fixture(PROJECT_ROOT, get_fixture(PROJECT_ROOT, "F-101"))
    two_cast = [item for item in result["diagnostics"]["terminalCandidates"] if item["castCount"] == 2]
    assert two_cast
    assert all(item["remainingBudget"] == 10 for item in two_cast)


def test_solver_requires_movement_but_uses_the_fewest_safe_charges() -> None:
    result = run_fixture(PROJECT_ROOT, get_fixture(PROJECT_ROOT, "F-101"))

    assert result["status"] == "solved"
    assert len(result["actions"]) == 1
    assert result["expected"]["blackPillarIds"] == []
    assert result["expected"]["whitePillarIds"] == []
    assert result["expected"]["nextSpellState"]["indecision"] == 1
    assert all(
        candidate["castCount"] >= 1
        for candidate in result["diagnostics"]["terminalCandidates"]
    )


def test_solver_never_recommends_a_black_adverse_fallback() -> None:
    fixture = deepcopy(get_fixture(PROJECT_ROOT, "F-101"))
    fixture["given"]["glyphs"]["physicalBlackCells"] = deepcopy(
        fixture["given"]["arena"]["walkable"]
    )

    result = run_fixture(PROJECT_ROOT, fixture)

    assert result["status"] == "no_safe_solution"
    assert result["actions"] == []
    assert result["expected"]["finalCell"] is None


def test_white_is_optional_and_only_breaks_ties_between_equally_short_sequences() -> None:
    solver = DeterministicSolver(PROJECT_ROOT)
    arena = _arena({(0, 0), (1, 0), (2, 0)})
    one_cast_no_white = {
        "raceOutcome": "neutral", "finalCell": {"x": 1, "y": 0},
        "castCount": 1, "sequence": ["one"],
        "nextSpellState": {spell: 1 for spell in SPELLS},
    }
    two_cast_with_white = {
        "raceOutcome": "crocoburio_advance", "finalCell": {"x": 2, "y": 0},
        "castCount": 2, "sequence": ["two-a", "two-b"],
        "nextSpellState": {spell: 4 for spell in SPELLS},
    }
    one_cast_with_white = {
        **one_cast_no_white,
        "sequence": ["one-white"],
        "nextSpellState": {spell: 2 for spell in SPELLS},
    }

    assert solver._ranking_key(one_cast_no_white, arena) < solver._ranking_key(two_cast_with_white, arena)
    assert solver._ranking_key(one_cast_with_white, arena) < solver._ranking_key(one_cast_no_white, arena)
    assert solver._is_black_safe({"blackPillarIds": [], "directCenterEffect": "none"})
    assert not solver._is_black_safe({"blackPillarIds": ["P1"], "directCenterEffect": "none"})


def test_charge_conserving_ranking_stays_safe_and_one_cast_through_round_fourteen() -> None:
    solver = DeterministicSolver(PROJECT_ROOT)
    arena = _arena({(0, 0), (1, 0)})
    charges = {spell: 2 for spell in SPELLS}

    for round_number in range(1, 15):
        candidates = []
        for spell in SPELLS:
            if charges[spell] == 0:
                continue
            next_charges = dict(charges)
            next_charges[spell] -= 1
            # Half the rounds deliberately have no white recharge. On the
            # others an equally short white-safe ending restores the used spell.
            if round_number % 2 == 0:
                next_charges[spell] = min(4, next_charges[spell] + 1)
            candidates.append(
                {
                    "raceOutcome": "crocoburio_advance",
                    "finalCell": {"x": 1, "y": 0},
                    "castCount": 1,
                    "sequence": [spell],
                    "nextSpellState": next_charges,
                    "blackPillarIds": [],
                    "directCenterEffect": "none",
                }
            )

        assert candidates, f"no charge-conserving move remained in round {round_number}"
        best = min(candidates, key=lambda item: solver._ranking_key(item, arena))
        assert best["castCount"] == 1
        assert solver._is_black_safe(best)
        charges = best["nextSpellState"]
        assert all(0 <= value <= 4 for value in charges.values())

    assert sum(charges.values()) == 1


@pytest.mark.parametrize(
    ("start", "casts", "hits", "expected"),
    [(2, 2, 0, 0), (2, 0, 1, 3), (2, 0, 2, 4), (3, 0, 2, 4), (2, 2, 1, 1)],
)
def test_normative_charge_formula(start: int, casts: int, hits: int, expected: int) -> None:
    assert resolve_next_charges(start, casts, hits) == expected


def test_charge_formula_never_allows_casting_below_zero() -> None:
    with pytest.raises(ValueError):
        resolve_next_charges(0, 1, 1)


def test_zero_charge_spell_is_not_usable() -> None:
    solver = DeterministicSolver(PROJECT_ROOT)
    given = _given(0)
    state, rules = solver._spell_usable(
        "indecision", given, _profile(), {spell: 0 for spell in SPELLS},
        {spell: 0 for spell in SPELLS}, RuleAuthority({}), True,
    )
    assert state == "invalid"
    assert rules == []


def test_indecision_has_exactly_four_orthogonal_targets_and_no_diagonals() -> None:
    solver = DeterministicSolver(PROJECT_ROOT)
    cells = {(x, y) for x in range(-1, 2) for y in range(-1, 2)}
    definite, _ = solver._enumerate_actions(
        (0, 0), _given(), _profile(), _arena(cells), {},
        {spell: 0 for spell in SPELLS}, {spell: 2 for spell in SPELLS}, 12,
        RuleAuthority({}), True,
    )
    targets = {
        (item["targetCell"]["x"], item["targetCell"]["y"])
        for item in definite if item["spell"] == "indecision"
    }
    assert targets == {(-1, 0), (1, 0), (0, -1), (0, 1)}
    assert not targets & {(-1, -1), (-1, 1), (1, -1), (1, 1)}


def test_indecision_rejects_an_occupied_destination() -> None:
    solver = DeterministicSolver(PROJECT_ROOT)
    pillars = {(1, 0): {"id": "P", "cell": {"x": 1, "y": 0}, "spellType": "reflection"}}
    definite, _ = solver._enumerate_actions(
        (0, 0), _given(), _profile(), _arena({(0, 0), (1, 0)}), pillars,
        {spell: 0 for spell in SPELLS}, {spell: 2 for spell in SPELLS}, 12,
        RuleAuthority({}), True,
    )
    assert all(item["destinationCell"] != {"x": 1, "y": 0} for item in definite)


def test_reflet_accepts_any_pillar_at_exact_two_cardinal_or_diagonal() -> None:
    solver = DeterministicSolver(PROJECT_ROOT)
    profile = _profile()
    for target in ((2, 0), (1, 1)):
        pillar = {"id": "P", "cell": {"x": target[0], "y": target[1]}, "spellType": "attraction"}
        action = solver._pillar_action("reflection", (0, 0), pillar, profile)
        assert action is not None
    for target in ((1, 0), (2, 2)):
        assert solver._pillar_action(
            "reflection",
            (0, 0),
            {"id": "P", "cell": {"x": target[0], "y": target[1]}, "spellType": "attraction"},
            profile,
        ) is None


def test_rejet_is_invalid_at_obstacle_pillar_and_map_edge() -> None:
    solver = DeterministicSolver(PROJECT_ROOT)
    profile = _profile()
    pillar = {"id": "P", "cell": {"x": -1, "y": 0}, "spellType": "indecision"}
    raw = solver._pillar_action("repulsion", (0, 0), pillar, profile)
    assert raw is not None
    clear_arena = _arena({(-1, 0), (0, 0), (1, 0), (2, 0), (3, 0)})
    clear = solver._apply_movement_constraints(raw.copy(), (0, 0), profile, clear_arena, {(-1, 0): pillar})
    assert clear and clear["destinationCell"] == {"x": 3, "y": 0}

    edge = solver._apply_movement_constraints(
        raw.copy(), (0, 0), profile,
        _arena({(-1, 0), (0, 0), (1, 0), (2, 0)}),
        {(-1, 0): pillar},
    )
    assert edge is None
    obstacle = solver._apply_movement_constraints(
        raw.copy(), (0, 0), profile,
        _arena({(-1, 0), (0, 0), (1, 0), (3, 0)}, {(2, 0)}),
        {(-1, 0): pillar},
    )
    assert obstacle is None
    blocker = {"id": "B", "cell": {"x": 1, "y": 0}, "spellType": "reflection"}
    blocked_by_pillar = solver._apply_movement_constraints(
        raw.copy(), (0, 0), profile, clear_arena,
        {(-1, 0): pillar, (1, 0): blocker},
    )
    assert blocked_by_pillar is None


def test_rejet_moves_three_cardinal_cells_but_only_two_diagonal_cells() -> None:
    solver = DeterministicSolver(PROJECT_ROOT)
    profile = _profile()
    cardinal = solver._pillar_action(
        "repulsion", (0, 0),
        {"id": "C", "cell": {"x": -1, "y": 0}, "spellType": "indecision"},
        profile,
    )
    diagonal = solver._pillar_action(
        "repulsion", (0, 0),
        {"id": "D", "cell": {"x": -1, "y": -1}, "spellType": "indecision"},
        profile,
    )
    assert cardinal and cardinal["destinationCell"] == {"x": 3, "y": 0}
    assert diagonal and diagonal["destinationCell"] == {"x": 2, "y": 2}


def test_diagonal_rejet_is_invalid_when_either_corner_side_is_blocked() -> None:
    solver = DeterministicSolver(PROJECT_ROOT)
    profile = _profile()
    target = {"id": "T", "cell": {"x": -1, "y": -1}, "spellType": "indecision"}
    raw = solver._pillar_action("repulsion", (0, 0), target, profile)
    assert raw and raw["destinationCell"] == {"x": 2, "y": 2}
    walkable = {
        (-1, -1), (0, 0), (1, 0), (0, 1), (1, 1),
        (2, 1), (1, 2), (2, 2),
    }

    for blocker_cell in ((1, 0), (0, 1), (2, 1), (1, 2)):
        blocker = {
            "id": f"B{blocker_cell}",
            "cell": {"x": blocker_cell[0], "y": blocker_cell[1]},
            "spellType": "reflection",
        }
        constrained = solver._apply_movement_constraints(
            raw.copy(), (0, 0), profile, _arena(walkable),
            {(-1, -1): target, blocker_cell: blocker},
        )
        assert constrained is None


def test_attrait_stops_before_target_and_reflet_cannot_cross_another_pillar() -> None:
    solver = DeterministicSolver(PROJECT_ROOT)
    profile = _profile()
    target = {"id": "T", "cell": {"x": 2, "y": 0}, "spellType": "repulsion"}
    attraction = solver._pillar_action("attraction", (0, 0), target, profile)
    assert attraction and attraction["destinationCell"] == {"x": 1, "y": 0}
    target_at_three = {"id": "T3", "cell": {"x": 3, "y": 0}, "spellType": "reflection"}
    attraction_at_three = solver._pillar_action("attraction", (0, 0), target_at_three, profile)
    assert attraction_at_three and attraction_at_three["destinationCell"] == {"x": 2, "y": 0}
    reflection = solver._pillar_action("reflection", (0, 0), target, profile)
    blocker = {"id": "B", "cell": {"x": 3, "y": 0}, "spellType": "indecision"}
    constrained = solver._apply_movement_constraints(
        reflection, (0, 0), profile, _arena({(x, 0) for x in range(5)}), {(2, 0): target, (3, 0): blocker}
    )
    assert constrained is None


def test_terminal_projection_is_relative_and_recharges_a_used_spell_twice() -> None:
    solver = DeterministicSolver(PROJECT_ROOT)
    profile = _profile()
    pillars = {
        (2, 0): {"id": "W1", "cell": {"x": 2, "y": 0}, "spellType": "indecision"},
        (3, 0): {"id": "W2", "cell": {"x": 3, "y": 0}, "spellType": "indecision"},
    }
    node = SearchNode((1, 0), 10, [{"canonicalSignature": "a"}, {"canonicalSignature": "b"}],
                      {"indecision": 2, "reflection": 0, "repulsion": 0, "attraction": 0},
                      {"indecision": 0, "reflection": 2, "repulsion": 2, "attraction": 2})
    given = {"player": {"current": {"x": 0, "y": 0}}, "glyphs": {
        "blackOffsets": [], "whiteOffsets": [{"dx": 1, "dy": 0}, {"dx": 2, "dy": 0}],
        "physicalBlackCells": [], "physicalWhiteCells": []}}
    terminal = solver._resolve_terminal(node, given, profile, pillars, RuleAuthority({}), True)
    assert terminal["whitePillarIds"] == ["W1", "W2"]
    assert terminal["nextSpellState"]["indecision"] == 2


def test_spellbar_fixture_is_unmodified_and_recognised_automatically() -> None:
    fixture = json.loads((PROJECT_ROOT / "data/vision/spellbar-fixture.v1.0.0.json").read_text(encoding="utf-8"))
    path = PROJECT_ROOT / fixture["source"]["path"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == fixture["source"]["sha256"]
    assert path.stat().st_size == fixture["source"]["byteSize"]
    result = recognise_spell_bar(path)
    assert result is not None
    for spell, expected in fixture["expected"].items():
        assert result["spells"][spell]["availability"] == expected["availability"]
        assert result["spells"][spell]["value"] == expected["value"]


def test_ui_annotations_and_recommendations_use_only_binding_spell_names() -> None:
    source = (PROJECT_ROOT / "apps/web/app/page.tsx").read_text(encoding="utf-8")
    for required in ("Indécision", "Reflet", "Rejet", "Attrait"):
        assert required in source
    for obsolete in ("Réflexion", "Répulsion", "Attirance"):
        assert obsolete not in source
