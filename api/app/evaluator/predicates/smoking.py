"""Tobacco predicates: smoking_status_is.

Per predicate-catalog.yaml, default policy is fail_closed (missing -> unknown).
Derived token 'current' expands to {current, current_some_day, current_every_day}.
"""

from __future__ import annotations

from typing import Any


# Derived token expansion per predicate-catalog.yaml notes.
_CURRENT_SMOKER_TOKENS = {"current", "current_some_day", "current_every_day"}


def eval_smoking_status_is(
    args: dict[str, Any], patient_context: dict[str, Any], entities: dict[str, Any]
) -> str:
    """smoking_status_is: check if patient's tobacco status is in the provided list.

    Supports the derived token 'current' which expands to
    {current, current_some_day, current_every_day}.
    Default policy: fail_closed (missing -> unknown).
    """
    values = args["values"]

    # Expand 'current' token
    expanded_values: set[str] = set()
    for v in values:
        if v == "current":
            expanded_values.update(_CURRENT_SMOKER_TOKENS)
        else:
            expanded_values.add(v)

    social_history = patient_context.get("social_history")
    if social_history is None:
        return "unknown"  # fail_closed

    tobacco = social_history.get("tobacco")
    if tobacco is None:
        return "unknown"  # fail_closed

    status = tobacco.get("status")
    if status is None:
        return "unknown"  # fail_closed

    return "true" if status in expanded_values else "false"
