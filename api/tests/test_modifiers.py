"""Unit tests for modifier resolution (F26).

Tests the pure resolve_modifiers() function and the engine integration.
No Neo4j required — uses in-memory graph snapshots.
"""

from __future__ import annotations

import json

import pytest

from app.evaluator.engine import evaluate
from app.evaluator.graph import (
    GraphSnapshot,
    ModifierEdge,
    PreemptionEdge,
    RecommendationNode,
)
from app.evaluator.modifiers import resolve_modifiers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_modifier(source: str, target: str, nature: str = "intensity_reduction") -> ModifierEdge:
    return ModifierEdge(
        source_rec_id=source,
        target_rec_id=target,
        nature=nature,
        note=f"{source} modifies {target}",
    )


def _make_preemption(preempted: str, winner: str, priority: int = 200) -> PreemptionEdge:
    return PreemptionEdge(
        preempted_rec_id=preempted,
        winning_rec_id=winner,
        priority=priority,
        rationale=f"{winner} preempts {preempted}",
    )


def _make_simple_graph(
    guideline_id: str,
    rec_ids: list[str],
) -> GraphSnapshot:
    """Build a minimal graph with recommendations that always match (no eligibility)."""
    recs = [
        RecommendationNode(
            id=rid,
            title=f"Test rec {rid}",
            evidence_grade="B",
            intent="primary_prevention",
            trigger="patient_state",
            structured_eligibility=None,
            strategy_ids=[],
        )
        for rid in rec_ids
    ]
    return GraphSnapshot(
        guideline_id=guideline_id,
        guideline_title=f"Test guideline {guideline_id}",
        recommendations=recs,
        entities={},
        strategies={},
    )


BASIC_PATIENT = {
    "evaluation_time": "2026-04-15T10:00:00Z",
    "patient": {
        "date_of_birth": "1970-01-01",
        "administrative_sex": "male",
    },
    "conditions": [],
    "observations": [],
    "medications": [],
    "social_history": {},
    "risk_scores": {},
    "completeness": {},
}


# ---------------------------------------------------------------------------
# Unit tests for resolve_modifiers()
# ---------------------------------------------------------------------------

class TestResolveModifiers:
    """Test the pure modifier resolution function."""

    def test_no_edges(self):
        """No modifier edges → no results."""
        result = resolve_modifiers(
            emitted_rec_ids={"rec:a", "rec:b"},
            preempted_rec_ids=set(),
            modifier_edges=[],
            rec_to_guideline={},
        )
        assert result == []

    def test_no_emitted_recs(self):
        """No emitted recs → no results even with edges."""
        result = resolve_modifiers(
            emitted_rec_ids=set(),
            preempted_rec_ids=set(),
            modifier_edges=[_make_modifier("rec:a", "rec:b")],
            rec_to_guideline={},
        )
        assert result == []

    def test_source_not_emitted(self):
        """Source not emitted → modifier does not activate."""
        result = resolve_modifiers(
            emitted_rec_ids={"rec:b"},
            preempted_rec_ids=set(),
            modifier_edges=[_make_modifier("rec:a", "rec:b")],
            rec_to_guideline={"rec:b": "g2"},
        )
        assert result == []

    def test_target_not_emitted(self):
        """Target not emitted → modifier does not activate."""
        result = resolve_modifiers(
            emitted_rec_ids={"rec:a"},
            preempted_rec_ids=set(),
            modifier_edges=[_make_modifier("rec:a", "rec:b")],
            rec_to_guideline={"rec:a": "g1"},
        )
        assert result == []

    def test_basic_modifier(self):
        """Both sides emitted, no preemption → modifier fires."""
        result = resolve_modifiers(
            emitted_rec_ids={"rec:a", "rec:b"},
            preempted_rec_ids=set(),
            modifier_edges=[_make_modifier("rec:a", "rec:b")],
            rec_to_guideline={"rec:a": "g1", "rec:b": "g2"},
        )
        assert len(result) == 1
        assert result[0].source_rec_id == "rec:a"
        assert result[0].target_rec_id == "rec:b"
        assert result[0].nature == "intensity_reduction"
        assert result[0].source_guideline_id == "g1"
        assert result[0].target_guideline_id == "g2"

    def test_preempted_target_suppressed(self):
        """Preempted target → modifier is suppressed (ADR 0019)."""
        result = resolve_modifiers(
            emitted_rec_ids={"rec:a", "rec:b"},
            preempted_rec_ids={"rec:b"},
            modifier_edges=[_make_modifier("rec:a", "rec:b")],
            rec_to_guideline={"rec:a": "g1", "rec:b": "g2"},
        )
        assert result == []

    def test_preempted_source_still_fires(self):
        """Preempted source → modifier still fires (source preemption is irrelevant).

        The source Rec being preempted does not suppress its modifiers on other
        non-preempted targets. The source was still emitted (matched the patient).
        """
        result = resolve_modifiers(
            emitted_rec_ids={"rec:source", "rec:target"},
            preempted_rec_ids={"rec:source"},  # source is preempted
            modifier_edges=[_make_modifier("rec:source", "rec:target")],
            rec_to_guideline={"rec:source": "g1", "rec:target": "g2"},
        )
        assert len(result) == 1
        assert result[0].source_rec_id == "rec:source"

    def test_multiple_modifiers_on_same_target(self):
        """Multiple modifiers on the same target all fire."""
        result = resolve_modifiers(
            emitted_rec_ids={"rec:a", "rec:b", "rec:c"},
            preempted_rec_ids=set(),
            modifier_edges=[
                _make_modifier("rec:a", "rec:c"),
                _make_modifier("rec:b", "rec:c"),
            ],
            rec_to_guideline={"rec:a": "g1", "rec:b": "g1", "rec:c": "g2"},
        )
        assert len(result) == 2
        target_ids = {r.target_rec_id for r in result}
        assert target_ids == {"rec:c"}

    def test_multiple_targets_from_same_source(self):
        """One source modifies multiple targets."""
        result = resolve_modifiers(
            emitted_rec_ids={"rec:src", "rec:t1", "rec:t2"},
            preempted_rec_ids=set(),
            modifier_edges=[
                _make_modifier("rec:src", "rec:t1"),
                _make_modifier("rec:src", "rec:t2"),
            ],
            rec_to_guideline={"rec:src": "g1", "rec:t1": "g2", "rec:t2": "g3"},
        )
        assert len(result) == 2

    def test_deterministic_ordering(self):
        """Results are in deterministic order (source_guideline_id, source_rec_id, target_rec_id)."""
        result = resolve_modifiers(
            emitted_rec_ids={"rec:z", "rec:a", "rec:t"},
            preempted_rec_ids=set(),
            modifier_edges=[
                _make_modifier("rec:z", "rec:t"),
                _make_modifier("rec:a", "rec:t"),
            ],
            rec_to_guideline={"rec:z": "g2", "rec:a": "g1", "rec:t": "g3"},
        )
        source_gids = [r.source_guideline_id for r in result]
        assert source_gids == sorted(source_gids)

    def test_different_nature_values(self):
        """Different nature values are preserved."""
        result = resolve_modifiers(
            emitted_rec_ids={"rec:a", "rec:b"},
            preempted_rec_ids=set(),
            modifier_edges=[_make_modifier("rec:a", "rec:b", nature="monitoring")],
            rec_to_guideline={"rec:a": "g1", "rec:b": "g2"},
        )
        assert len(result) == 1
        assert result[0].nature == "monitoring"


