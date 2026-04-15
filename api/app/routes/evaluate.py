"""POST /evaluate endpoint — accepts PatientContext, returns EvalTrace."""

from __future__ import annotations

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
    trace = evaluate(pc, graph)
    return trace
