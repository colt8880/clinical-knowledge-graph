"""Age comparison predicates for the evaluator.

Per predicate-catalog.yaml, all age predicates have default_policy: require.
Missing date_of_birth is a hard evaluation error, not unknown.
"""

from __future__ import annotations

from typing import Any

from app.evaluator.trace import compute_age


def _get_age(patient_context: dict[str, Any]) -> int:
    """Extract computed age from patient context. Raises if DOB missing."""
    dob = patient_context.get("patient", {}).get("date_of_birth")
    if dob is None:
        raise ValueError("patient.date_of_birth is required for age predicates (policy: require)")
    eval_time = patient_context["evaluation_time"]
    return compute_age(dob, eval_time)


def eval_age_between(
    args: dict[str, Any], patient_context: dict[str, Any], entities: dict[str, Any]
) -> str:
    """age_between: floor(age) in [min, max] inclusive."""
    age = _get_age(patient_context)
    min_age = args["min"]
    max_age = args["max"]
    return "true" if min_age <= age <= max_age else "false"


def eval_age_less_than(
    args: dict[str, Any], patient_context: dict[str, Any], entities: dict[str, Any]
) -> str:
    """age_less_than: floor(age) < value. Strict inequality."""
    age = _get_age(patient_context)
    return "true" if age < args["value"] else "false"


def eval_age_greater_than_or_equal(
    args: dict[str, Any], patient_context: dict[str, Any], entities: dict[str, Any]
) -> str:
    """age_greater_than_or_equal: floor(age) >= value."""
    age = _get_age(patient_context)
    return "true" if age >= args["value"] else "false"
