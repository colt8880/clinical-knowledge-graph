"""Medication predicates: has_medication_active.

Per predicate-catalog.yaml, default policy is fail_open (missing -> false).
Class-level matching via graph node code list.
"""

from __future__ import annotations

from typing import Any


def eval_has_medication_active(
    args: dict[str, Any], patient_context: dict[str, Any], entities: dict[str, Any]
) -> str:
    """has_medication_active: any active medication matching entity codes.

    Checks status=active and code intersection with referenced graph nodes.
    Default policy: fail_open.
    """
    codes_arg = args["codes"]

    # Collect all codes from referenced entity nodes
    entity_code_set: set[tuple[str, str]] = set()
    for node_id in codes_arg:
        entity = entities.get(node_id)
        if entity is not None:
            for code_ref in entity.codes:
                entity_code_set.add((code_ref.system, code_ref.code))

    medications = patient_context.get("medications", [])
    for med in medications:
        if med.get("status") != "active":
            continue
        for code_ref in med.get("codes", []):
            if (code_ref["system"], code_ref["code"]) in entity_code_set:
                return "true"

    return "false"
