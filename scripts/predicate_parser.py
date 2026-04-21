"""Parse structured_eligibility JSON into normalized eligibility criteria.

Extracts age ranges, required/excluded conditions, required observations,
required medications, and risk score requirements from the predicate tree
used in Recommendation.structured_eligibility.

The seed files store predicates as {predicate_name: {args...}} objects
nested inside all_of / any_of / none_of composites. This module walks
the tree and extracts a flat summary suitable for overlap computation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EligibilityCriteria:
    """Normalized eligibility extracted from a structured_eligibility tree."""

    age_min: int | None = None
    age_max: int | None = None
    age_gte: int | None = None  # from age_greater_than_or_equal
    required_conditions: list[str] = field(default_factory=list)
    excluded_conditions: list[str] = field(default_factory=list)
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


def parse_eligibility(json_str: str) -> EligibilityCriteria:
    """Parse a structured_eligibility JSON string into EligibilityCriteria."""
    tree = json.loads(json_str)
    criteria = EligibilityCriteria()
    _walk(tree, criteria, negated=False)
    return criteria


def _walk(node: dict[str, Any], criteria: EligibilityCriteria, negated: bool) -> None:
    """Recursively walk a predicate tree, extracting criteria."""
    if not isinstance(node, dict):
        return

    # Handle composites
    if "all_of" in node:
        for child in node["all_of"]:
            _walk(child, criteria, negated)
    if "any_of" in node:
        for child in node["any_of"]:
            _walk(child, criteria, negated)
    if "none_of" in node:
        for child in node["none_of"]:
            _walk(child, criteria, negated=not negated)
    if "n_of" in node:
        n_of = node["n_of"]
        for child in n_of.get("of", []):
            _walk(child, criteria, negated)

    # Handle predicate atoms — keys are predicate names with args as values
    _extract_predicate(node, criteria, negated)


def _extract_predicate(
    node: dict[str, Any], criteria: EligibilityCriteria, negated: bool
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
            # Negated age_between is unusual; flag for manual review
            else:
                criteria.manual_review_notes.append(
                    f"Negated age_between({args.get('min')}, {args.get('max')})"
                )

        elif pred_name == "age_greater_than_or_equal":
            if not negated:
                criteria.age_gte = args.get("value")
            else:
                # NOT age >= X means age < X
                criteria.age_max = args.get("value", 0) - 1

        elif pred_name == "age_less_than":
            if not negated:
                criteria.age_max = args.get("value", 0) - 1

        elif pred_name in ("has_condition_history", "has_active_condition"):
            codes = args.get("codes", [])
            if negated:
                criteria.excluded_conditions.extend(codes)
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
            else:
                criteria.required_observations.append(obs)

        elif pred_name == "has_medication_active":
            codes = args.get("codes", [])
            if negated:
                criteria.excluded_medications.extend(codes)
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
            criteria.smoking_status.extend(args.get("values", []))

        else:
            criteria.manual_review_notes.append(
                f"Unhandled predicate: {pred_name}({args})"
            )


def eligibility_to_plain_english(criteria: EligibilityCriteria) -> str:
    """Render EligibilityCriteria as a clinician-readable plain English summary."""
    parts: list[str] = []

    # Age
    parts.append(f"Age: {criteria.age_range_str()}")

    # Required conditions
    if criteria.required_conditions:
        codes_str = ", ".join(_display_code(c) for c in criteria.required_conditions)
        parts.append(f"Requires (any): {codes_str}")

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
    # Strip prefix (cond:, med:, obs:, proc:) and title-case
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
