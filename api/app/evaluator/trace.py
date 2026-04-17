"""EvalTrace event models and trace-builder.

All models follow docs/contracts/eval-trace.schema.json.
The TraceBuilder assigns monotonic seq values and collects events.

Every event carries a guideline_id field (v1, F21). For envelope-level
events (evaluation_started, evaluation_completed) that sit outside any
guideline bracket, guideline_id is null. For all other events, it is set
from the enclosing guideline context via set_guideline_context().
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def patient_fingerprint(patient_context: dict[str, Any]) -> str:
    """Deterministic SHA-256 hash of the patient context (canonical JSON)."""
    canonical = json.dumps(patient_context, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_age(date_of_birth: str, evaluation_time: str) -> int:
    """Compute age in whole years (floor) from DOB and evaluation_time."""
    from datetime import date as date_type

    if "T" in evaluation_time:
        eval_date = datetime.fromisoformat(evaluation_time.replace("Z", "+00:00")).date()
    else:
        eval_date = date_type.fromisoformat(evaluation_time)

    dob = date_type.fromisoformat(date_of_birth)
    age = eval_date.year - dob.year
    if (eval_date.month, eval_date.day) < (dob.month, dob.day):
        age -= 1
    return age


class TraceBuilder:
    """Accumulates trace events with monotonic seq assignment.

    Every event carries a guideline_id field. Use set_guideline_context()
    to set the current guideline; envelope-level events (before the first
    guideline or after the last) get guideline_id=None.
    """

    def __init__(self) -> None:
        self._seq = 0
        self.events: list[dict[str, Any]] = []
        self._guideline_id: str | None = None

    def set_guideline_context(self, guideline_id: str | None) -> None:
        """Set the current guideline context for subsequent events."""
        self._guideline_id = guideline_id

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def emit(self, event_type: str, **fields: Any) -> dict[str, Any]:
        event: dict[str, Any] = {
            "seq": self._next_seq(),
            "type": event_type,
            "guideline_id": self._guideline_id,
            **fields,
        }
        self.events.append(event)
        return event

    def evaluation_started(
        self, patient_age_years: int, patient_sex: str, guidelines_in_scope: list[str]
    ) -> None:
        self.emit(
            "evaluation_started",
            patient_age_years=patient_age_years,
            patient_sex=patient_sex,
            guidelines_in_scope=guidelines_in_scope,
        )

    def guideline_entered(self, guideline_id: str, guideline_title: str) -> None:
        self.emit(
            "guideline_entered",
            guideline_id=guideline_id,
            guideline_title=guideline_title,
        )

    def guideline_exited(self, guideline_id: str, recommendations_emitted: int) -> None:
        """Emitted at the end of each guideline's traversal."""
        self.emit(
            "guideline_exited",
            guideline_id=guideline_id,
            recommendations_emitted=recommendations_emitted,
        )

    def exit_condition_triggered(
        self, recommendation_id: str, exit: str, rationale: str
    ) -> None:
        self.emit(
            "exit_condition_triggered",
            recommendation_id=recommendation_id,
            exit=exit,
            rationale=rationale,
        )

    def recommendation_considered(
        self,
        recommendation_id: str,
        recommendation_title: str,
        evidence_grade: str,
        intent: str,
        trigger: str,
    ) -> None:
        self.emit(
            "recommendation_considered",
            recommendation_id=recommendation_id,
            recommendation_title=recommendation_title,
            evidence_grade=evidence_grade,
            intent=intent,
            trigger=trigger,
        )

    def eligibility_evaluation_started(self, recommendation_id: str) -> None:
        self.emit(
            "eligibility_evaluation_started",
            recommendation_id=recommendation_id,
        )

    def predicate_evaluated(
        self,
        recommendation_id: str,
        path: list[str | int],
        predicate: str,
        args: dict[str, Any],
        inputs_read: list[dict[str, Any]],
        result: str,
        missing_data_policy_applied: str | None = None,
        note: str | None = None,
    ) -> None:
        self.emit(
            "predicate_evaluated",
            recommendation_id=recommendation_id,
            path=path,
            predicate=predicate,
            args=args,
            inputs_read=inputs_read,
            result=result,
            missing_data_policy_applied=missing_data_policy_applied,
            note=note,
        )

    def composite_resolved(
        self,
        recommendation_id: str,
        path: list[str | int],
        operator: str,
        result: str,
        short_circuited: bool,
    ) -> None:
        self.emit(
            "composite_resolved",
            recommendation_id=recommendation_id,
            path=path,
            operator=operator,
            result=result,
            short_circuited=short_circuited,
        )

    def eligibility_evaluation_completed(
        self,
        recommendation_id: str,
        result: str,
        final_value: str,
    ) -> None:
        self.emit(
            "eligibility_evaluation_completed",
            recommendation_id=recommendation_id,
            result=result,
            final_value=final_value,
        )

    def strategy_considered(
        self,
        recommendation_id: str,
        strategy_id: str,
        strategy_name: str,
    ) -> None:
        self.emit(
            "strategy_considered",
            recommendation_id=recommendation_id,
            strategy_id=strategy_id,
            strategy_name=strategy_name,
        )

    def action_checked(
        self,
        recommendation_id: str,
        strategy_id: str,
        action_node_id: str,
        action_entity_type: str,
        inputs_read: list[dict[str, Any]],
        satisfied: bool,
        cadence: str | None = None,
        lookback: str | None = None,
        note: str | None = None,
    ) -> None:
        self.emit(
            "action_checked",
            recommendation_id=recommendation_id,
            strategy_id=strategy_id,
            action_node_id=action_node_id,
            action_entity_type=action_entity_type,
            cadence=cadence,
            lookback=lookback,
            inputs_read=inputs_read,
            satisfied=satisfied,
            note=note,
        )

    def strategy_resolved(
        self,
        recommendation_id: str,
        strategy_id: str,
        satisfied: bool,
    ) -> None:
        self.emit(
            "strategy_resolved",
            recommendation_id=recommendation_id,
            strategy_id=strategy_id,
            satisfied=satisfied,
        )

    def risk_score_lookup(
        self,
        score_name: str,
        resolution: str,
        supplied_value: float | None = None,
        supplied_computed_date: str | None = None,
        inputs_read: list[dict[str, Any]] | None = None,
        computed_value: float | None = None,
        method: str | None = None,
        note: str | None = None,
    ) -> None:
        self.emit(
            "risk_score_lookup",
            score_name=score_name,
            resolution=resolution,
            supplied_value=supplied_value,
            supplied_computed_date=supplied_computed_date,
            inputs_read=inputs_read or [],
            computed_value=computed_value,
            method=method,
            note=note,
        )

    def recommendation_emitted(
        self,
        recommendation_id: str,
        status: str,
        evidence_grade: str,
        reason: str,
        offered_strategies: list[str] | None = None,
        satisfying_strategy: str | None = None,
    ) -> None:
        fields: dict[str, Any] = {
            "recommendation_id": recommendation_id,
            "status": status,
            "evidence_grade": evidence_grade,
            "reason": reason,
        }
        if offered_strategies is not None:
            fields["offered_strategies"] = offered_strategies
        if satisfying_strategy is not None:
            fields["satisfying_strategy"] = satisfying_strategy
        self.emit("recommendation_emitted", **fields)

    def cross_guideline_match(
        self,
        source_rec_id: str,
        target_rec_id: str,
        nature: str,
        note: str,
        source_guideline_id: str,
        target_guideline_id: str,
    ) -> None:
        """Append a cross_guideline_match event for a MODIFIES edge (F26).

        Emitted after preemption resolution but before evaluation_completed.
        Does not mutate prior events (append-only).
        """
        self.emit(
            "cross_guideline_match",
            source_rec_id=source_rec_id,
            target_rec_id=target_rec_id,
            nature=nature,
            note=note,
            source_guideline_id=source_guideline_id,
            target_guideline_id=target_guideline_id,
        )

    def preemption_resolved(
        self,
        preempted_rec_id: str,
        winning_rec_id: str,
        edge_priority: int,
        reason: str,
    ) -> None:
        """Append a preemption_resolved event (post-traversal, F25).

        Emitted after all guideline traversals complete but before
        evaluation_completed. Does not mutate prior events (append-only).
        """
        self.emit(
            "preemption_resolved",
            preempted_recommendation_id=preempted_rec_id,
            preempting_recommendation_id=winning_rec_id,
            edge_priority=edge_priority,
            reason=reason,
        )

    def evaluation_completed(
        self, recommendations_emitted: int, duration_ms: int
    ) -> None:
        self.emit(
            "evaluation_completed",
            recommendations_emitted=recommendations_emitted,
            duration_ms=duration_ms,
        )
