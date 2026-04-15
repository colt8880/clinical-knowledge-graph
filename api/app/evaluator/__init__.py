"""Trace-first evaluator for the clinical knowledge graph.

Public API: evaluate(patient_context, graph_snapshot) -> EvalTrace dict.
"""

from app.evaluator.engine import evaluate

__all__ = ["evaluate"]
