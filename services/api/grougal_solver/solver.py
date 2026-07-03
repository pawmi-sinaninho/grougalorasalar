from __future__ import annotations

import time
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .profiles import RuleAuthority, compile_profile, load_rule_statuses
from .util import (
    SPELLS,
    action_sort_key,
    add_cell,
    canonical_action_signature,
    cell_dict,
    cell_tuple,
    deep_copy,
    sequence_key,
    sign,
    unique_preserve,
)


class CapacityExceeded(RuntimeError):
    pass


def resolve_next_charges(
    charges_at_turn_start: int,
    casts_this_turn: int,
    matching_white_hits: int,
    maximum: int = 4,
) -> int:
    """Normative end-of-turn charge transition."""
    remaining = charges_at_turn_start - casts_this_turn
    if remaining < 0:
        raise ValueError("charges may never fall below zero during a turn")
    return min(maximum, remaining + matching_white_hits)


@dataclass(frozen=True)
class ArenaSets:
    walkable: frozenset[tuple[int, int]]
    boundary: frozenset[tuple[int, int]]
    occluded: frozenset[tuple[int, int]]
    blocked: frozenset[tuple[int, int]]

    @classmethod
    def from_given(cls, arena: dict[str, Any]) -> "ArenaSets":
        return cls(
            frozenset(cell_tuple(c) for c in arena.get("walkable", [])),
            frozenset(cell_tuple(c) for c in arena.get("boundaryUnverified", [])),
            frozenset(cell_tuple(c) for c in arena.get("occludedUnknown", [])),
            frozenset(cell_tuple(c) for c in arena.get("permanentBlocked", [])),
        )

    def classification(self, cell: tuple[int, int]) -> str:
        if cell in self.walkable:
            return "walkable"
        if cell in self.boundary:
            return "boundary"
        if cell in self.occluded:
            return "occluded"
        if cell in self.blocked:
            return "blocked"
        return "outside"


@dataclass
class SearchNode:
    cell: tuple[int, int]
    budget: int
    actions: list[dict[str, Any]]
    cast_counts: dict[str, int]
    spell_values: dict[str, int | None]


