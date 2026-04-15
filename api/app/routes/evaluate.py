"""POST /evaluate endpoint — accepts PatientContext, returns EvalTrace."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.evaluator.engine import evaluate
from app.evaluator.graph import load_graph

router = APIRouter(tags=["evaluate"])


class EvaluateRequest(BaseModel):
    patient_context: dict[str, Any]
    options: dict[str, Any] = Field(default_factory=dict)


@router.post("/evaluate")
async def post_evaluate(request: EvaluateRequest) -> dict[str, Any]:
    """Run the evaluator against a PatientContext, return the EvalTrace.

    Loads the graph snapshot from Neo4j, then calls the pure evaluate()
    function. The evaluator itself does no I/O.
    """
    pc = request.patient_context

    # Validate required top-level fields
    if "evaluation_time" not in pc:
        raise HTTPException(status_code=400, detail="evaluation_time is required")
    if "patient" not in pc:
        raise HTTPException(status_code=400, detail="patient is required")
    patient = pc["patient"]
    if "date_of_birth" not in patient:
        raise HTTPException(status_code=400, detail="patient.date_of_birth is required")
    if "administrative_sex" not in patient:
        raise HTTPException(status_code=400, detail="patient.administrative_sex is required")

    graph = await load_graph()

    # Wall-clock timing is the route handler's responsibility, not the
    # pure evaluator's. Stamp before/after and inject into the trace.
    started_at = datetime.now(timezone.utc)
    trace = evaluate(pc, graph)
    completed_at = datetime.now(timezone.utc)

    duration_ms = int((completed_at - started_at).total_seconds() * 1000)
    trace["envelope"]["started_at"] = started_at.isoformat().replace("+00:00", "Z")
    trace["envelope"]["completed_at"] = completed_at.isoformat().replace("+00:00", "Z")
    # Overwrite the placeholder duration_ms on the final evaluation_completed event
    for event in trace["events"]:
        if event["type"] == "evaluation_completed":
            event["duration_ms"] = duration_ms

    return trace
