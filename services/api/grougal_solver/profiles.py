from __future__ import annotations

from pathlib import Path
from typing import Any

from .util import deep_copy, load_json, set_dotted


class ProfileError(ValueError):
    pass


class RuleAuthority:
    AUTHORITATIVE = {"verified_multi_source", "verified_direct_observation"}
    CONFIRMABLE = {"single_source_supported"}
    BLOCKING = {"screenshot_observed", "hypothesis", "unknown"}

    def __init__(self, statuses: dict[str, str], focus_rule_ids: list[str] | None = None):
        self.statuses = statuses
        self.focus_rule_ids = set(focus_rule_ids or [])

    def status(self, rule_id: str, fixture_mode: bool = False) -> str:
        if fixture_mode and rule_id not in self.focus_rule_ids:
            return "verified_direct_observation"
        return self.statuses.get(rule_id, "unknown")

    def classify(self, rule_id: str, fixture_mode: bool = False) -> str:
        status = self.status(rule_id, fixture_mode)
        if status in self.AUTHORITATIVE:
            return "authoritative"
        if status in self.CONFIRMABLE:
            return "confirmable"
        return "blocking"


def load_rule_statuses(project_root: Path) -> dict[str, str]:
    catalogue = load_json(project_root / "data" / "rule-catalog.json")
    return {item["id"]: item["status"] for item in catalogue["rules"]}


def load_base_profile(project_root: Path) -> dict[str, Any]:
    return load_json(project_root / "examples" / "rules-profile.verified.json")


def compile_profile(
    project_root: Path,
    overrides: dict[str, Any] | None = None,
    *,
    action_budget: int | None = None,
    fixture_mode: bool = False,
) -> dict[str, Any]:
    profile = deep_copy(load_base_profile(project_root))
    for dotted, value in (overrides or {}).items():
        set_dotted(profile, dotted, value)
    if fixture_mode:
        profile["purpose"] = "specification_test_only"
        profile["profileId"] = "specification-test-explicit-v0.7.0"
        # Fixture states may exercise a smaller remaining budget, while the
        # verified per-turn profile remains fixed at 12 AP.
    validate_profile(profile)
    return profile


def validate_profile(profile: dict[str, Any]) -> None:
    resources = profile.get("resources", {})
    cost = resources.get("movementActionCost")
    if not isinstance(cost, int) or cost <= 0:
        raise ProfileError("movementActionCost must be a positive integer")
    if resources.get("actionBudgetPerTurn") != 12:
        raise ProfileError("actionBudgetPerTurn must be exactly 12")
    for spell in ("indecision", "reflection", "repulsion", "attraction"):
        if resources.get("initialCharges", {}).get(spell) != 2:
            raise ProfileError(f"{spell} initialCharges must be exactly 2")
        if resources.get("maxCharges", {}).get(spell) != 4:
            raise ProfileError(f"{spell} maxCharges must be exactly 4")
        if resources.get("chargeCostPerCast", {}).get(spell) != 1:
            raise ProfileError(f"{spell} chargeCostPerCast must be exactly 1")
    for spell in ("reflection", "repulsion", "attraction"):
        item = profile.get("movement", {}).get(spell, {})
        min_range = item.get("minRange")
        max_range = item.get("maxRange")
        if min_range is not None and max_range is not None and min_range > max_range:
            raise ProfileError(f"{spell} minRange exceeds maxRange")

    movement = profile.get("movement", {})
    exact_geometry = {
        "indecision": {
            "contactMetric": "orthogonal",
            "destinationOccupancy": "invalid",
        },
        "reflection": {
            "targetPillarType": "any_pillar",
            "rangeMetric": "manhattan",
            "minRange": 2,
            "maxRange": 2,
            "alignment": "cardinal_or_diagonal",
            "destinationOccupancy": "invalid",
        },
        "repulsion": {
            "targetPillarType": "any_pillar",
            "rangeMetric": "aligned_steps",
            "minRange": 1,
            "maxRange": 2,
            "destinationOccupancy": "invalid",
        },
        "attraction": {
            "targetPillarType": "any_pillar",
            "rangeMetric": "aligned_steps",
            "minRange": 1,
            "maxRange": 6,
            "alignment": "cardinal",
            "distance": 3,
            "destinationOccupancy": "invalid",
        },
    }
    for spell, required in exact_geometry.items():
        item = movement.get(spell, {})
        for field, expected in required.items():
            if item.get(field) != expected:
                raise ProfileError(f"{spell} {field} must be {expected!r}")
    if set(movement.get("repulsion", {}).get("allowedAlignments", [])) != {
        "cardinal",
        "diagonal",
    }:
        raise ProfileError("repulsion allowedAlignments must be cardinal and diagonal")
