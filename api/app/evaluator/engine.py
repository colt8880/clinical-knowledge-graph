"""Evaluator engine: top-level orchestration.

evaluate() is pure — no wall-clock reads, no RNG, no external I/O.
All inputs are PatientContext + a loaded GraphSnapshot.

For v0, the statin model has three out-of-scope exits that are checked
before iterating recommendations. See docs/reference/guidelines/statins.md §
Out-of-scope exits.
"""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.evaluator.graph import GraphSnapshot, CodeRef
from app.evaluator.trace import TraceBuilder, compute_age, patient_fingerprint


# ---------------------------------------------------------------------------
# Exit-condition definitions (statin guideline)
#
# Per guidelines/statins.md, these are not Recommendation nodes — they are
# evaluator-level pre-flight checks. Ordering matters: secondary
# prevention > familial hypercholesterolemia > age below range.
# ---------------------------------------------------------------------------

_STATIN_EXITS = [
    {
        "token": "out_of_scope_secondary_prevention",
        "rationale": "Established ASCVD is secondary prevention — addressed by ACC/AHA cholesterol guideline, not this USPSTF statement.",
        "check": "_check_secondary_prevention",
    },
    {
        "token": "out_of_scope_familial_hypercholesterolemia",
        "rationale": "Severe primary hypercholesterolemia falls outside the Pooled Cohort Equation calibration range and has its own management pathway.",
        "check": "_check_familial_hypercholesterolemia",
    },
    {
        "token": "out_of_scope_age_below_range",
        "rationale": "USPSTF statin primary prevention does not address adults under 40.",
        "check": "_check_age_below_range",
    },
]


def _patient_has_condition_matching(
    patient_context: dict[str, Any],
    entity_codes: list[CodeRef],
) -> bool:
    """Check if any patient condition matches any code in the entity's code list."""
    conditions = patient_context.get("conditions", [])
    entity_code_set = {(c.system, c.code) for c in entity_codes}
    for cond in conditions:
        if cond.get("verification_status") not in ("confirmed",):
            continue
        for code_ref in cond.get("codes", []):
            if (code_ref["system"], code_ref["code"]) in entity_code_set:
                return True
    return False


def _get_most_recent_observation_value(
    patient_context: dict[str, Any],
    entity_codes: list[CodeRef],
) -> float | None:
    """Get the most recent observation value matching the entity codes.

    Only considers observations with status in {final, amended, corrected}.
    Returns value_quantity.value or None if no match.
    Tiebreaker on same effective_date: lexicographic by id (per docs/ISSUES.md).
    """
    observations = patient_context.get("observations", [])
    entity_code_set = {(c.system, c.code) for c in entity_codes}

    matching: list[tuple[str, str, float]] = []  # (effective_date, id, value)
    for obs in observations:
        if obs.get("status") not in ("final", "amended", "corrected"):
            continue
        codes_match = any(
            (c["system"], c["code"]) in entity_code_set
            for c in obs.get("codes", [])
        )
        if not codes_match:
            continue
        value = obs.get("value")
        if value and "value_quantity" in value:
            matching.append((
                obs.get("effective_date", ""),
                obs.get("id", ""),
                value["value_quantity"]["value"],
            ))

    if not matching:
        return None
    # Sort by effective_date desc, then id desc for deterministic tiebreak
    matching.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return matching[0][2]


def _check_secondary_prevention(
    patient_context: dict[str, Any], age: int, graph: GraphSnapshot
) -> bool:
    """Exit if patient has established ASCVD (cond:ascvd-established)."""
    entity = graph.entities.get("cond:ascvd-established")
    if entity is None:
        return False
    return _patient_has_condition_matching(patient_context, entity.codes)


