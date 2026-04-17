"""Unit tests for Arm C serialization."""

import pytest

from harness.serialization import (
    build_arm_c_context,
    serialize_subgraph,
    serialize_trace_summary,
)


SAMPLE_TRACE = {
    "envelope": {
        "spec_tag": "spec/v2-2026-04-15",
        "graph_version": "test",
        "evaluator_version": "test",
    },
    "events": [
        {
            "seq": 1,
            "type": "evaluation_started",
            "guideline_id": None,
            "patient_age_years": 55,
            "patient_sex": "male",
            "guidelines_in_scope": ["guideline:uspstf-statin-2022"],
        },
        {
            "seq": 2,
            "type": "guideline_entered",
            "guideline_id": "guideline:uspstf-statin-2022",
            "guideline_title": "USPSTF 2022 Statin Primary Prevention",
        },
        {
            "seq": 3,
            "type": "recommendation_considered",
            "guideline_id": "guideline:uspstf-statin-2022",
            "recommendation_id": "rec:statin-initiate-grade-b",
            "recommendation_title": "Initiate statin (Grade B)",
            "evidence_grade": "B",
            "intent": "primary_prevention",
            "trigger": "patient_state",
        },
        {
            "seq": 4,
            "type": "risk_score_lookup",
            "guideline_id": "guideline:uspstf-statin-2022",
            "score_name": "ascvd_10yr",
            "resolution": "supplied",
            "supplied_value": 18.2,
        },
        {
            "seq": 5,
            "type": "strategy_considered",
            "guideline_id": "guideline:uspstf-statin-2022",
            "recommendation_id": "rec:statin-initiate-grade-b",
            "strategy_id": "strategy:statin-moderate-intensity",
            "strategy_name": "Moderate-intensity statin therapy",
        },
        {
            "seq": 6,
            "type": "action_checked",
            "guideline_id": "guideline:uspstf-statin-2022",
            "recommendation_id": "rec:statin-initiate-grade-b",
            "strategy_id": "strategy:statin-moderate-intensity",
            "action_node_id": "med:atorvastatin",
            "action_entity_type": "Medication",
            "satisfied": False,
            "inputs_read": [],
        },
        {
            "seq": 7,
            "type": "strategy_resolved",
            "guideline_id": "guideline:uspstf-statin-2022",
            "recommendation_id": "rec:statin-initiate-grade-b",
            "strategy_id": "strategy:statin-moderate-intensity",
            "satisfied": False,
        },
        {
            "seq": 8,
            "type": "recommendation_emitted",
            "guideline_id": "guideline:uspstf-statin-2022",
            "recommendation_id": "rec:statin-initiate-grade-b",
            "status": "due",
            "evidence_grade": "B",
            "reason": "Patient eligible, no strategy satisfied",
            "offered_strategies": ["strategy:statin-moderate-intensity"],
        },
        {
            "seq": 9,
            "type": "guideline_exited",
            "guideline_id": "guideline:uspstf-statin-2022",
            "recommendations_emitted": 1,
        },
        {
            "seq": 10,
            "type": "evaluation_completed",
            "guideline_id": None,
            "recommendations_emitted": 1,
            "duration_ms": 10,
        },
    ],
}


class TestSerializeTraceSummary:
    def test_extracts_matched_recs(self):
        summary = serialize_trace_summary(SAMPLE_TRACE)
        assert len(summary["matched_recs"]) == 1
        rec = summary["matched_recs"][0]
        assert rec["recommendation_id"] == "rec:statin-initiate-grade-b"
        assert rec["status"] == "due"
        assert rec["evidence_grade"] == "B"

    def test_empty_preemption_and_modifier(self):
        summary = serialize_trace_summary(SAMPLE_TRACE)
        assert summary["preemption_events"] == []
        assert summary["modifier_events"] == []

    def test_exit_conditions_extracted(self):
        trace = {
            "events": [
                {
                    "seq": 1,
                    "type": "exit_condition_triggered",
                    "guideline_id": "guideline:uspstf-statin-2022",
                    "recommendation_id": "rec:statin-initiate-grade-b",
                    "exit": "out_of_scope_secondary_prevention",
                    "rationale": "Established ASCVD",
                },
            ]
        }
        summary = serialize_trace_summary(trace)
        assert len(summary["exit_conditions"]) == 1
        assert summary["exit_conditions"][0]["exit"] == "out_of_scope_secondary_prevention"


class TestSerializeSubgraph:
    def test_extracts_nodes(self):
        subgraph = serialize_subgraph(SAMPLE_TRACE)
        node_ids = {n["id"] for n in subgraph["nodes"]}
        assert "rec:statin-initiate-grade-b" in node_ids
        assert "guideline:uspstf-statin-2022" in node_ids
        assert "strategy:statin-moderate-intensity" in node_ids
        assert "med:atorvastatin" in node_ids

    def test_extracts_edges(self):
        subgraph = serialize_subgraph(SAMPLE_TRACE)
        edge_types = {(e["source"], e["type"], e["target"]) for e in subgraph["edges"]}
        assert ("rec:statin-initiate-grade-b", "OFFERS", "strategy:statin-moderate-intensity") in edge_types
        assert ("strategy:statin-moderate-intensity", "INCLUDES_ACTION", "med:atorvastatin") in edge_types

    def test_rendered_prose_not_empty(self):
        subgraph = serialize_subgraph(SAMPLE_TRACE)
        assert len(subgraph["rendered_prose"]) > 0
        assert "USPSTF 2022" in subgraph["rendered_prose"]

    def test_no_duplicate_nodes(self):
        subgraph = serialize_subgraph(SAMPLE_TRACE)
        node_ids = [n["id"] for n in subgraph["nodes"]]
        assert len(node_ids) == len(set(node_ids))


class TestBuildArmCContext:
    def test_has_expected_top_level_keys(self):
        ctx = build_arm_c_context(SAMPLE_TRACE)
        assert "trace_summary" in ctx
        assert "subgraph" in ctx

    def test_trace_summary_has_expected_keys(self):
        ctx = build_arm_c_context(SAMPLE_TRACE)
        summary = ctx["trace_summary"]
        assert "matched_recs" in summary
        assert "preemption_events" in summary
        assert "modifier_events" in summary

    def test_subgraph_has_expected_keys(self):
        ctx = build_arm_c_context(SAMPLE_TRACE)
        subgraph = ctx["subgraph"]
        assert "nodes" in subgraph
        assert "edges" in subgraph
        assert "rendered_prose" in subgraph
