"""POST /evaluate endpoint — accepts PatientContext, returns EvalTrace."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.evaluator.engine import evaluate
from app.evaluator.graph import load_graph

router = APIRouter(tags=["evaluate"])


def _problem(status: int, title: str, detail: str, errors: list[dict] | None = None) -> JSONResponse:
    """Return an RFC 7807-style Problem response matching api.openapi.yaml."""
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status,
        "detail": detail,
    }
    if errors:
        body["errors"] = errors
    return JSONResponse(status_code=status, content=body)


class EvaluateRequest(BaseModel):
    patient_context: dict[str, Any]
    options: dict[str, Any] = Field(default_factory=dict)


@router.post("/evaluate")
async def post_evaluate(request: EvaluateRequest) -> Any:
    """Run the evaluator against a PatientContext, return the EvalTrace.

    Loads the graph snapshot from Neo4j, then calls the pure evaluate()
    function. The evaluator itself does no I/O.
    """
    pc = request.patient_context

    # Validate required top-level fields per patient-context.schema.json.
    missing: list[dict[str, str]] = []
    if "evaluation_time" not in pc:
        missing.append({"path": "evaluation_time", "message": "required"})
    if "patient" not in pc:
        missing.append({"path": "patient", "message": "required"})
    else:
        patient = pc["patient"]
        if "date_of_birth" not in patient:
            missing.append({"path": "patient.date_of_birth", "message": "required"})
        if "administrative_sex" not in patient:
            missing.append({"path": "patient.administrative_sex", "message": "required"})
    if missing:
        return _problem(
            400,
            "Invalid PatientContext",
            "Required fields are missing from the patient context.",
            errors=missing,
        )

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