# ---------------------------------------------------------------------------
# Engine integration tests (in-memory, no Neo4j)
# ---------------------------------------------------------------------------

class TestEngineModifierIntegration:
    """Test modifier integration in the evaluate() function."""

    def test_no_modifier_edges_no_change(self):
        """Without modifier edges, evaluate behaves as before."""
        graphs = [_make_simple_graph("guideline:aaa", ["rec:a1"])]
        result = evaluate(BASIC_PATIENT, graphs, modifier_edges=[])

        assert len(result["recommendations"]) == 1
        assert result["recommendations"][0]["modifiers"] == []
        modifier_events = [
            e for e in result["events"] if e["type"] == "cross_guideline_match"
        ]
        assert len(modifier_events) == 0

    def test_modifier_fires_when_both_match(self):
        """When both Recs match and a MODIFIES edge exists, modifier event emitted."""
        graphs = [
            _make_simple_graph("guideline:aaa", ["rec:source"]),
            _make_simple_graph("guideline:zzz", ["rec:target"]),
        ]
        modifiers = [_make_modifier("rec:source", "rec:target")]

        result = evaluate(BASIC_PATIENT, graphs, modifier_edges=modifiers)

        # Both recs emitted
        assert len(result["recommendations"]) == 2

        # cross_guideline_match event present
        modifier_events = [
            e for e in result["events"] if e["type"] == "cross_guideline_match"
        ]
        assert len(modifier_events) == 1
        me = modifier_events[0]
        assert me["source_rec_id"] == "rec:source"
        assert me["target_rec_id"] == "rec:target"
        assert me["nature"] == "intensity_reduction"
        assert me["guideline_id"] is None  # envelope-level

        # Derived recommendation has modifiers field
        target_rec = next(
            r for r in result["recommendations"]
            if r["recommendation_id"] == "rec:target"
        )
        assert len(target_rec["modifiers"]) == 1
        assert target_rec["modifiers"][0]["source_rec_id"] == "rec:source"
        assert target_rec["modifiers"][0]["nature"] == "intensity_reduction"

        source_rec = next(
            r for r in result["recommendations"]
            if r["recommendation_id"] == "rec:source"
        )
        assert source_rec["modifiers"] == []

    def test_modifier_suppressed_when_target_preempted(self):
        """Preempted target → modifier not emitted (ADR 0019)."""
        graphs = [
            _make_simple_graph("guideline:aaa", ["rec:source", "rec:loser"]),
            _make_simple_graph("guideline:zzz", ["rec:winner"]),
        ]
        preemption = [_make_preemption("rec:loser", "rec:winner")]
        modifiers = [_make_modifier("rec:source", "rec:loser")]

        result = evaluate(
            BASIC_PATIENT, graphs,
            preemption_edges=preemption,
            modifier_edges=modifiers,
        )

        # Preemption fires
        preemption_events = [
            e for e in result["events"] if e["type"] == "preemption_resolved"
        ]
        assert len(preemption_events) == 1

        # Modifier is suppressed
        modifier_events = [
            e for e in result["events"] if e["type"] == "cross_guideline_match"
        ]
        assert len(modifier_events) == 0

        # Preempted rec has no modifiers
        loser_rec = next(
            r for r in result["recommendations"]
            if r["recommendation_id"] == "rec:loser"
        )
        assert loser_rec["modifiers"] == []
        assert loser_rec["preempted_by"] == "rec:winner"

    def test_modifier_event_ordering(self):
        """Modifier events come after preemption but before evaluation_completed."""
        graphs = [
            _make_simple_graph("guideline:aaa", ["rec:src"]),
            _make_simple_graph("guideline:zzz", ["rec:tgt"]),
        ]
        modifiers = [_make_modifier("rec:src", "rec:tgt")]

        result = evaluate(BASIC_PATIENT, graphs, modifier_edges=modifiers)

        event_types = [e["type"] for e in result["events"]]
        modifier_idx = event_types.index("cross_guideline_match")
        completed_idx = event_types.index("evaluation_completed")
        last_exited_idx = max(
            i for i, t in enumerate(event_types) if t == "guideline_exited"
        )

        assert modifier_idx > last_exited_idx
        assert modifier_idx < completed_idx

    def test_modifier_with_preemption_ordering(self):
        """Modifier events come AFTER preemption_resolved events."""
        graphs = [
            _make_simple_graph("guideline:aaa", ["rec:src", "rec:loser"]),
            _make_simple_graph("guideline:mmm", ["rec:non_preempted_target"]),
            _make_simple_graph("guideline:zzz", ["rec:winner"]),
        ]
        preemption = [_make_preemption("rec:loser", "rec:winner")]
        modifiers = [_make_modifier("rec:src", "rec:non_preempted_target")]

        result = evaluate(
            BASIC_PATIENT, graphs,
            preemption_edges=preemption,
            modifier_edges=modifiers,
        )

        event_types = [e["type"] for e in result["events"]]
        preemption_idx = event_types.index("preemption_resolved")
        modifier_idx = event_types.index("cross_guideline_match")

        assert modifier_idx > preemption_idx

    def test_determinism_with_modifiers(self):
        """Two runs with same inputs produce byte-identical traces."""
        graphs = [
            _make_simple_graph("guideline:aaa", ["rec:src"]),
            _make_simple_graph("guideline:zzz", ["rec:tgt"]),
        ]
        modifiers = [_make_modifier("rec:src", "rec:tgt")]

        r1 = evaluate(BASIC_PATIENT, graphs, modifier_edges=modifiers)
        r2 = evaluate(BASIC_PATIENT, graphs, modifier_edges=modifiers)

        j1 = json.dumps(r1, sort_keys=True, separators=(",", ":"))
        j2 = json.dumps(r2, sort_keys=True, separators=(",", ":"))
        assert j1 == j2

    def test_modifiers_in_recommendations_by_guideline(self):
        """modifiers field appears in recommendations_by_guideline too."""
        graphs = [
            _make_simple_graph("guideline:aaa", ["rec:src"]),
            _make_simple_graph("guideline:zzz", ["rec:tgt"]),
        ]
        modifiers = [_make_modifier("rec:src", "rec:tgt")]

        result = evaluate(BASIC_PATIENT, graphs, modifier_edges=modifiers)

        zzz_recs = result["recommendations_by_guideline"]["guideline:zzz"]
        assert len(zzz_recs) == 1
        assert len(zzz_recs[0]["modifiers"]) == 1
        assert zzz_recs[0]["modifiers"][0]["source_rec_id"] == "rec:src"

    def test_no_modifier_edges_backward_compatible(self):
        """Existing preemption-only test still works with modifiers parameter."""
        graphs = [
            _make_simple_graph("guideline:aaa", ["rec:loser"]),
            _make_simple_graph("guideline:zzz", ["rec:winner"]),
        ]
        edges = [_make_preemption("rec:loser", "rec:winner")]

        result = evaluate(BASIC_PATIENT, graphs, preemption_edges=edges)

        # Preemption still works; modifiers field present but empty
        loser_rec = next(
            r for r in result["recommendations"]
            if r["recommendation_id"] == "rec:loser"
        )
        assert loser_rec["preempted_by"] == "rec:winner"
        assert loser_rec["modifiers"] == []
