"""Predicate dispatch table.

Maps predicate names from predicate-catalog.yaml to evaluator functions.
Predicates not yet implemented raise NotImplementedError with the predicate name.
"""

from __future__ import annotations

from typing import Any, Callable

from app.evaluator.predicates.age import eval_age_between, eval_age_less_than, eval_age_greater_than_or_equal

# Type: (args, patient_context, entities) -> "true" | "false" | "unknown"
PredicateFn = Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], str]


def _not_implemented(name: str) -> PredicateFn:
    def _stub(args: dict[str, Any], patient_context: dict[str, Any], entities: dict[str, Any]) -> str:
        raise NotImplementedError(f"Predicate '{name}' is not yet implemented")
    return _stub


# Dispatch table keyed by predicate name from predicate-catalog.yaml.
# Implemented predicates point to real functions; everything else stubs.
REGISTRY: dict[str, PredicateFn] = {
    # Demographics — implemented
    "age_between": eval_age_between,
    "age_less_than": eval_age_less_than,
    "age_greater_than_or_equal": eval_age_greater_than_or_equal,
    "administrative_sex_is": _not_implemented("administrative_sex_is"),
    "has_ancestry_matching": _not_implemented("has_ancestry_matching"),
    # Conditions — stub
    "has_condition_history": _not_implemented("has_condition_history"),
    "has_active_condition": _not_implemented("has_active_condition"),
    # Tobacco — stub
    "smoking_status_is": _not_implemented("smoking_status_is"),
    # Observations — stub
    "most_recent_observation_value": _not_implemented("most_recent_observation_value"),
    # Medications — stub
    "has_medication_active": _not_implemented("has_medication_active"),
    # Risk scores — stub
    "risk_score_compares": _not_implemented("risk_score_compares"),
}


def get_predicate(name: str) -> PredicateFn:
    """Look up a predicate function by catalog name."""
    if name in REGISTRY:
        return REGISTRY[name]
    raise NotImplementedError(f"Predicate '{name}' is not in the registry")
