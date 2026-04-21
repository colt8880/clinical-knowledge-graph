"""Parse structured_eligibility JSON into normalized eligibility criteria.

Extracts age ranges, required/excluded conditions, required observations,
required medications, and risk score requirements from the predicate tree
used in Recommendation.structured_eligibility.

The seed files store predicates as {predicate_name: {args...}} objects
nested inside all_of / any_of / none_of composites. This module walks
the tree and extracts a flat summary suitable for overlap computation.

Disjunctions (any_of) are tracked separately from conjunctions (all_of)
so the overlap computation and plain English rendering correctly represent
OR vs AND semantics. The spec requires flagging complex nesting as
"manual review needed" rather than silently misrepresenting it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DisjunctiveGroup:
    """A group of conditions/predicates where ANY one suffices (from any_of)."""

    conditions: list[str] = field(default_factory=list)
    observations: list[dict] = field(default_factory=list)
    medications: list[str] = field(default_factory=list)
    smoking_values: list[str] = field(default_factory=list)
    nested_all_of: list[dict] = field(default_factory=list)
    # raw children for complex nesting that can't be flattened cleanly
    manual_review_notes: list[str] = field(default_factory=list)


@dataclass
class EligibilityCriteria:
    """Normalized eligibility extracted from a structured_eligibility tree."""

    age_min: int | None = None
    age_max: int | None = None
    age_gte: int | None = None  # from age_greater_than_or_equal
    # Conjunctive conditions: patient must have ALL of these
    required_conditions: list[str] = field(default_factory=list)
    excluded_conditions: list[str] = field(default_factory=list)
    # Disjunctive groups: patient must satisfy at least one branch per group
    disjunctive_groups: list[DisjunctiveGroup] = field(default_factory=list)
    required_observations: list[dict] = field(default_factory=list)
    excluded_observations: list[dict] = field(default_factory=list)
    required_medications: list[str] = field(default_factory=list)
    excluded_medications: list[str] = field(default_factory=list)
    risk_scores: list[dict] = field(default_factory=list)
    smoking_status: list[str] = field(default_factory=list)
    manual_review_notes: list[str] = field(default_factory=list)

    @property
    def effective_age_min(self) -> int | None:
        """Compute the effective minimum age from age_between and age_gte."""
        candidates = [v for v in [self.age_min, self.age_gte] if v is not None]
        return max(candidates) if candidates else None

    @property
    def effective_age_max(self) -> int | None:
        return self.age_max

    def age_range_str(self) -> str:
        lo = self.effective_age_min
        hi = self.effective_age_max
        if lo is not None and hi is not None:
            return f"{lo}–{hi}"
        elif lo is not None:
            return f"≥{lo}"
        elif hi is not None:
            return f"≤{hi}"
        return "any age"

    @property
    def all_required_conditions(self) -> list[str]:
        """All conditions that could satisfy eligibility (conjunctive + any disjunctive branch)."""
        result = list(self.required_conditions)
        for group in self.disjunctive_groups:
            result.extend(group.conditions)
        return result


def parse_eligibility(json_str: str) -> EligibilityCriteria:
    """Parse a structured_eligibility JSON string into EligibilityCriteria."""
    tree = json.loads(json_str)
    criteria = EligibilityCriteria()
    _walk(tree, criteria, negated=False, in_any_of=False)
    return criteria


def _walk(
    node: dict[str, Any],
    criteria: EligibilityCriteria,
    negated: bool,
    in_any_of: bool,
    disjunctive_group: DisjunctiveGroup | None = None,
) -> None:
    """Recursively walk a predicate tree, extracting criteria."""
    if not isinstance(node, dict):
        return

    # Handle composites
    if "all_of" in node:
        if in_any_of and disjunctive_group is not None:
            # all_of nested inside any_of — complex nesting, flag for review
            # but still extract what we can
            for child in node["all_of"]:
                _walk(child, criteria, negated, in_any_of=True, disjunctive_group=disjunctive_group)
        else:
            for child in node["all_of"]:
                _walk(child, criteria, negated, in_any_of=False)

    if "any_of" in node:
        if negated:
            # NOT(any_of) = none_of — each child is excluded
            for child in node["any_of"]:
                _walk(child, criteria, negated=True, in_any_of=False)
        else:
            # Create a disjunctive group for this any_of
            group = DisjunctiveGroup()
            for child in node["any_of"]:
                _walk(child, criteria, negated=False, in_any_of=True, disjunctive_group=group)
            # Only add group if it has content
            if group.conditions or group.observations or group.medications or group.smoking_values:
                criteria.disjunctive_groups.append(group)
            if group.manual_review_notes:
                criteria.manual_review_notes.extend(group.manual_review_notes)

    if "none_of" in node:
        for child in node["none_of"]:
            _walk(child, criteria, negated=not negated, in_any_of=False)

    if "n_of" in node:
        n_of = node["n_of"]
        n = n_of.get("n", 1)
        children = n_of.get("of", [])
        if n == 1:
            # n_of with n=1 is semantically any_of
            group = DisjunctiveGroup()
            for child in children:
                _walk(child, criteria, negated=False, in_any_of=True, disjunctive_group=group)
            if group.conditions or group.observations or group.medications or group.smoking_values:
                criteria.disjunctive_groups.append(group)
        else:
            # n_of with n>1 is complex — flag for manual review
            criteria.manual_review_notes.append(
                f"n_of(n={n}) with {len(children)} branches — manual review needed"
            )
            # Still extract children conservatively
            for child in children:
                _walk(child, criteria, negated, in_any_of=False)

    # Handle predicate atoms — keys are predicate names with args as values
    _extract_predicate(node, criteria, negated, in_any_of, disjunctive_group)


def _extract_predicate(
    node: dict[str, Any],
    criteria: EligibilityCriteria,
    negated: bool,
    in_any_of: bool,
    disjunctive_group: DisjunctiveGroup | None,
) -> None:
    """Extract a single predicate atom from the node."""
    for pred_name, args in node.items():
        if pred_name in ("all_of", "any_of", "none_of", "n_of"):
            continue  # composites handled above
        if not isinstance(args, dict):
            continue

        if pred_name == "age_between":
            if not negated:
                criteria.age_min = args.get("min")
                criteria.age_max = args.get("max")
            else:
                criteria.manual_review_notes.append(
                    f"Negated age_between({args.get('min')}, {args.get('max')})"
                )

        elif pred_name == "age_greater_than_or_equal":
            if not negated:
                criteria.age_gte = args.get("value")
            else:
                criteria.age_max = args.get("value", 0) - 1

        elif pred_name == "age_less_than":
            if not negated:
                criteria.age_max = args.get("value", 0) - 1

        elif pred_name in ("has_condition_history", "has_active_condition"):
            codes = args.get("codes", [])
            if negated:
                criteria.excluded_conditions.extend(codes)
            elif in_any_of and disjunctive_group is not None:
                disjunctive_group.conditions.extend(codes)
            else:
                criteria.required_conditions.extend(codes)

        elif pred_name == "most_recent_observation_value":
            obs = {
                "code": args.get("code"),
                "comparator": args.get("comparator"),
                "threshold": args.get("threshold"),
                "unit": args.get("unit"),
                "window": args.get("window"),
            }
            if negated:
                criteria.excluded_observations.append(obs)
            elif in_any_of and disjunctive_group is not None:
                disjunctive_group.observations.append(obs)
            else:
                criteria.required_observations.append(obs)

        elif pred_name == "has_medication_active":
            codes = args.get("codes", [])
            if negated:
                criteria.excluded_medications.extend(codes)
            elif in_any_of and disjunctive_group is not None:
                disjunctive_group.medications.extend(codes)
            else:
                criteria.required_medications.extend(codes)

        elif pred_name == "risk_score_compares":
            criteria.risk_scores.append(
                {
                    "name": args.get("name"),
                    "comparator": args.get("comparator"),
                    "threshold": args.get("threshold"),
                }
            )

        elif pred_name == "smoking_status_is":
            if in_any_of and disjunctive_group is not None:
                disjunctive_group.smoking_values.extend(args.get("values", []))
            else:
                criteria.smoking_status.extend(args.get("values", []))

        else:
            note = f"Unhandled predicate: {pred_name}({args})"
            if in_any_of and disjunctive_group is not None:
                disjunctive_group.manual_review_notes.append(note)
            else:
                criteria.manual_review_notes.append(note)


def eligibility_to_plain_english(criteria: EligibilityCriteria) -> str:
    """Render EligibilityCriteria as a clinician-readable plain English summary."""
    parts: list[str] = []

    # Age
    parts.append(f"Age: {criteria.age_range_str()}")

    # Conjunctive required conditions
    if criteria.required_conditions:
        codes_str = ", ".join(_display_code(c) for c in criteria.required_conditions)
        parts.append(f"Requires: {codes_str}")

    # Disjunctive groups
    for group in criteria.disjunctive_groups:
        or_parts: list[str] = []
        for c in group.conditions:
            or_parts.append(_display_code(c))
        for obs in group.observations:
            comp = _comparator_symbol(obs.get("comparator", ""))
            or_parts.append(
                f"{_display_code(obs['code'])} {comp} {obs.get('threshold')} "
                f"{obs.get('unit', '')} (within {obs.get('window', 'N/A')})"
            )
        for m in group.medications:
            or_parts.append(f"active {_display_code(m)}")
        for sv in group.smoking_values:
            or_parts.append(f"smoking: {sv}")
        if or_parts:
            parts.append(f"Requires ANY of: [{' | '.join(or_parts)}]")

    # Excluded conditions
    if criteria.excluded_conditions:
        codes_str = ", ".join(_display_code(c) for c in criteria.excluded_conditions)
        parts.append(f"Excludes: {codes_str}")

    # Required observations
    for obs in criteria.required_observations:
        comp = _comparator_symbol(obs.get("comparator", ""))
        parts.append(
            f"Requires {_display_code(obs['code'])} {comp} "
            f"{obs.get('threshold')} {obs.get('unit', '')} "
            f"(within {obs.get('window', 'N/A')})"
        )

    # Excluded observations
    for obs in criteria.excluded_observations:
        comp = _comparator_symbol(obs.get("comparator", ""))
        parts.append(
            f"Excludes patients with {_display_code(obs['code'])} {comp} "
            f"{obs.get('threshold')} {obs.get('unit', '')} "
            f"(within {obs.get('window', 'N/A')})"
        )

    # Required medications
    if criteria.required_medications:
        codes_str = ", ".join(_display_code(c) for c in criteria.required_medications)
        parts.append(f"Requires active medication: {codes_str}")

    # Excluded medications
    if criteria.excluded_medications:
        codes_str = ", ".join(_display_code(c) for c in criteria.excluded_medications)
        parts.append(f"Excludes active medication: {codes_str}")

    # Risk scores
    for rs in criteria.risk_scores:
        comp = _comparator_symbol(rs.get("comparator", ""))
        parts.append(f"Risk score {rs.get('name')} {comp} {rs.get('threshold')}")

    # Smoking
    if criteria.smoking_status:
        parts.append(f"Smoking status: {', '.join(criteria.smoking_status)}")

    # Manual review flags
    if criteria.manual_review_notes:
        parts.append(f"⚠ Manual review: {'; '.join(criteria.manual_review_notes)}")

    return "; ".join(parts) if parts else "No criteria extracted"


def _display_code(code: str) -> str:
    """Convert a graph node ID to a readable display name."""
    if ":" in code:
        _, name = code.split(":", 1)
        return name.replace("-", " ").title()
    return code


def _comparator_symbol(comp: str) -> str:
    return {
        "eq": "=",
        "ne": "≠",
        "gt": ">",
        "lt": "<",
        "gte": "≥",
        "lte": "≤",
    }.get(comp, comp)