class DeterministicSolver:
    """Implementation of the Phase-3 deterministic contract.

    The solver accepts the compact fixture/manual-editor shape used by Phase 3.
    API adapters convert the full TurnState into this shape. Conditional actions
    are diagnostics and are never inserted into the definite graph.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.rule_statuses = load_rule_statuses(project_root)

    def solve_given(
        self,
        given: dict[str, Any],
        *,
        focus_rule_ids: list[str] | None = None,
        fixture_mode: bool = False,
        max_nodes: int = 100_000,
        timeout_seconds: float = 2.0,
        prune_dominated: bool = False,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        authority = RuleAuthority(self.rule_statuses, focus_rule_ids)
        action_budget = given.get("resources", {}).get("actionBudget")
        profile = compile_profile(
            self.project_root,
            given.get("profileOverrides", {}),
            action_budget=action_budget,
            fixture_mode=fixture_mode,
        )
        arena = ArenaSets.from_given(given.get("arena", {}))
        pillars = list(given.get("pillars", []))
        pillar_by_cell = {cell_tuple(p["cell"]): p for p in pillars}

        invalid_reasons = self._invalid_reasons(given, arena, pillars, profile)
        if invalid_reasons:
            return self._empty_result("invalid_state", invalid_reasons, profile)

        blocking_reasons = self._preflight_blocking_reasons(given, profile)
        if blocking_reasons:
            return self._empty_result("blocked_unverified_rule", blocking_reasons, profile)

        budget = self._resolved_budget(given, profile)
        assert budget is not None
        movement_cost = profile["resources"]["movementActionCost"]
        current = cell_tuple(given["player"]["current"])
        spells = given["resources"]["spells"]
        # A calibrated "available" cue proves a conservative lower bound of
        # one cast even when the exact positive count is not visually legible.
        spell_values = {
            spell: (
                spells[spell].get("value")
                if spells[spell].get("value") is not None
                else (1 if spells[spell].get("availability") == "available" else None)
            )
            for spell in SPELLS
        }

        # Geometry depends on the source cell and which numeric spell charges
        # remain, not on the order used to reach that state. Caching this pure
        # enumeration removes the dominant repeated pillar/path scan while
        # preserving the complete deterministic graph.
        action_cache: dict[
            tuple[tuple[int, int], tuple[bool, ...]],
            tuple[list[dict[str, Any]], list[dict[str, Any]]],
        ] = {}

        def enumerate_node(
            source: tuple[int, int],
            cast_counts: dict[str, int],
            values: dict[str, int | None],
            remaining_budget: int,
        ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
            if profile["resources"]["trackingMode"] != "numeric":
                return self._enumerate_actions(
                    source, given, profile, arena, pillar_by_cell, cast_counts,
                    values, remaining_budget, authority, fixture_mode,
                )
            key = (
                source,
                tuple(
                    values.get(spell) is not None
                    and values[spell] >= profile["resources"]["chargeCostPerCast"][spell]
                    for spell in SPELLS
                ),
            )
            cached = action_cache.get(key)
            if cached is None:
                cached = self._enumerate_actions(
                    source, given, profile, arena, pillar_by_cell, cast_counts,
                    values, remaining_budget, authority, fixture_mode,
                )
                action_cache[key] = cached
            return cached

        root_definite, root_conditional = enumerate_node(
            current,
            {spell: 0 for spell in SPELLS},
            spell_values,
            budget,
        )

        # Some unresolved root actions are themselves sufficient to block.
        root_block_reasons = self._conditional_reason_codes(root_conditional)

        queue: deque[SearchNode] = deque(
            [
                SearchNode(
                    cell=current,
                    budget=budget,
                    actions=[],
                    cast_counts={spell: 0 for spell in SPELLS},
                    spell_values=spell_values,
                )
            ]
        )
        visited: dict[tuple[Any, ...], str] = {}
        pareto_by_cell: dict[tuple[int, int], list[tuple[int, tuple[int, ...], str]]] = {
            current: [(budget, tuple(int(spell_values[spell] or 0) for spell in SPELLS), "")]
        }
        terminal_candidates: list[dict[str, Any]] = []
        conditional_sequences: list[dict[str, Any]] = []
        node_count = 0

        while queue:
            if time.perf_counter() - started > timeout_seconds:
                raise CapacityExceeded("solver timeout")
            node = queue.popleft()
            node_count += 1
            if node_count > max_nodes:
                raise CapacityExceeded("solver node cap exceeded")

            # At least one movement spell is mandatory every round. Standing
            # still is never a legal terminal, even when it would avoid black.
            if node.actions:
                terminal_candidates.append(
                    self._resolve_terminal(
                        node,
                        given,
                        profile,
                        pillar_by_cell,
                        authority,
                        fixture_mode,
                    )
                )

            if node.budget < movement_cost:
                continue

            definite, conditional = enumerate_node(
                node.cell,
                node.cast_counts,
                node.spell_values,
                node.budget,
            )
            for conditional_action in conditional:
                conditional_sequences.append(
                    {
                        "signature": sequence_key(node.actions + [conditional_action]),
                        "ruleIds": conditional_action.get("conditionalRuleIds", []),
                    }
                )
            for action in definite:
                next_counts = dict(node.cast_counts)
                next_counts[action["spell"]] += 1
                next_values = dict(node.spell_values)
                if profile["resources"]["trackingMode"] == "numeric":
                    charge_cost = profile["resources"]["chargeCostPerCast"].get(action["spell"])
                    if charge_cost is None:
                        continue
                    current_value = next_values.get(action["spell"])
                    if current_value is None or current_value < charge_cost:
                        continue
                    next_values[action["spell"]] = current_value - charge_cost
                actions = node.actions + [action]
                next_node = SearchNode(
                    cell=cell_tuple(action["destinationCell"]),
                    budget=node.budget - movement_cost,
                    actions=actions,
                    cast_counts=next_counts,
                    spell_values=next_values,
                )
                state_key = (
                    next_node.cell,
                    next_node.budget,
                    tuple(next_counts[s] for s in SPELLS),
                    tuple(next_values[s] for s in SPELLS),
                )
                seq = sequence_key(actions)
                if prune_dominated and profile["resources"]["trackingMode"] == "numeric":
                    values_key = tuple(int(next_values[spell] or 0) for spell in SPELLS)
                    dominated = any(
                        prior_budget >= next_node.budget
                        and all(prior >= value for prior, value in zip(prior_values, values_key))
                        and (
                            prior_budget > next_node.budget
                            or prior_values != values_key
                            or prior_sequence <= seq
                        )
                        for prior_budget, prior_values, prior_sequence in pareto_by_cell.get(next_node.cell, [])
                    )
                    if dominated:
                        continue
                    pareto_by_cell.setdefault(next_node.cell, []).append(
                        (next_node.budget, values_key, seq)
                    )
                previous = visited.get(state_key)
                if previous is None or seq < previous:
                    visited[state_key] = seq
                    queue.append(next_node)

        safe = [c for c in terminal_candidates if self._is_black_safe(c)]
        unresolved_terminals = [c for c in terminal_candidates if c["classification"] == "conditional"]

        # Determine status. Unknown/conditional branches are blocking when they
        # can affect completeness. Confirmable rules yield confirmation_required.
        reasons: list[str] = []
        status = "solved"
        if root_block_reasons:
            status = "blocked_unverified_rule"
            reasons.extend(root_block_reasons)
        if conditional_sequences and status == "solved":
            status = "blocked_unverified_rule"
            reasons.extend(self._conditional_reason_codes_from_sequences(conditional_sequences))

        # Never expose an adverse black-ending sequence as a recommendation.
        # No white collision is required: a moved, black-safe ending is valid.
        best_pool = safe
        ordered = sorted(best_pool, key=lambda c: self._ranking_key(c, arena))
        recommendations = ordered[:3]

        confirmable_rules = unique_preserve(
            rule_id
            for candidate in recommendations
            for rule_id in candidate.get("ruleIds", [])
            if authority.classify(rule_id, fixture_mode) == "confirmable"
        )
        blocking_rules = unique_preserve(
            rule_id
            for candidate in recommendations + unresolved_terminals
            for rule_id in candidate.get("ruleIds", [])
            if authority.classify(rule_id, fixture_mode) == "blocking"
        )
        if blocking_rules:
            status = "blocked_unverified_rule"
            reasons.extend(self._rule_reason(rule_id) for rule_id in blocking_rules)
        elif confirmable_rules and status != "blocked_unverified_rule":
            status = "confirmation_required"
            reasons.extend(self._rule_reason(rule_id, confirm=True) for rule_id in confirmable_rules)

        if status == "solved" and not safe and not root_block_reasons and not conditional_sequences:
            status = "no_safe_solution"
            reasons = ["S-NO-LEGAL-MOVEMENT"] if not root_definite else ["S-NO-SAFE-SOLUTION"]

        if status == "solved":
            reasons = ["S-SOLVED-CONTRACT"]
        elif not reasons:
            reasons = ["S-BLOCK-UNVERIFIED-RULE"]

        recommendation = self._build_recommendation(
            status,
            unique_preserve(reasons),
            recommendations,
            profile,
            len(root_definite),
            len(root_conditional),
            terminal_candidates,
            conditional_sequences,
            node_count,
        )
        recommendation["diagnostics"] = {
            "definiteRootActions": [a["canonicalSignature"] for a in root_definite],
            "conditionalRootActions": [
                {
                    "signature": a["canonicalSignature"],
                    "ruleIds": a.get("conditionalRuleIds", []),
                }
                for a in root_conditional
            ],
            "terminalCandidates": terminal_candidates,
            "conditionalSequences": conditional_sequences,
            "nodeCount": node_count,
        }
        return recommendation

    def _invalid_reasons(
        self,
        given: dict[str, Any],
        arena: ArenaSets,
        pillars: list[dict[str, Any]],
        profile: dict[str, Any],
    ) -> list[str]:
        reasons: list[str] = []
        flags = given.get("flags", {})
        if flags.get("multiplayerDetected"):
            reasons.append("S-INVALID-MULTIPLAYER")
        cells = [cell_tuple(p["cell"]) for p in pillars]
        if len(cells) != len(set(cells)):
            reasons.append("S-INVALID-DUPLICATE-PILLAR")
        player = given.get("player", {}).get("current")
        if player is None or arena.classification(cell_tuple(player)) in {"outside", "blocked"}:
            reasons.append("S-INVALID-PLAYER-CELL")
        state_budget = given.get("resources", {}).get("actionBudget")
        profile_budget = profile.get("resources", {}).get("actionBudgetPerTurn")
        if (
            profile.get("purpose") != "specification_test_only"
            and state_budget is not None
            and profile_budget is not None
            and state_budget != profile_budget
        ):
            reasons.append("S-INVALID-BUDGET-CONFLICT")
        return reasons

    def _preflight_blocking_reasons(self, given: dict[str, Any], profile: dict[str, Any]) -> list[str]:
        reasons: list[str] = []
        flags = given.get("flags", {})
        if not flags.get("anchorConfirmed", False):
            reasons.append("S-BLOCK-ANCHOR")
        if self._resolved_budget(given, profile) is None:
            reasons.append("S-BLOCK-ACTION-BUDGET")
        spells = given.get("resources", {}).get("spells", {})
        if any(not spells.get(spell, {}).get("confirmed", False) for spell in SPELLS):
            reasons.append("S-BLOCK-SPELL-STATE")
        if (
            not flags.get("criticalFieldsConfirmed", False)
            and not flags.get("solverInputComplete", False)
            and "S-BLOCK-SPELL-STATE" not in reasons
        ):
            reasons.append("S-BLOCK-CRITICAL-FIELDS")
        return reasons

    def _resolved_budget(self, given: dict[str, Any], profile: dict[str, Any]) -> int | None:
        state_budget = given.get("resources", {}).get("actionBudget")
        if state_budget is not None:
            return int(state_budget)
        profile_budget = profile.get("resources", {}).get("actionBudgetPerTurn")
        return int(profile_budget) if profile_budget is not None else None

    def _spell_usable(
        self,
        spell: str,
        given: dict[str, Any],
        profile: dict[str, Any],
        cast_counts: dict[str, int],
        spell_values: dict[str, int | None],
        authority: RuleAuthority,
        fixture_mode: bool,
    ) -> tuple[str, list[str]]:
        spell_state = given["resources"]["spells"][spell]
        availability = spell_state.get("availability", "unknown")
        if availability == "unavailable":
            return "invalid", []
        if availability == "unknown":
            return "conditional", ["R-025"]
        mode = profile["resources"]["trackingMode"]
        if mode == "unknown":
            return "conditional", ["R-029"]
        if mode == "numeric":
            charge_cost = profile["resources"]["chargeCostPerCast"].get(spell)
            value = spell_values.get(spell)
            if charge_cost is None or value is None:
                return "conditional", ["R-026", "R-029"]
            if value < charge_cost:
                return "invalid", []
        elif cast_counts[spell] >= 1:
            return "conditional", ["R-048"]
        return "definite", []

    def _enumerate_actions(
        self,
        source: tuple[int, int],
        given: dict[str, Any],
        profile: dict[str, Any],
        arena: ArenaSets,
        pillar_by_cell: dict[tuple[int, int], dict[str, Any]],
        cast_counts: dict[str, int],
        spell_values: dict[str, int | None],
        budget: int,
        authority: RuleAuthority,
        fixture_mode: bool,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        movement_cost = profile["resources"]["movementActionCost"]
        if budget < movement_cost:
            return [], []
        definite: list[dict[str, Any]] = []
        conditional: list[dict[str, Any]] = []
        pillars = sorted(pillar_by_cell.values(), key=lambda p: (*cell_tuple(p["cell"]), p["id"]))

        for spell in SPELLS:
            resource_state, resource_rules = self._spell_usable(
                spell, given, profile, cast_counts, spell_values, authority, fixture_mode
            )
            if resource_state == "invalid":
                continue
            candidates: list[dict[str, Any]] = []
            if spell == "indecision":
                metric = profile["movement"][spell]["contactMetric"]
                offsets = [(-1, 0), (0, -1), (0, 1), (1, 0)]
                mechanic_rules: list[str] = []
                if metric == "chebyshev":
                    offsets = [
                        (-1, -1), (-1, 0), (-1, 1),
                        (0, -1), (0, 1),
                        (1, -1), (1, 0), (1, 1),
                    ]
                elif metric == "unknown":
                    mechanic_rules = ["R-039"]
                for dx, dy in offsets:
                    target = source[0] + dx, source[1] + dy
                    candidates.append(
                        self._make_action(spell, source, target, "cell", target, None, mechanic_rules)
                    )
            else:
                for pillar in pillars:
                    candidate = self._pillar_action(spell, source, pillar, profile)
                    if candidate is not None:
                        candidates.append(candidate)

            for action in candidates:
                rules = list(resource_rules) + list(action.get("conditionalRuleIds", []))
                action = self._apply_movement_constraints(
                    action, source, profile, arena, pillar_by_cell
                )
                if action is None:
                    continue
                destination = cell_tuple(action["destinationCell"])
                cell_class = arena.classification(destination)
                if cell_class in {"blocked", "outside"}:
                    continue
                if cell_class == "boundary" and not fixture_mode:
                    rules.append("ARENA-BOUNDARY")
                elif cell_class == "occluded":
                    rules.append("ARENA-OCCLUDED")

                # Every spell must end on a free cell. Indécision therefore
                # rejects adjacent pillar cells just like all other spells.
                if destination in pillar_by_cell:
                    occupancy = profile["movement"][spell].get("destinationOccupancy", "unknown")
                    if occupancy == "invalid":
                        continue
                    if occupancy == "unknown":
                        rules.append("R-034")

                if resource_state == "conditional":
                    rules.extend(resource_rules)
                action["conditionalRuleIds"] = unique_preserve(rules)
                if rules:
                    conditional.append(action)
                else:
                    definite.append(action)

        definite.sort(key=action_sort_key)
        conditional.sort(key=action_sort_key)
        return definite, conditional

    def _pillar_action(
        self,
        spell: str,
        source: tuple[int, int],
        pillar: dict[str, Any],
        profile: dict[str, Any],
    ) -> dict[str, Any] | None:
        cfg = profile["movement"][spell]
        target = cell_tuple(pillar["cell"])
        dx, dy = target[0] - source[0], target[1] - source[1]
        rules: list[str] = []

        target_type = cfg.get("targetPillarType", "unknown")
        if target_type == "matching_spell_type" and pillar["spellType"] != spell:
            return None
        if target_type == "unknown":
            rules.append("R-044")

        alignment = self._alignment(dx, dy)
        if spell == "repulsion":
            allowed = cfg.get("allowedAlignments")
            if allowed is None:
                rules.append("R-042")
            elif alignment not in allowed:
                return None
        else:
            required = cfg.get("alignment")
            if required == "cardinal" and alignment != "cardinal":
                return None
            if required == "cardinal_or_diagonal" and alignment not in {"cardinal", "diagonal"}:
                return None
            if required == "unknown":
                rules.append("R-041" if spell == "reflection" else "R-017")

        range_metric = cfg.get("rangeMetric")
        distance = self._distance(dx, dy, range_metric)
        if distance is None:
            rules.append({"reflection": "R-040", "repulsion": "R-042", "attraction": "R-043"}[spell])
        else:
            minimum, maximum = cfg.get("minRange"), cfg.get("maxRange")
            if minimum is None or maximum is None:
                rules.append({"reflection": "R-011", "repulsion": "R-013", "attraction": "R-015"}[spell])
            elif distance < minimum or distance > maximum:
                return None

        if cfg.get("lineOfSight") == "unknown":
            rules.append("R-045")
        if cfg.get("pathMode") == "unknown":
            rules.extend(["R-054"] if spell == "reflection" else ["R-033", "R-049"])
        if cfg.get("edgeMode") == "unknown":
            rules.append("R-035")

        if spell == "reflection":
            destination = (2 * target[0] - source[0], 2 * target[1] - source[1])
        elif spell == "repulsion":
            unit = self._normalised_direction(source[0] - target[0], source[1] - target[1])
            if unit is None:
                return None
            alignment_distance_key = (
                "cardinalDistance" if alignment == "cardinal" else "diagonalDistance"
            )
            move_distance = cfg.get(alignment_distance_key)
            if move_distance is None:
                rules.append("R-014")
                move_distance = cfg.get("distance", 3)
            destination = source[0] + move_distance * unit[0], source[1] + move_distance * unit[1]
        else:
            unit = self._normalised_direction(dx, dy)
            if unit is None:
                return None
            move_distance = cfg.get("distance")
            if move_distance is None:
                rules.append("R-016")
                move_distance = 3
            target_distance = self._aligned_steps(dx, dy)
            if target_distance is not None and target_distance <= move_distance:
                behaviour = cfg.get("shortRangeBehaviour")
                if behaviour == "unknown":
                    rules.extend(["R-016", "ATTRACTION-SHORT-RANGE"])
                    destination = source[0] + move_distance * unit[0], source[1] + move_distance * unit[1]
                elif behaviour == "action_invalid":
                    return None
                elif behaviour == "stop_adjacent_to_pillar":
                    destination = target[0] - unit[0], target[1] - unit[1]
                else:
                    destination = source[0] + move_distance * unit[0], source[1] + move_distance * unit[1]
            else:
                destination = source[0] + move_distance * unit[0], source[1] + move_distance * unit[1]

        return self._make_action(spell, source, target, "pillar", destination, pillar["id"], rules)

    def _apply_movement_constraints(
        self,
        action: dict[str, Any],
        source: tuple[int, int],
        profile: dict[str, Any],
        arena: ArenaSets,
        pillar_by_cell: dict[tuple[int, int], dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Apply blocker and edge semantics to a generated movement action."""
        spell = action["spell"]
        if spell == "indecision":
            return action
        cfg = profile["movement"][spell]
        destination = cell_tuple(action["destinationCell"])
        target = cell_tuple(action["targetCell"])
        if spell == "attraction":
            target_dx, target_dy = target[0] - source[0], target[1] - source[1]
            target_steps = self._aligned_steps(target_dx, target_dy)
            target_unit = self._normalised_direction(target_dx, target_dy)
            if target_steps is None or target_unit is None:
                return None
            # Attrait cannot be cast through a nearer pillar or obstacle, even
            # when that blocker lies beyond the three cells the player moves.
            for distance in range(1, target_steps):
                cell = (
                    source[0] + distance * target_unit[0],
                    source[1] + distance * target_unit[1],
                )
                if cell in pillar_by_cell or arena.classification(cell) in {"blocked", "outside"}:
                    return None
        if spell == "attraction" and destination == source:
            # An adjacent target is legal: stopping immediately before that
            # pillar leaves the player on the current cell.
            return action
        dx, dy = destination[0] - source[0], destination[1] - source[1]
        steps = self._aligned_steps(dx, dy)
        unit = self._normalised_direction(dx, dy)
        if steps is None or unit is None:
            return None

        last_free = source
        for distance in range(1, steps + 1):
            cell = source[0] + distance * unit[0], source[1] + distance * unit[1]

            # A diagonal Rejet crosses the corner shared by two orthogonal
            # cells. Dofus rejects the complete push when either side of that
            # corner is occupied or outside the arena; checking only the
            # diagonal landing cells permits impossible corner clipping.
            if spell == "repulsion" and unit[0] != 0 and unit[1] != 0:
                previous = (
                    source[0] + (distance - 1) * unit[0],
                    source[1] + (distance - 1) * unit[1],
                )
                diagonal_side_cells = (
                    (previous[0] + unit[0], previous[1]),
                    (previous[0], previous[1] + unit[1]),
                )
                if any(
                    side_cell in pillar_by_cell
                    or arena.classification(side_cell) in {"blocked", "outside"}
                    for side_cell in diagonal_side_cells
                ):
                    return None

            target_pillar_exempt = spell == "reflection" and cell == target
            blocked = arena.classification(cell) in {"blocked", "outside"}
            blocked = blocked or (cell in pillar_by_cell and not target_pillar_exempt)
            if blocked:
                if cfg.get("pathMode") == "truncate_before_blocker" or cfg.get("edgeMode") == "truncate_to_last_walkable":
                    if last_free == source:
                        return None
                    action["destinationCell"] = cell_dict(last_free)
                    return action
                return None
            last_free = cell
        return action

    def _make_action(
        self,
        spell: str,
        source: tuple[int, int],
        target: tuple[int, int],
        target_kind: str,
        destination: tuple[int, int],
        pillar_id: str | None,
        conditional_rules: Iterable[str],
    ) -> dict[str, Any]:
        signature = canonical_action_signature(spell, target_kind, target, pillar_id)
        return {
            "actionId": f"act_{abs(hash((source, signature))) & 0xFFFFFFFF:08x}",
            "spell": spell,
            "sourceCell": cell_dict(source),
            "destinationCell": cell_dict(destination),
            "targetKind": target_kind,
            "targetCell": cell_dict(target),
            "targetPillarId": pillar_id,
            "canonicalSignature": signature,
            "conditionalRuleIds": unique_preserve(conditional_rules),
        }

    def _resolve_terminal(
        self,
        node: SearchNode,
        given: dict[str, Any],
        profile: dict[str, Any],
        pillar_by_cell: dict[tuple[int, int], dict[str, Any]],
        authority: RuleAuthority,
        fixture_mode: bool,
    ) -> dict[str, Any]:
        final = node.cell
        glyphs = given.get("glyphs", {})
        rules: list[str] = []
        black_ids: list[str] = []
        white_ids: list[str] = []

        physical_black = {cell_tuple(c) for c in glyphs.get("physicalBlackCells", [])}
        physical_white = {cell_tuple(c) for c in glyphs.get("physicalWhiteCells", [])}
        direct_black = final in physical_black
        direct_white = final in physical_white

        for offset in glyphs.get("blackOffsets", []):
            projected = final[0] + int(offset["dx"]), final[1] + int(offset["dy"])
            pillar = pillar_by_cell.get(projected)
            if pillar:
                black_ids.append(pillar["id"])
        for offset in glyphs.get("whiteOffsets", []):
            projected = final[0] + int(offset["dx"]), final[1] + int(offset["dy"])
            pillar = pillar_by_cell.get(projected)
            if pillar:
                white_ids.append(pillar["id"])

        race = "unknown"
        if direct_black:
            rules.append("R-020")
            race = profile["resolution"].get("centerBlackOutcome", "unknown")
        elif black_ids:
            if white_ids:
                rules.append("R-008")
                black_priority = profile["resolution"].get("blackPriority")
                race = "dragon_advance" if black_priority is not False else "crocoburio_advance"
            else:
                race = "dragon_advance"
        elif white_ids or direct_white:
            if direct_white:
                rules.append("R-021")
            outcome = profile["resolution"].get("whiteWithoutBlackOutcome")
            rules.append("R-051")
            race = "crocoburio_advance" if outcome == "crocoburio_advance_and_recharge" else "neutral"
        else:
            rules.append("R-019")
            race = profile["resolution"].get("noBlackNoWhiteOutcome", "unknown")

        if white_ids:
            counts = Counter(pillar_by_cell_by_id(pillar_by_cell)[pid]["spellType"] for pid in white_ids)
            if any(count > 1 for count in counts.values()) and profile["resources"].get("multipleWhiteHitsStack") is None:
                rules.append("R-031")

        classification = "definite"
        if any(authority.classify(rule_id, fixture_mode) != "authoritative" for rule_id in rules):
            classification = "conditional"

        next_spell_state: dict[str, int | None] = {}
        white_counts = Counter(
            pillar_by_cell_by_id(pillar_by_cell)[pid]["spellType"] for pid in white_ids
        )
        for spell in SPELLS:
            value = node.spell_values.get(spell)
            if value is None:
                next_spell_state[spell] = None
                continue
            recharge = white_counts.get(spell, 0)
            if direct_white and profile["resources"].get("centerWhiteRecharge") == "all_spells_plus_one":
                recharge += 1
            maximum = profile["resources"]["maxCharges"].get(spell)
            start_value = value + node.cast_counts.get(spell, 0)
            next_spell_state[spell] = (
                resolve_next_charges(start_value, node.cast_counts.get(spell, 0), recharge, maximum)
                if maximum is not None
                else value + recharge
            )

        return {
            "sequence": [action["canonicalSignature"] for action in node.actions],
            "actions": deep_copy(node.actions),
            "classification": classification,
            "finalCell": cell_dict(final),
            "raceOutcome": race,
            "terminalFightState": "unknown",
            "blackPillarIds": sorted(black_ids),
            "whitePillarIds": sorted(white_ids),
            "rechargedSpells": sorted(
                {
                    pillar_by_cell_by_id(pillar_by_cell)[pid]["spellType"]
                    for pid in white_ids
                }
            ),
            "nextSpellState": next_spell_state,
            "directCenterEffect": "black_adverse" if direct_black else ("white_recharge" if direct_white else "none"),
            "ruleIds": unique_preserve(rules),
            "remainingBudget": node.budget,
            "castCount": len(node.actions),
        }

    def _ranking_key(self, candidate: dict[str, Any], arena: ArenaSets) -> tuple[Any, ...]:
        race_rank = {
            "crocoburio_advance": 0,
            "neutral": 1,
            "unknown": 2,
            "dragon_advance": 3,
        }.get(candidate["raceOutcome"], 4)
        cell = cell_tuple(candidate["finalCell"])
        mobility = sum(
            1
            for offset in [(-1, 0), (0, -1), (0, 1), (1, 0)]
            if arena.classification((cell[0] + offset[0], cell[1] + offset[1])) == "walkable"
        )
        next_spell_state = candidate.get("nextSpellState") or {}
        known_charges = [
            int(next_spell_state[spell])
            for spell in SPELLS
            if isinstance(next_spell_state.get(spell), int)
        ]
        resource_unknown = len(known_charges) != len(SPELLS)
        minimum_charge = min(known_charges) if known_charges else -1
        total_charges = sum(known_charges)
        return (
            # All candidates reaching ranking are already black-safe. Spending
            # fewer spell charges is the primary tactical objective.
            candidate["castCount"],
            resource_unknown,
            -minimum_charge,
            -total_charges,
            race_rank,
            -mobility,
            tuple(candidate["sequence"]),
        )

    @staticmethod
    def _is_black_safe(candidate: dict[str, Any]) -> bool:
        return (
            not candidate.get("blackPillarIds")
            and candidate.get("directCenterEffect") != "black_adverse"
        )

    def _build_recommendation(
        self,
        status: str,
        reasons: list[str],
        recommendations: list[dict[str, Any]],
        profile: dict[str, Any],
        root_definite_count: int,
        root_conditional_count: int,
        terminals: list[dict[str, Any]],
        conditional_sequences: list[dict[str, Any]],
        node_count: int,
    ) -> dict[str, Any]:
        best = recommendations[0] if recommendations else None
        actions: list[dict[str, Any]] = []
        if best:
            for index, action in enumerate(best["actions"], start=1):
                target = action.get("targetPillarId") or f"case {action['targetCell']['x']},{action['targetCell']['y']}"
                actions.append(
                    {
                        "order": index,
                        **{k: v for k, v in action.items() if k != "conditionalRuleIds"},
                        "pathCells": self._path_cells(
                            cell_tuple(action["sourceCell"]),
                            cell_tuple(action["destinationCell"]),
                        ),
                        "instruction": f"{action['spell']} → {target}",
                    }
                )
        expected = {
            "finalCell": best["finalCell"] if best else None,
            "raceOutcome": best["raceOutcome"] if best else "unknown",
            "terminalFightState": best["terminalFightState"] if best else "unknown",
            "blackPillarIds": best["blackPillarIds"] if best else [],
            "whitePillarIds": best["whitePillarIds"] if best else [],
            "rechargedSpells": best["rechargedSpells"] if best else [],
            "directCenterEffect": best["directCenterEffect"] if best else "unknown",
            "nextSpellState": best.get("nextSpellState") if best else None,
        }
        alternatives = []
        for candidate in recommendations[1:3]:
            alternatives.append(
                {
                    "sequence": candidate["sequence"],
                    "finalCell": candidate["finalCell"],
                    "raceOutcome": candidate["raceOutcome"],
                }
            )
        return {
            "schemaVersion": "0.5.0",
            "status": status,
            "statusReasonCodes": reasons,
            "rulesProfileId": profile["profileId"],
            "rankingPolicyId": "ranking-lexicographic-v0.5.0",
            "candidateId": f"cand_{abs(hash(tuple(best['sequence']))) & 0xFFFFFFFF:08x}" if best else None,
            "sequenceKey": "->".join(best["sequence"]) if best else None,
            "actions": actions,
            "expected": expected,
            "confidence": {"visual": 1.0, "mechanical": 1.0 if status == "solved" else 0.5, "overall": 1.0 if status == "solved" else 0.5},
            "assumptions": [],
            "searchSummary": {
                "definiteRootActions": root_definite_count,
                "conditionalRootActions": root_conditional_count,
                "definiteTerminalCandidates": sum(c["classification"] == "definite" for c in terminals),
                "conditionalTerminalCandidates": sum(c["classification"] == "conditional" for c in terminals) + len(conditional_sequences),
                "adverseDefiniteCandidates": sum(
                    c["classification"] == "definite" and not self._is_black_safe(c)
                    for c in terminals
                ),
                "safeDefiniteCandidates": sum(
                    c["classification"] == "definite" and self._is_black_safe(c)
                    for c in terminals
                ),
            },
            "rankingKey": list(self._ranking_key(best, ArenaSets(frozenset(), frozenset(), frozenset(), frozenset()))) if best else None,
            "trace": [
                {
                    "index": 0,
                    "type": "preflight",
                    "message": "Preflight completed.",
                    "ruleIds": [],
                    "data": {"nodeCount": node_count},
                },
                {
                    "index": 1,
                    "type": "final_status",
                    "message": f"Solver status: {status}",
                    "ruleIds": [],
                    "data": {"reasonCodes": reasons},
                },
            ],
            "alternatives": alternatives,
            "warnings": [],
        }

    @staticmethod
    def _path_cells(source: tuple[int, int], destination: tuple[int, int]) -> list[dict[str, int]]:
        dx, dy = destination[0] - source[0], destination[1] - source[1]
        steps = max(abs(dx), abs(dy))
        if steps == 0:
            return [cell_dict(source)]
        ux, uy = sign(dx), sign(dy)
        if dx != 0 and dy != 0 and abs(dx) != abs(dy):
            return [cell_dict(source), cell_dict(destination)]
        return [cell_dict((source[0] + index * ux, source[1] + index * uy)) for index in range(steps + 1)]

    def _empty_result(self, status: str, reasons: list[str], profile: dict[str, Any]) -> dict[str, Any]:
        return {
            "schemaVersion": "0.5.0",
            "status": status,
            "statusReasonCodes": reasons,
            "rulesProfileId": profile["profileId"],
            "rankingPolicyId": "ranking-lexicographic-v0.5.0",
            "candidateId": None,
            "sequenceKey": None,
            "actions": [],
            "expected": {
                "finalCell": None,
                "raceOutcome": "unknown",
                "terminalFightState": "unknown",
                "blackPillarIds": [],
                "whitePillarIds": [],
                "rechargedSpells": [],
                "directCenterEffect": "unknown",
                "nextSpellState": None,
            },
            "confidence": {"visual": 0.0, "mechanical": 0.0, "overall": 0.0},
            "assumptions": [],
            "searchSummary": {
                "definiteRootActions": 0,
                "conditionalRootActions": 0,
                "definiteTerminalCandidates": 0,
                "conditionalTerminalCandidates": 0,
                "adverseDefiniteCandidates": 0,
                "safeDefiniteCandidates": 0,
            },
            "rankingKey": None,
            "trace": [
                {
                    "index": 0,
                    "type": "preflight",
                    "message": "Preflight blocked.",
                    "ruleIds": [],
                    "data": {"reasonCodes": reasons},
                }
            ],
            "alternatives": [],
            "warnings": [],
            "diagnostics": {
                "definiteRootActions": [],
                "conditionalRootActions": [],
                "terminalCandidates": [],
                "conditionalSequences": [],
                "nodeCount": 0,
            },
        }

    @staticmethod
    def _alignment(dx: int, dy: int) -> str | None:
        if dx == 0 and dy != 0 or dy == 0 and dx != 0:
            return "cardinal"
        if dx != 0 and abs(dx) == abs(dy):
            return "diagonal"
        return None

    @staticmethod
    def _aligned_steps(dx: int, dy: int) -> int | None:
        if dx == 0:
            return abs(dy)
        if dy == 0:
            return abs(dx)
        if abs(dx) == abs(dy):
            return abs(dx)
        return None

    def _distance(self, dx: int, dy: int, metric: str | None) -> int | None:
        if metric == "manhattan":
            return abs(dx) + abs(dy)
        if metric == "chebyshev":
            return max(abs(dx), abs(dy))
        if metric == "aligned_steps":
            return self._aligned_steps(dx, dy)
        return None

    def _normalised_direction(self, dx: int, dy: int) -> tuple[int, int] | None:
        alignment = self._alignment(dx, dy)
        if alignment is None:
            return None
        return sign(dx), sign(dy)

    def _conditional_reason_codes(self, actions: list[dict[str, Any]]) -> list[str]:
        return unique_preserve(
            self._rule_reason(rule_id)
            for action in actions
            for rule_id in action.get("conditionalRuleIds", [])
        )

    def _conditional_reason_codes_from_sequences(self, sequences: list[dict[str, Any]]) -> list[str]:
        return unique_preserve(
            self._rule_reason(rule_id)
            for sequence in sequences
            for rule_id in sequence.get("ruleIds", [])
        )

    @staticmethod
    def _rule_reason(rule_id: str, confirm: bool = False) -> str:
        explicit = {
            "R-008": "S-CONFIRM-BLACK-PRIORITY",
            "R-019": "S-CONFIRM-NO-COLLISION",
            "R-031": "S-BLOCK-WHITE-STACKING",
            "R-033": "S-BLOCK-PATH-MODE",
            "R-034": "S-BLOCK-OCCUPIED-DESTINATION",
            "R-039": "S-BLOCK-INDECISION-METRIC",
            "R-044": "S-BLOCK-TARGET-PILLAR-TYPE",
            "R-045": "S-BLOCK-LINE-OF-SIGHT",
            "R-046": "S-BLOCK-STATIONARY-REFERENCE",
            "R-048": "S-BLOCK-REPEAT-AVAILABILITY-ONLY",
            "R-054": "S-BLOCK-PATH-MODE",
            "ARENA-BOUNDARY": "S-CONFIRM-BOUNDARY",
            "ARENA-OCCLUDED": "S-BLOCK-OCCLUDED-CELL",
            "ATTRACTION-SHORT-RANGE": "S-BLOCK-ATTRACTION-SHORT-RANGE",
        }
        if rule_id in explicit:
            return explicit[rule_id]
        prefix = "S-CONFIRM" if confirm else "S-BLOCK"
        return f"{prefix}-{rule_id}"


def pillar_by_cell_by_id(pillar_by_cell: dict[tuple[int, int], dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {pillar["id"]: pillar for pillar in pillar_by_cell.values()}
