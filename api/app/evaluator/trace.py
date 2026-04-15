"""EvalTrace event models and trace-builder.

All models follow docs/contracts/eval-trace.schema.json.
The TraceBuilder assigns monotonic seq values and collects events.
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
    """Accumulates trace events with monotonic seq assignment."""

    def __init__(self) -> None:
        self._seq = 0
        self.events: list[dict[str, Any]] = []

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def emit(self, event_type: str, **fields: Any) -> dict[str, Any]:
        event: dict[str, Any] = {
            "seq": self._next_seq(),
            "type": event_type,
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

    def exit_condition_triggered(
        self, recommendation_id: str, exit: str, rationale: str
    ) -> None:
        self.emit(
            "exit_condition_triggered",
            recommendation_id=recommendation_id,
            exit=exit,
            rationale=rationale,
        )

    def evaluation_completed(
        self, recommendations_emitted: int, duration_ms: int
    ) -> None:
        self.emit(
            "evaluation_completed",
            recommendations_emitted=recommendations_emitted,
            duration_ms=duration_ms,
        )
