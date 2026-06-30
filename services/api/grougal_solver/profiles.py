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
    return load_json(project_root / "examples" / "rules-profile.hypothesis.json")


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
        # The fixture state is the selected action-budget source. This avoids
        # manufacturing a conflict with the review profile's provisional default.
        profile["resources"]["actionBudgetPerTurn"] = action_budget
    validate_profile(profile)
    return profile


def validate_profile(profile: dict[str, Any]) -> None:
    resources = profile.get("resources", {})
    cost = resources.get("movementActionCost")
    if not isinstance(cost, int) or cost <= 0:
        raise ProfileError("movementActionCost must be a positive integer")
    for spell in ("reflection", "repulsion", "attraction"):
        item = profile.get("movement", {}).get(spell, {})
        min_range = item.get("minRange")
        max_range = item.get("maxRange")
        if min_range is not None and max_range is not None and min_range > max_range:
            raise ProfileError(f"{spell} minRange exceeds maxRange")
