"""Risk-score predicates: risk_score_compares.

Per predicate-catalog.yaml, default policy is fail_closed (missing -> unknown).
v0 does NOT compute ASCVD via Pooled Cohort Equations; it reads supplied scores.
"""

from __future__ import annotations

from typing import Any

from app.evaluator.predicates.compare import compare_value


def eval_risk_score_compares(
    args: dict[str, Any], patient_context: dict[str, Any], entities: dict[str, Any]
) -> str:
    """risk_score_compares: compare a named risk score against a threshold.

    Resolution order (per predicate-catalog.yaml):
    1. If patient_context.risk_scores[name] present, use supplied value.
    2. Else: v0 does not compute; return "false" (fail_closed -> unavailable).

    Default policy: fail_closed.
    """
    score_name = args["name"]
    comparator = args["comparator"]
    threshold = args["threshold"]

    risk_scores = patient_context.get("risk_scores", {})
    score_data = risk_scores.get(score_name)

    if score_data is None:
        return "unknown"  # fail_closed: score not supplied

    value = score_data.get("value")
    if value is None:
        return "unknown"

    return "true" if compare_value(value, comparator, threshold) else "false"
