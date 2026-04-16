"""Observation predicates: most_recent_observation_value.

Per predicate-catalog.yaml, default policy is fail_open (missing -> false).
Tiebreaker when two observations share effective_date: lexicographic by id
(per docs/ISSUES.md).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.evaluator.predicates.compare import compare_value


def _parse_iso_duration_to_days(duration: str) -> int:
    """Parse a simple ISO 8601 duration (P1Y, P2Y, P30D, P6M) to days.

    Approximate: 1Y = 365 days, 1M = 30 days.
    """
    if not duration.startswith("P"):
        raise ValueError(f"Invalid ISO 8601 duration: {duration}")
    rest = duration[1:]
    days = 0
    if "Y" in rest:
        years, rest = rest.split("Y", 1)
        days += int(years) * 365
    if "M" in rest:
        months, rest = rest.split("M", 1)
        days += int(months) * 30
    if "D" in rest:
        d, rest = rest.split("D", 1)
        days += int(d)
    return days


def _normalize_unit(unit: str) -> str:
    """Normalize common unit variations for comparison.

    Per docs/ISSUES.md: unit normalization happens in the observation predicate.
    """
    normalized = unit.lower().replace("[", "").replace("]", "")
    return normalized


def eval_most_recent_observation_value(
    args: dict[str, Any], patient_context: dict[str, Any], entities: dict[str, Any]
) -> str:
    """most_recent_observation_value: find most recent matching observation and compare.

    Args:
        code: graph_node_id for the observation entity
        window: ISO 8601 duration (e.g., P2Y)
        comparator: eq, ne, gt, lt, gte, lte
        threshold: number to compare against
        unit: expected unit (UCUM)
        component: optional code for component selection (e.g., SBP within BP panel)

    Default policy: fail_open (no match -> false).
    """
    code_node_id = args["code"]
    window = args.get("window", "P10Y")
    comparator = args["comparator"]
    threshold = args["threshold"]
    component = args.get("component")

    # Resolve entity codes
    entity = entities.get(code_node_id)
    if entity is None:
        return "false"

    entity_code_set = {(c.system, c.code) for c in entity.codes}

    observations = patient_context.get("observations", [])
    eval_time_str = patient_context["evaluation_time"]
    if "T" in eval_time_str:
        eval_time = datetime.fromisoformat(eval_time_str.replace("Z", "+00:00"))
    else:
        eval_time = datetime.fromisoformat(eval_time_str)

    window_days = _parse_iso_duration_to_days(window)
    window_start = eval_time - timedelta(days=window_days)

    # Find matching observations
    matching: list[tuple[str, str, float]] = []  # (effective_date, id, value)
    for obs in observations:
        if obs.get("status") not in ("final", "amended", "corrected"):
            continue

        obs_codes = obs.get("codes", [])
        codes_match = any(
            (c["system"], c["code"]) in entity_code_set
            for c in obs_codes
        )
        if not codes_match:
            continue

        eff_date_str = obs.get("effective_date", "")
        if not eff_date_str:
            continue

        if "T" in eff_date_str:
            eff_date = datetime.fromisoformat(eff_date_str.replace("Z", "+00:00"))
        else:
            eff_date = datetime.fromisoformat(eff_date_str)

        # Check window
        if eff_date < window_start or eff_date > eval_time:
            continue

        # Extract value — either from component or top-level value
        if component is not None:
            # Look in components for a matching code
            value = _extract_component_value(obs, component, entity_code_set)
        else:
            value = _extract_value(obs)

        if value is not None:
            matching.append((eff_date_str, obs.get("id", ""), value))

    if not matching:
        return "false"

    # Sort by effective_date desc, then id desc for deterministic tiebreak
    # (per docs/ISSUES.md: lexicographic by id when dates are equal)
    matching.sort(key=lambda x: (x[0], x[1]), reverse=True)
    most_recent_value = matching[0][2]

    return "true" if compare_value(most_recent_value, comparator, threshold) else "false"


def _extract_value(obs: dict[str, Any]) -> float | None:
    """Extract value_quantity.value from an observation."""
    value = obs.get("value")
    if value and "value_quantity" in value:
        return value["value_quantity"]["value"]
    return None


def _extract_component_value(
    obs: dict[str, Any],
    component_code: str,
    entity_code_set: set[tuple[str, str]],
) -> float | None:
    """Extract a component value from an observation by component code.

    The component arg is a LOINC code (e.g., "8480-6" for SBP).
    """
    components = obs.get("components", [])
    for comp in components:
        comp_codes = comp.get("codes", [])
        for cc in comp_codes:
            if cc.get("code") == component_code:
                comp_value = comp.get("value")
                if comp_value and "value_quantity" in comp_value:
                    return comp_value["value_quantity"]["value"]
    return None
