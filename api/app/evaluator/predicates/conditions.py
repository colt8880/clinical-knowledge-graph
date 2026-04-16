"""Condition predicates: has_condition_history, has_active_condition.

Per predicate-catalog.yaml, both default to fail_open (missing data -> false).
"""

from __future__ import annotations

from typing import Any


def _match_condition(
    patient_context: dict[str, Any],
    entities: dict[str, Any],
    codes_arg: list[str],
    allowed_statuses: set[str],
) -> tuple[str, list[dict[str, Any]]]:
    """Check if any patient condition matches the referenced entity codes.

    Returns (result, inputs_read) tuple.
    """
    conditions = patient_context.get("conditions", [])
    inputs_read: list[dict[str, Any]] = []

    # Collect all codes from referenced entity nodes
    entity_code_set: set[tuple[str, str]] = set()
    for node_id in codes_arg:
        entity = entities.get(node_id)
        if entity is not None:
            for code_ref in entity.codes:
                entity_code_set.add((code_ref.system, code_ref.code))

    for cond in conditions:
        if cond.get("verification_status") != "confirmed":
            continue
        if cond.get("clinical_status") not in allowed_statuses:
            continue
        for code_ref in cond.get("codes", []):
            if (code_ref["system"], code_ref["code"]) in entity_code_set:
                inputs_read.append({
                    "source": "patient.conditions",
                    "locator": f"conditions[id={cond['id']}]",
                    "value": {
                        "id": cond["id"],
                        "clinical_status": cond.get("clinical_status"),
                        "codes": cond.get("codes", []),
                    },
                    "present": True,
                })
                return "true", inputs_read

    # No match found
    inputs_read.append({
        "source": "patient.conditions",
        "locator": "conditions[]",
        "value": None,
        "present": len(conditions) > 0,
    })
    return "false", inputs_read


def eval_has_condition_history(
    args: dict[str, Any], patient_context: dict[str, Any], entities: dict[str, Any]
) -> str:
    """has_condition_history: any confirmed condition regardless of clinical_status.

    Per predicate-catalog.yaml: verification_status=confirmed,
    clinical_status in {active, recurrence, remission, resolved, inactive}.
    Default policy: fail_open.
    """
    allowed = {"active", "recurrence", "remission", "resolved", "inactive"}
    result, _ = _match_condition(patient_context, entities, args["codes"], allowed)
    return result


def eval_has_active_condition(
    args: dict[str, Any], patient_context: dict[str, Any], entities: dict[str, Any]
) -> str:
    """has_active_condition: confirmed and active/recurrence only.

    Default policy: fail_open.
    """
    allowed = {"active", "recurrence"}
    result, _ = _match_condition(patient_context, entities, args["codes"], allowed)
    return result
