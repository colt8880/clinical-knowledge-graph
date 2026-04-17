"""Modifier resolution for cross-guideline MODIFIES edges.

Runs as a post-traversal step after preemption resolution (F25) and
before evaluation_completed. Resolves which emitted Recs have active
MODIFIES edges from other emitted Recs per ADR 0019.

Pure function: no I/O. Takes the set of emitted Rec IDs, preempted Rec
IDs, the loaded modifier edges, and guideline metadata. Returns a list
of resolved modifiers.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.evaluator.graph import ModifierEdge


@dataclass(frozen=True)
class ModifierResult:
    """One resolved modifier: source Rec annotates target Rec."""
    source_rec_id: str
    target_rec_id: str
    nature: str
    note: str
    source_guideline_id: str
    target_guideline_id: str


def resolve_modifiers(
    emitted_rec_ids: set[str],
    preempted_rec_ids: set[str],
    modifier_edges: list[ModifierEdge],
    rec_to_guideline: dict[str, str],
) -> list[ModifierResult]:
    """Resolve modifiers among emitted, non-preempted Recs.

    Args:
        emitted_rec_ids: Set of recommendation IDs that were emitted
            (matched the patient) during the guideline loop.
        preempted_rec_ids: Set of recommendation IDs that were preempted.
            Preempted targets do not receive modifier events (ADR 0019).
        modifier_edges: All MODIFIES edges loaded from the graph.
        rec_to_guideline: Maps recommendation_id → guideline_id.

    Returns:
        List of ModifierResult ordered deterministically by
        (source_guideline_id, source_rec_id, target_rec_id).
    """
    if not modifier_edges or not emitted_rec_ids:
        return []

    results: list[ModifierResult] = []

    for edge in modifier_edges:
        # Both source and target must have been emitted
        if edge.source_rec_id not in emitted_rec_ids:
            continue
        if edge.target_rec_id not in emitted_rec_ids:
            continue

        # Preempted targets do not receive modifiers (ADR 0019)
        if edge.target_rec_id in preempted_rec_ids:
            continue

        source_gid = rec_to_guideline.get(edge.source_rec_id, "")
        target_gid = rec_to_guideline.get(edge.target_rec_id, "")

        results.append(ModifierResult(
            source_rec_id=edge.source_rec_id,
            target_rec_id=edge.target_rec_id,
            nature=edge.nature,
            note=edge.note,
            source_guideline_id=source_gid,
            target_guideline_id=target_gid,
        ))

    # Deterministic ordering per F26 spec
    results.sort(key=lambda r: (r.source_guideline_id, r.source_rec_id, r.target_rec_id))

    return results
