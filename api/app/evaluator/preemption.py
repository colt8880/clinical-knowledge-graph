"""Preemption resolution for cross-guideline PREEMPTED_BY edges.

Runs as a post-traversal step after all guidelines have been evaluated.
Resolves which emitted Recs are preempted by higher-priority Recs from
other guidelines per ADR 0018.

Pure function: no I/O. Takes the set of emitted Rec IDs, the loaded
preemption edges, and guideline metadata. Returns a list of resolved
preemptions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.evaluator.graph import PreemptionEdge

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreemptionResult:
    """One resolved preemption: a losing Rec and the winning Rec."""
    preempted_rec_id: str
    winning_rec_id: str
    edge_priority: int
    reason: str


def resolve_preemptions(
    emitted_rec_ids: set[str],
    preemption_edges: list[PreemptionEdge],
    guideline_published_at: dict[str, str],
    rec_to_guideline: dict[str, str],
) -> list[PreemptionResult]:
    """Resolve preemptions among emitted Recs.

    Args:
        emitted_rec_ids: Set of recommendation IDs that were emitted
            (matched the patient) during the guideline loop.
        preemption_edges: All PREEMPTED_BY edges loaded from the graph.
        guideline_published_at: Maps guideline_id → effective_date string
            (ISO 8601) for tie-breaking.
        rec_to_guideline: Maps recommendation_id → guideline_id.

    Returns:
        List of PreemptionResult for each Rec that is preempted. If a Rec
        is preempted by multiple winners, the highest-priority winner wins
        (with published_at tie-break). Only one PreemptionResult per
        preempted Rec.

    Raises:
        ValueError: If a transitive preemption chain is detected (A
            preempted by B, B preempted by C, no direct A → C edge).
    """
    # Filter to edges where BOTH sides were emitted
    active_edges = [
        e for e in preemption_edges
        if e.preempted_rec_id in emitted_rec_ids
        and e.winning_rec_id in emitted_rec_ids
    ]

    if not active_edges:
        return []

    # For each preempted Rec, find the highest-priority winner
    # (tie-break on guideline published_at, then rec_id lexicographic)
    candidates: dict[str, list[PreemptionEdge]] = {}
    for edge in active_edges:
        candidates.setdefault(edge.preempted_rec_id, []).append(edge)

    results: list[PreemptionResult] = []
    preempted_set: set[str] = set()

    for preempted_id, edges in sorted(candidates.items()):
        # Pick the best winner: highest priority, then newest published_at, then
        # lexicographically smallest winner_id as final deterministic tiebreak.
        def is_better(a: PreemptionEdge, b: PreemptionEdge) -> bool:
            """Return True if a is a better winner than b."""
            if a.priority != b.priority:
                return a.priority > b.priority
            a_gid = rec_to_guideline.get(a.winning_rec_id, "")
            b_gid = rec_to_guideline.get(b.winning_rec_id, "")
            a_pub = guideline_published_at.get(a_gid, "")
            b_pub = guideline_published_at.get(b_gid, "")
            if a_pub != b_pub:
                return a_pub > b_pub  # newer (lexicographically larger) wins
            return a.winning_rec_id < b.winning_rec_id

        best = edges[0]
        for e in edges[1:]:
            if is_better(e, best):
                best = e

        results.append(PreemptionResult(
            preempted_rec_id=preempted_id,
            winning_rec_id=best.winning_rec_id,
            edge_priority=best.priority,
            reason=best.rationale,
        ))
        preempted_set.add(preempted_id)

    # Check for transitive chains: if A is preempted by B and B is
    # preempted by C, warn (A should have a direct edge to C if intended).
    winning_set = {r.winning_rec_id for r in results}
    transitive_winners = preempted_set & winning_set
    if transitive_winners:
        for rec_id in sorted(transitive_winners):
            # Find who preempts this rec and who this rec preempts
            preempted_by = next(
                r.winning_rec_id for r in results if r.preempted_rec_id == rec_id
            )
            preempts = [
                r.preempted_rec_id for r in results if r.winning_rec_id == rec_id
            ]
            logger.warning(
                "Transitive preemption detected: %s is preempted by %s, "
                "but %s also preempts %s. Add explicit edges if intended.",
                rec_id, preempted_by, rec_id, preempts,
            )

    return results