def _check_familial_hypercholesterolemia(
    patient_context: dict[str, Any], age: int, graph: GraphSnapshot
) -> bool:
    """Exit if patient has FH condition or LDL >= 190 mg/dL."""
    # Check FH condition
    fh_entity = graph.entities.get("cond:familial-hypercholesterolemia")
    if fh_entity and _patient_has_condition_matching(patient_context, fh_entity.codes):
        return True
    # Check LDL >= 190
    ldl_entity = graph.entities.get("obs:ldl-cholesterol")
    if ldl_entity:
        ldl_value = _get_most_recent_observation_value(patient_context, ldl_entity.codes)
        if ldl_value is not None and ldl_value >= 190:
            return True
    return False


def _check_age_below_range(
    patient_context: dict[str, Any], age: int, graph: GraphSnapshot
) -> bool:
    """Exit if patient age < 40."""
    return age < 40


_EXIT_CHECKERS = {
    "_check_secondary_prevention": _check_secondary_prevention,
    "_check_familial_hypercholesterolemia": _check_familial_hypercholesterolemia,
    "_check_age_below_range": _check_age_below_range,
}


def evaluate(patient_context: dict[str, Any], graph: GraphSnapshot) -> dict[str, Any]:
    """Run the trace-first evaluator.

    Pure function: same (patient_context, graph) -> same trace.
    Wall-clock fields (envelope.started_at, envelope.completed_at,
    evaluation_completed.duration_ms) are NOT set here — the caller
    (route handler) stamps them after evaluate() returns. This keeps
    evaluate() free of datetime.now() calls.
    """
    trace = TraceBuilder()

    # Compute patient demographics
    dob = patient_context["patient"]["date_of_birth"]
    eval_time = patient_context["evaluation_time"]
    age = compute_age(dob, eval_time)
    sex = patient_context["patient"]["administrative_sex"]
    fingerprint = patient_fingerprint(patient_context)

    # 1. evaluation_started
    trace.evaluation_started(age, sex, [graph.guideline_id])

    # 2. guideline_entered
    trace.guideline_entered(graph.guideline_id, graph.guideline_title)

    # 3. Exit-condition scan (statin-specific, per guidelines/statins.md)
    #    The first recommendation is used as the recommendation_id for exit
    #    events, since exits short-circuit eligibility evaluation at R1.
    exit_rec_id = graph.recommendations[0].id if graph.recommendations else graph.guideline_id
    exit_fired = False

    for exit_def in _STATIN_EXITS:
        checker = _EXIT_CHECKERS[exit_def["check"]]
        if checker(patient_context, age, graph):
            trace.exit_condition_triggered(
                recommendation_id=exit_rec_id,
                exit=exit_def["token"],
                rationale=exit_def["rationale"],
            )
            exit_fired = True
            break

    recommendations_emitted = 0

    if not exit_fired:
        # Full recommendation evaluation — not exercised in fixture 03.
        # Feature 04 implements this path for the remaining fixtures.
        for rec in graph.recommendations:
            pass  # TODO: feature 04

    # Final event — duration_ms is set to 0 here; the route handler
    # overwrites it with the actual wall-clock duration after evaluate() returns.
    trace.evaluation_completed(recommendations_emitted, duration_ms=0)

    # Build the envelope — wall-clock fields (started_at, completed_at)
    # are injected by the route handler, not by the pure evaluator.
    envelope: dict[str, Any] = {
        "spec_tag": settings.spec_tag,
        "graph_version": settings.graph_version,
        "evaluator_version": settings.evaluator_version,
        "evaluation_time": eval_time,
        "patient_fingerprint": fingerprint,
    }

    # Derive recommendation list from trace events (empty for exit paths)
    derived_recommendations = [
        {
            "recommendation_id": e["recommendation_id"],
            "status": e["status"],
            "evidence_grade": e["evidence_grade"],
            "reason": e["reason"],
            **({"offered_strategies": e["offered_strategies"]} if "offered_strategies" in e else {}),
            **({"satisfying_strategy": e["satisfying_strategy"]} if "satisfying_strategy" in e else {}),
        }
        for e in trace.events
        if e["type"] == "recommendation_emitted"
    ]

    return {
        "envelope": envelope,
        "events": trace.events,
        "recommendations": derived_recommendations,
    }
