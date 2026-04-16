"""Predicate dispatch table.

Maps predicate names from predicate-catalog.yaml to evaluator functions.
Predicates not yet implemented raise NotImplementedError with the predicate name.
"""

from __future__ import annotations

from typing import Any, Callable

from app.evaluator.predicates.age import (
    eval_age_between,
    eval_age_less_than,
    eval_age_greater_than_or_equal,
)
from app.evaluator.predicates.conditions import (
    eval_has_condition_history,
    eval_has_active_condition,
)
from app.evaluator.predicates.observations import eval_most_recent_observation_value
from app.evaluator.predicates.medications import eval_has_medication_active
from app.evaluator.predicates.smoking import eval_smoking_status_is
from app.evaluator.predicates.risk_score import eval_risk_score_compares

# Type: (args, patient_context, entities) -> "true" | "false" | "unknown"
PredicateFn = Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], str]


def _not_implemented(name: str) -> PredicateFn:
    def _stub(args: dict[str, Any], patient_context: dict[str, Any], entities: dict[str, Any]) -> str:
        raise NotImplementedError(f"Predicate '{name}' is not yet implemented")
    return _stub


# Dispatch table keyed by predicate name from predicate-catalog.yaml.
REGISTRY: dict[str, PredicateFn] = {
    # Demographics
    "age_between": eval_age_between,
    "age_less_than": eval_age_less_than,
    "age_greater_than_or_equal": eval_age_greater_than_or_equal,
    "administrative_sex_is": _not_implemented("administrative_sex_is"),
    "has_ancestry_matching": _not_implemented("has_ancestry_matching"),
    # Conditions
    "has_condition_history": eval_has_condition_history,
    "has_active_condition": eval_has_active_condition,
    # Tobacco
    "smoking_status_is": eval_smoking_status_is,
    # Observations
    "most_recent_observation_value": eval_most_recent_observation_value,
    # Medications
    "has_medication_active": eval_has_medication_active,
    # Risk scores
    "risk_score_compares": eval_risk_score_compares,
}


def get_predicate(name: str) -> PredicateFn:
    """Look up a predicate function by catalog name."""
    if name in REGISTRY:
        return REGISTRY[name]
    raise NotImplementedError(f"Predicate '{name}' is not in the registry")
