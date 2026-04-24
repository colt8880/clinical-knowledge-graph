"""Unit tests for Arm C serialization."""

import pytest

from harness.arms.graph_context import (
    _build_interactions_section,
    _build_negative_evidence_section,
    _build_output_format_instruction,
    _build_satisfied_strategies_section,
    get_prompt,
)
from harness.serialization import (
    _filter_trace_by_relevance,
    build_arm_c_context,
    classify_guideline_relevance,
    serialize_convergence_summary,
    serialize_negative_evidence,
    serialize_satisfied_strategies,
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
        assert "convergence_summary" in ctx

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

    def test_convergence_summary_has_expected_keys(self):
        ctx = build_arm_c_context(SAMPLE_TRACE)
        conv = ctx["convergence_summary"]
        assert "shared_actions" in conv
        assert "convergence_prose" in conv


# --- Multi-guideline trace for convergence tests ---

MULTI_GUIDELINE_TRACE = {
    "envelope": {
        "spec_tag": "spec/v2-2026-04-15",
        "graph_version": "test",
        "evaluator_version": "test",
    },
    "events": [
        # USPSTF guideline
        {"seq": 1, "type": "evaluation_started", "guideline_id": None},
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
            "recommendation_id": "rec:statin-selective-grade-c",
            "recommendation_title": "Selectively offer statin (Grade C)",
            "evidence_grade": "C",
            "intent": "primary_prevention",
            "trigger": "patient_state",
        },
        {
            "seq": 4,
            "type": "strategy_considered",
            "guideline_id": "guideline:uspstf-statin-2022",
            "recommendation_id": "rec:statin-selective-grade-c",
            "strategy_id": "strategy:uspstf-moderate-intensity",
            "strategy_name": "Moderate-intensity statin therapy",
        },
        {
            "seq": 5,
            "type": "action_checked",
            "guideline_id": "guideline:uspstf-statin-2022",
            "recommendation_id": "rec:statin-selective-grade-c",
            "strategy_id": "strategy:uspstf-moderate-intensity",
            "action_node_id": "med:atorvastatin",
            "action_entity_type": "Medication",
            "satisfied": False,
        },
        {
            "seq": 6,
            "type": "action_checked",
            "guideline_id": "guideline:uspstf-statin-2022",
            "recommendation_id": "rec:statin-selective-grade-c",
            "strategy_id": "strategy:uspstf-moderate-intensity",
            "action_node_id": "med:rosuvastatin",
            "action_entity_type": "Medication",
            "satisfied": False,
        },
        {
            "seq": 7,
            "type": "recommendation_emitted",
            "guideline_id": "guideline:uspstf-statin-2022",
            "recommendation_id": "rec:statin-selective-grade-c",
            "status": "due",
            "evidence_grade": "C",
            "reason": "Patient eligible, no strategy satisfied",
            "offered_strategies": ["strategy:uspstf-moderate-intensity"],
        },
        # ACC/AHA guideline
        {
            "seq": 8,
            "type": "guideline_entered",
            "guideline_id": "guideline:acc-aha-cholesterol-2018",
            "guideline_title": "ACC/AHA 2018 Cholesterol",
        },
        {
            "seq": 9,
            "type": "recommendation_considered",
            "guideline_id": "guideline:acc-aha-cholesterol-2018",
            "recommendation_id": "rec:accaha-statin-primary-prevention",
            "recommendation_title": "Statin for primary prevention",
            "evidence_grade": "COR I, LOE A",
            "intent": "primary_prevention",
            "trigger": "patient_state",
        },
        {
            "seq": 10,
            "type": "strategy_considered",
            "guideline_id": "guideline:acc-aha-cholesterol-2018",
            "recommendation_id": "rec:accaha-statin-primary-prevention",
            "strategy_id": "strategy:accaha-moderate-intensity",
            "strategy_name": "Moderate-intensity statin therapy",
        },
        {
            "seq": 11,
            "type": "action_checked",
            "guideline_id": "guideline:acc-aha-cholesterol-2018",
            "recommendation_id": "rec:accaha-statin-primary-prevention",
            "strategy_id": "strategy:accaha-moderate-intensity",
            "action_node_id": "med:atorvastatin",
            "action_entity_type": "Medication",
            "satisfied": False,
        },
        {
            "seq": 12,
            "type": "action_checked",
            "guideline_id": "guideline:acc-aha-cholesterol-2018",
            "recommendation_id": "rec:accaha-statin-primary-prevention",
            "strategy_id": "strategy:accaha-moderate-intensity",
            "action_node_id": "med:rosuvastatin",
            "action_entity_type": "Medication",
            "satisfied": False,
        },
        {
            "seq": 13,
            "type": "recommendation_emitted",
            "guideline_id": "guideline:acc-aha-cholesterol-2018",
            "recommendation_id": "rec:accaha-statin-primary-prevention",
            "status": "due",
            "evidence_grade": "COR I, LOE A",
            "reason": "Patient eligible, no strategy satisfied",
            "offered_strategies": ["strategy:accaha-moderate-intensity"],
        },
        # KDIGO guideline
        {
            "seq": 14,
            "type": "guideline_entered",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "guideline_title": "KDIGO 2024 CKD",
        },
        {
            "seq": 15,
            "type": "recommendation_considered",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "recommendation_id": "rec:kdigo-statin-for-ckd",
            "recommendation_title": "Statin for CKD patients",
            "evidence_grade": "1A",
            "intent": "treatment",
            "trigger": "patient_state",
        },
        {
            "seq": 16,
            "type": "strategy_considered",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "recommendation_id": "rec:kdigo-statin-for-ckd",
            "strategy_id": "strategy:kdigo-statin-therapy",
            "strategy_name": "Statin therapy for CKD",
        },
        {
            "seq": 17,
            "type": "action_checked",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "recommendation_id": "rec:kdigo-statin-for-ckd",
            "strategy_id": "strategy:kdigo-statin-therapy",
            "action_node_id": "med:atorvastatin",
            "action_entity_type": "Medication",
            "satisfied": False,
        },
        {
            "seq": 18,
            "type": "recommendation_emitted",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "recommendation_id": "rec:kdigo-statin-for-ckd",
            "status": "due",
            "evidence_grade": "1A",
            "reason": "Patient eligible, no strategy satisfied",
            "offered_strategies": ["strategy:kdigo-statin-therapy"],
        },
        # KDIGO also checks an entity unique to itself (not shared)
        {
            "seq": 19,
            "type": "recommendation_considered",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "recommendation_id": "rec:kdigo-ckd-monitoring",
            "recommendation_title": "CKD monitoring",
            "evidence_grade": "1B",
            "intent": "monitoring",
            "trigger": "patient_state",
        },
        {
            "seq": 20,
            "type": "strategy_considered",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "recommendation_id": "rec:kdigo-ckd-monitoring",
            "strategy_id": "strategy:kdigo-monitoring",
            "strategy_name": "CKD monitoring protocol",
        },
        {
            "seq": 21,
            "type": "action_checked",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "recommendation_id": "rec:kdigo-ckd-monitoring",
            "strategy_id": "strategy:kdigo-monitoring",
            "action_node_id": "obs:egfr",
            "action_entity_type": "Observation",
            "satisfied": False,
        },
        {
            "seq": 22,
            "type": "recommendation_emitted",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "recommendation_id": "rec:kdigo-ckd-monitoring",
            "status": "due",
            "evidence_grade": "1B",
            "reason": "Monitoring needed",
            "offered_strategies": ["strategy:kdigo-monitoring"],
        },
        {"seq": 23, "type": "evaluation_completed", "guideline_id": None},
    ],
}


class TestCrossGuidelineEvents:
    """Tests for cross-guideline event handling in serialize_trace_summary."""

    def test_preemption_resolved_extracted(self):
        trace = {
            "events": [
                {
                    "seq": 1,
                    "type": "preemption_resolved",
                    "guideline_id": "guideline:uspstf-statin-2022",
                    "preempted_recommendation_id": "rec:statin-initiate-grade-b",
                    "preempting_recommendation_id": "rec:accaha-statin-primary-prevention",
                    "edge_priority": 200,
                    "reason": "ACC/AHA more specific",
                },
            ]
        }
        summary = serialize_trace_summary(trace)
        assert len(summary["preemption_events"]) == 1
        pe = summary["preemption_events"][0]
        assert pe["preempted_recommendation_id"] == "rec:statin-initiate-grade-b"
        assert pe["preempting_recommendation_id"] == "rec:accaha-statin-primary-prevention"

    def test_cross_guideline_match_uses_nature_field(self):
        """The evaluator sends 'nature', not 'match_type'. Serialization must handle this."""
        trace = {
            "events": [
                {
                    "seq": 1,
                    "type": "cross_guideline_match",
                    "guideline_id": "guideline:kdigo-ckd-2024",
                    "source_rec_id": "rec:kdigo-statin-for-ckd",
                    "target_rec_id": "rec:accaha-statin-secondary-prevention",
                    "nature": "intensity_reduction",
                    "note": "KDIGO recommends moderate-intensity",
                    "source_guideline_id": "guideline:kdigo-ckd-2024",
                    "target_guideline_id": "guideline:acc-aha-cholesterol-2018",
                },
            ]
        }
        summary = serialize_trace_summary(trace)
        assert len(summary["modifier_events"]) == 1
        me = summary["modifier_events"][0]
        assert me["match_type"] == "intensity_reduction"
        assert me["source_guideline_id"] == "guideline:kdigo-ckd-2024"
        assert me["target_guideline_id"] == "guideline:acc-aha-cholesterol-2018"

    def test_cross_guideline_match_defaults_to_unknown(self):
        """If neither match_type nor nature is present, defaults to 'unknown'."""
        trace = {
            "events": [
                {
                    "seq": 1,
                    "type": "cross_guideline_match",
                    "guideline_id": "test",
                    "source_guideline_id": "a",
                    "target_guideline_id": "b",
                },
            ]
        }
        summary = serialize_trace_summary(trace)
        assert summary["modifier_events"][0]["match_type"] == "unknown"

    def test_build_arm_c_context_with_cross_guideline_events(self):
        """build_arm_c_context should not crash when trace has cross-guideline events."""
        trace = {
            "events": [
                {
                    "seq": 1,
                    "type": "evaluation_started",
                    "guideline_id": None,
                },
                {
                    "seq": 2,
                    "type": "cross_guideline_match",
                    "guideline_id": "guideline:kdigo-ckd-2024",
                    "source_rec_id": "rec:kdigo-statin-for-ckd",
                    "target_rec_id": "rec:accaha-statin-secondary-prevention",
                    "nature": "intensity_reduction",
                    "note": "test",
                    "source_guideline_id": "guideline:kdigo-ckd-2024",
                    "target_guideline_id": "guideline:acc-aha-cholesterol-2018",
                },
                {
                    "seq": 3,
                    "type": "preemption_resolved",
                    "guideline_id": "guideline:uspstf-statin-2022",
                    "preempted_recommendation_id": "rec:statin-initiate-grade-b",
                    "preempting_recommendation_id": "rec:accaha-statin-primary-prevention",
                    "edge_priority": 200,
                    "reason": "ACC/AHA more specific",
                },
                {
                    "seq": 4,
                    "type": "evaluation_completed",
                    "guideline_id": None,
                },
            ]
        }
        ctx = build_arm_c_context(trace)
        assert len(ctx["trace_summary"]["modifier_events"]) == 1
        assert len(ctx["trace_summary"]["preemption_events"]) == 1


class TestSerializeConvergenceSummary:
    """Tests for serialize_convergence_summary."""

    def test_multi_guideline_shared_statin_medications(self):
        """Three guidelines targeting the same statin meds should appear in shared_actions."""
        subgraph = serialize_subgraph(MULTI_GUIDELINE_TRACE)
        conv = serialize_convergence_summary(MULTI_GUIDELINE_TRACE, subgraph)

        shared_ids = {a["entity_id"] for a in conv["shared_actions"]}
        # atorvastatin is targeted by all 3 guidelines
        assert "med:atorvastatin" in shared_ids
        # rosuvastatin is targeted by USPSTF + ACC/AHA (2 guidelines)
        assert "med:rosuvastatin" in shared_ids

        # Check atorvastatin has all 3 guidelines
        atorva = next(a for a in conv["shared_actions"] if a["entity_id"] == "med:atorvastatin")
        assert atorva["guideline_count"] == 3
        assert atorva["entity_type"] == "Medication"
        assert atorva["convergence_type"] == "reinforcing"
        guideline_names = {rb["guideline"] for rb in atorva["recommended_by"]}
        assert "USPSTF 2022 Statin" in guideline_names
        assert "ACC/AHA 2018 Cholesterol" in guideline_names
        assert "KDIGO 2024 CKD" in guideline_names

    def test_single_guideline_entity_not_in_shared_actions(self):
        """An entity targeted by only one guideline should NOT appear in shared_actions."""
        subgraph = serialize_subgraph(MULTI_GUIDELINE_TRACE)
        conv = serialize_convergence_summary(MULTI_GUIDELINE_TRACE, subgraph)

        shared_ids = {a["entity_id"] for a in conv["shared_actions"]}
        # obs:egfr is only checked by KDIGO — not convergence
        assert "obs:egfr" not in shared_ids

    def test_empty_trace_empty_convergence(self):
        """An empty trace should produce an empty convergence summary."""
        empty_trace = {"events": []}
        subgraph = serialize_subgraph(empty_trace)
        conv = serialize_convergence_summary(empty_trace, subgraph)

        assert conv["shared_actions"] == []
        assert conv["convergence_prose"] == ""

    def test_convergence_prose_nonempty_when_shared_actions_exist(self):
        """Convergence prose should be a non-empty string when shared actions exist."""
        subgraph = serialize_subgraph(MULTI_GUIDELINE_TRACE)
        conv = serialize_convergence_summary(MULTI_GUIDELINE_TRACE, subgraph)

        assert len(conv["convergence_prose"]) > 0
        # v2 prose uses "convergence point" rather than "independently recommended"
        assert "convergence point" in conv["convergence_prose"]

    def test_single_guideline_trace_no_convergence(self):
        """A trace with only one guideline should produce no shared_actions."""
        subgraph = serialize_subgraph(SAMPLE_TRACE)
        conv = serialize_convergence_summary(SAMPLE_TRACE, subgraph)

        assert conv["shared_actions"] == []
        assert conv["convergence_prose"] == ""

    def test_recommended_by_includes_evidence_grade_and_status(self):
        """Each recommended_by entry should carry evidence_grade and status from the trace."""
        subgraph = serialize_subgraph(MULTI_GUIDELINE_TRACE)
        conv = serialize_convergence_summary(MULTI_GUIDELINE_TRACE, subgraph)

        atorva = next(a for a in conv["shared_actions"] if a["entity_id"] == "med:atorvastatin")
        for rb in atorva["recommended_by"]:
            assert rb["evidence_grade"] != ""
            assert rb["status"] != ""
            assert rb["via_strategy"] != ""

    def test_determinism(self):
        """Same trace + same subgraph = same convergence summary."""
        subgraph = serialize_subgraph(MULTI_GUIDELINE_TRACE)
        conv1 = serialize_convergence_summary(MULTI_GUIDELINE_TRACE, subgraph)
        conv2 = serialize_convergence_summary(MULTI_GUIDELINE_TRACE, subgraph)
        assert conv1 == conv2


class TestGroupedConvergence:
    """Tests for v2 grouped convergence output."""

    def test_grouped_convergence_key_exists(self):
        """serialize_convergence_summary should return a grouped_convergence key."""
        subgraph = serialize_subgraph(MULTI_GUIDELINE_TRACE)
        conv = serialize_convergence_summary(MULTI_GUIDELINE_TRACE, subgraph)
        assert "grouped_convergence" in conv

    def test_grouped_by_therapeutic_class(self):
        """Multiple statin medications should be grouped into one therapeutic class."""
        subgraph = serialize_subgraph(MULTI_GUIDELINE_TRACE)
        conv = serialize_convergence_summary(MULTI_GUIDELINE_TRACE, subgraph)
        grouped = conv["grouped_convergence"]

        # All strategies in MULTI_GUIDELINE_TRACE are moderate-intensity,
        # so atorvastatin and rosuvastatin should be in one group
        assert len(grouped) >= 1
        statin_group = next(
            (g for g in grouped if "statin" in g["therapeutic_class"].lower()), None
        )
        assert statin_group is not None
        assert "Moderate" in statin_group["therapeutic_class"]
        # Both atorvastatin and rosuvastatin should be members
        assert "med:atorvastatin" in statin_group["members"]
        assert "med:rosuvastatin" in statin_group["members"]

    def test_grouped_has_guideline_count(self):
        """Each grouped convergence entry should track guideline count."""
        subgraph = serialize_subgraph(MULTI_GUIDELINE_TRACE)
        conv = serialize_convergence_summary(MULTI_GUIDELINE_TRACE, subgraph)
        grouped = conv["grouped_convergence"]

        for group in grouped:
            assert group["guideline_count"] >= 2
            assert len(group["recommended_by"]) == group["guideline_count"]

    def test_grouped_has_intensity_details(self):
        """Each group should have intensity_details with strategy names."""
        subgraph = serialize_subgraph(MULTI_GUIDELINE_TRACE)
        conv = serialize_convergence_summary(MULTI_GUIDELINE_TRACE, subgraph)
        grouped = conv["grouped_convergence"]

        for group in grouped:
            assert "intensity_details" in group
            for detail in group["intensity_details"]:
                assert "strategy_id" in detail
                assert "strategy_name" in detail
                assert "guideline" in detail

    def test_prose_mentions_therapeutic_class(self):
        """v2 convergence prose should reference the therapeutic class, not individual meds."""
        subgraph = serialize_subgraph(MULTI_GUIDELINE_TRACE)
        conv = serialize_convergence_summary(MULTI_GUIDELINE_TRACE, subgraph)
        prose = conv["convergence_prose"]

        assert "statin therapy" in prose.lower()
        # Should list members with "Any of:"
        assert "Any of:" in prose

    def test_empty_trace_no_grouped_convergence(self):
        """Empty trace should produce empty grouped_convergence."""
        empty_trace = {"events": []}
        subgraph = serialize_subgraph(empty_trace)
        conv = serialize_convergence_summary(empty_trace, subgraph)
        assert conv["grouped_convergence"] == []

    def test_fewer_rows_than_shared_actions(self):
        """Grouped output should have fewer entries than raw shared_actions."""
        subgraph = serialize_subgraph(MULTI_GUIDELINE_TRACE)
        conv = serialize_convergence_summary(MULTI_GUIDELINE_TRACE, subgraph)

        # 2 shared actions (atorvastatin, rosuvastatin) should group into 1 class
        assert len(conv["shared_actions"]) == 2
        assert len(conv["grouped_convergence"]) == 1


class TestPreemptionModifierProse:
    """Tests for v2 preemption/modifier prose rendering."""

    def test_preemption_prose_rendered(self):
        """Preemption events should produce prose, not raw JSON."""
        trace = {
            "events": [
                {
                    "seq": 1,
                    "type": "preemption_resolved",
                    "guideline_id": "guideline:uspstf-statin-2022",
                    "preempted_recommendation_id": "rec:statin-initiate-grade-b",
                    "preempting_recommendation_id": "rec:accaha-statin-primary-prevention",
                    "edge_priority": 200,
                    "reason": "ACC/AHA more specific",
                },
                {
                    "seq": 2,
                    "type": "recommendation_emitted",
                    "guideline_id": "guideline:acc-aha-cholesterol-2018",
                    "recommendation_id": "rec:accaha-statin-primary-prevention",
                    "status": "due",
                    "evidence_grade": "COR I, LOE A",
                    "reason": "Patient eligible",
                    "offered_strategies": [],
                },
            ]
        }
        summary = serialize_trace_summary(trace)
        assert summary["preemption_prose"] != ""
        assert "preempts" in summary["preemption_prose"]
        # Should contain guideline labels, not raw rec IDs
        assert "ACC/AHA 2018 Cholesterol" in summary["preemption_prose"]

    def test_modifier_prose_rendered(self):
        """Modifier events should produce prose, not raw JSON."""
        trace = {
            "events": [
                {
                    "seq": 1,
                    "type": "cross_guideline_match",
                    "guideline_id": "guideline:kdigo-ckd-2024",
                    "source_guideline_id": "guideline:kdigo-ckd-2024",
                    "target_guideline_id": "guideline:acc-aha-cholesterol-2018",
                    "nature": "intensity_reduction",
                    "note": "KDIGO recommends moderate-intensity for eGFR < 30",
                },
            ]
        }
        summary = serialize_trace_summary(trace)
        assert summary["modifier_prose"] != ""
        assert "modifies" in summary["modifier_prose"]
        assert "KDIGO 2024 CKD" in summary["modifier_prose"]
        assert "intensity reduction" in summary["modifier_prose"]

    def test_empty_events_no_prose(self):
        """No preemption/modifier events should produce empty prose strings."""
        summary = serialize_trace_summary(SAMPLE_TRACE)
        assert summary["preemption_prose"] == ""
        assert summary["modifier_prose"] == ""

    def test_modifier_note_included(self):
        """Modifier prose should include the note when present."""
        trace = {
            "events": [
                {
                    "seq": 1,
                    "type": "cross_guideline_match",
                    "guideline_id": "guideline:kdigo-ckd-2024",
                    "source_guideline_id": "guideline:kdigo-ckd-2024",
                    "target_guideline_id": "guideline:acc-aha-cholesterol-2018",
                    "nature": "intensity_reduction",
                    "note": "consider dose reduction for eGFR < 30",
                },
            ]
        }
        summary = serialize_trace_summary(trace)
        assert "dose reduction" in summary["modifier_prose"]

    def test_preemption_prose_keys_in_summary(self):
        """serialize_trace_summary should always include prose keys."""
        summary = serialize_trace_summary({"events": []})
        assert "preemption_prose" in summary
        assert "modifier_prose" in summary


# --- Satisfied strategies trace for continue-action tests ---

SATISFIED_STRATEGY_TRACE = {
    "envelope": {"spec_tag": "test", "graph_version": "test", "evaluator_version": "test"},
    "events": [
        {"seq": 1, "type": "evaluation_started", "guideline_id": None},
        {
            "seq": 2,
            "type": "guideline_entered",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "guideline_title": "KDIGO 2024 CKD",
        },
        {
            "seq": 3,
            "type": "recommendation_considered",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "recommendation_id": "rec:kdigo-acei-arb-for-ckd",
            "recommendation_title": "ACEi/ARB for CKD",
            "evidence_grade": "1B",
            "intent": "treatment",
            "trigger": "patient_state",
        },
        {
            "seq": 4,
            "type": "strategy_considered",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "recommendation_id": "rec:kdigo-acei-arb-for-ckd",
            "strategy_id": "strategy:kdigo-acei-arb",
            "strategy_name": "ACEi or ARB therapy",
        },
        {
            "seq": 5,
            "type": "action_checked",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "recommendation_id": "rec:kdigo-acei-arb-for-ckd",
            "strategy_id": "strategy:kdigo-acei-arb",
            "action_node_id": "med:losartan",
            "action_entity_type": "Medication",
            "satisfied": True,
        },
        {
            "seq": 6,
            "type": "strategy_resolved",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "recommendation_id": "rec:kdigo-acei-arb-for-ckd",
            "strategy_id": "strategy:kdigo-acei-arb",
            "satisfied": True,
        },
        {
            "seq": 7,
            "type": "recommendation_emitted",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "recommendation_id": "rec:kdigo-acei-arb-for-ckd",
            "status": "up_to_date",
            "evidence_grade": "1B",
            "reason": "Patient already on losartan (ARB)",
            "satisfying_strategy": "strategy:kdigo-acei-arb",
        },
        # A "due" rec — should NOT appear in satisfied strategies
        {
            "seq": 8,
            "type": "recommendation_considered",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "recommendation_id": "rec:kdigo-statin-for-ckd",
            "recommendation_title": "Statin for CKD",
            "evidence_grade": "1A",
            "intent": "treatment",
            "trigger": "patient_state",
        },
        {
            "seq": 9,
            "type": "strategy_considered",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "recommendation_id": "rec:kdigo-statin-for-ckd",
            "strategy_id": "strategy:kdigo-statin",
            "strategy_name": "Statin therapy for CKD",
        },
        {
            "seq": 10,
            "type": "action_checked",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "recommendation_id": "rec:kdigo-statin-for-ckd",
            "strategy_id": "strategy:kdigo-statin",
            "action_node_id": "med:atorvastatin",
            "action_entity_type": "Medication",
            "satisfied": False,
        },
        {
            "seq": 11,
            "type": "recommendation_emitted",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "recommendation_id": "rec:kdigo-statin-for-ckd",
            "status": "due",
            "evidence_grade": "1A",
            "reason": "No statin on med list",
            "offered_strategies": ["strategy:kdigo-statin"],
        },
        {"seq": 12, "type": "evaluation_completed", "guideline_id": None},
    ],
}


class TestSerializeSatisfiedStrategies:
    """Tests for serialize_satisfied_strategies (F49)."""

    def test_extracts_up_to_date_recs(self):
        """Only up_to_date recs should appear in satisfied strategies."""
        satisfied = serialize_satisfied_strategies(SATISFIED_STRATEGY_TRACE)
        assert len(satisfied) == 1
        assert satisfied[0]["recommendation_id"] == "rec:kdigo-acei-arb-for-ckd"

    def test_includes_strategy_details(self):
        satisfied = serialize_satisfied_strategies(SATISFIED_STRATEGY_TRACE)
        s = satisfied[0]
        assert s["strategy_id"] == "strategy:kdigo-acei-arb"
        assert s["strategy_name"] == "ACEi or ARB therapy"
        assert s["evidence_grade"] == "1B"

    def test_includes_satisfied_actions(self):
        """Should list the specific actions that satisfied the strategy."""
        satisfied = serialize_satisfied_strategies(SATISFIED_STRATEGY_TRACE)
        assert "med:losartan" in satisfied[0]["satisfied_by"]

    def test_includes_guideline_label(self):
        satisfied = serialize_satisfied_strategies(SATISFIED_STRATEGY_TRACE)
        assert satisfied[0]["guideline_label"] == "KDIGO 2024 CKD"

    def test_due_recs_excluded(self):
        """Recs with status 'due' should not appear."""
        satisfied = serialize_satisfied_strategies(SATISFIED_STRATEGY_TRACE)
        rec_ids = {s["recommendation_id"] for s in satisfied}
        assert "rec:kdigo-statin-for-ckd" not in rec_ids

    def test_empty_trace(self):
        satisfied = serialize_satisfied_strategies({"events": []})
        assert satisfied == []

    def test_build_arm_c_context_includes_satisfied_strategies(self):
        """build_arm_c_context should include the satisfied_strategies key."""
        ctx = build_arm_c_context(SATISFIED_STRATEGY_TRACE)
        assert "satisfied_strategies" in ctx
        assert len(ctx["satisfied_strategies"]) == 1


class TestBuildSatisfiedStrategiesSection:
    """Tests for _build_satisfied_strategies_section rendering (F49)."""

    def test_renders_section_header(self):
        satisfied = [{
            "guideline_label": "KDIGO 2024 CKD",
            "evidence_grade": "1B",
            "strategy_name": "ACEi or ARB therapy",
            "satisfied_by": ["med:losartan"],
        }]
        text = _build_satisfied_strategies_section(satisfied)
        assert "### Currently Satisfied Strategies" in text

    def test_renders_strategy_name_and_guideline(self):
        satisfied = [{
            "guideline_label": "KDIGO 2024 CKD",
            "evidence_grade": "1B",
            "strategy_name": "ACEi or ARB therapy",
            "satisfied_by": ["med:losartan"],
        }]
        text = _build_satisfied_strategies_section(satisfied)
        assert "ACEi or ARB therapy" in text
        assert "KDIGO 2024 CKD" in text
        assert "med:losartan" in text

    def test_empty_list_returns_empty_string(self):
        assert _build_satisfied_strategies_section([]) == ""

    def test_multiple_strategies(self):
        satisfied = [
            {"guideline_label": "G1", "evidence_grade": "A", "strategy_name": "S1", "satisfied_by": ["med:a"]},
            {"guideline_label": "G2", "evidence_grade": "B", "strategy_name": "S2", "satisfied_by": ["med:b"]},
        ]
        text = _build_satisfied_strategies_section(satisfied)
        assert "S1" in text
        assert "S2" in text


class TestBuildInteractionsSection:
    """Tests for _build_interactions_section rendering (F49)."""

    def test_directive_language_present(self):
        summary = {
            "preemption_prose": "ACC/AHA preempts USPSTF",
            "modifier_prose": "",
        }
        text = _build_interactions_section(summary)
        assert "IMPORTANT" in text
        assert "explicitly state" in text.lower()

    def test_preemption_with_follow_up_instruction(self):
        summary = {"preemption_prose": "ACC/AHA preempts USPSTF", "modifier_prose": ""}
        text = _build_interactions_section(summary)
        assert "preempted and preempting guidelines" in text

    def test_modifier_with_follow_up_instruction(self):
        summary = {"preemption_prose": "", "modifier_prose": "KDIGO modifies ACC/AHA"}
        text = _build_interactions_section(summary)
        assert "explain this modification" in text

    def test_empty_events_returns_empty(self):
        summary = {"preemption_prose": "", "modifier_prose": ""}
        assert _build_interactions_section(summary) == ""

    def test_both_preemption_and_modifier(self):
        summary = {
            "preemption_prose": "ACC/AHA preempts USPSTF",
            "modifier_prose": "KDIGO modifies ACC/AHA",
        }
        text = _build_interactions_section(summary)
        assert "Preemption" in text
        assert "Modifier" in text


# --- Negative evidence traces ---

NEGATIVE_EVIDENCE_TRACE_ZERO_RECS = {
    "events": [
        {"seq": 1, "type": "evaluation_started", "guideline_id": None},
        {
            "seq": 2,
            "type": "guideline_entered",
            "guideline_id": "guideline:uspstf-statin-2022",
            "guideline_title": "USPSTF 2022 Statin Primary Prevention",
        },
        {
            "seq": 3,
            "type": "exit_condition_triggered",
            "guideline_id": "guideline:uspstf-statin-2022",
            "recommendation_id": "rec:statin-initiate-grade-b",
            "exit": "out_of_scope_age_below_range",
            "rationale": "Patient age 35 below minimum 40",
        },
        {
            "seq": 4,
            "type": "guideline_exited",
            "guideline_id": "guideline:uspstf-statin-2022",
            "recommendations_emitted": 0,
        },
        # ACC/AHA fires normally
        {
            "seq": 5,
            "type": "guideline_entered",
            "guideline_id": "guideline:acc-aha-cholesterol-2018",
            "guideline_title": "ACC/AHA 2018 Cholesterol",
        },
        {
            "seq": 6,
            "type": "recommendation_emitted",
            "guideline_id": "guideline:acc-aha-cholesterol-2018",
            "recommendation_id": "rec:accaha-statin-primary-prevention",
            "status": "due",
            "evidence_grade": "COR I, LOE A",
            "reason": "Patient eligible",
            "offered_strategies": [],
        },
        {
            "seq": 7,
            "type": "guideline_exited",
            "guideline_id": "guideline:acc-aha-cholesterol-2018",
            "recommendations_emitted": 1,
        },
        {"seq": 8, "type": "evaluation_completed", "guideline_id": None},
    ],
}

NEGATIVE_EVIDENCE_TRACE_ALL_PREEMPTED = {
    "events": [
        {"seq": 1, "type": "evaluation_started", "guideline_id": None},
        {
            "seq": 2,
            "type": "guideline_entered",
            "guideline_id": "guideline:uspstf-statin-2022",
            "guideline_title": "USPSTF 2022 Statin Primary Prevention",
        },
        {
            "seq": 3,
            "type": "recommendation_emitted",
            "guideline_id": "guideline:uspstf-statin-2022",
            "recommendation_id": "rec:statin-initiate-grade-b",
            "status": "due",
            "evidence_grade": "B",
            "reason": "Patient eligible",
            "offered_strategies": [],
        },
        {
            "seq": 4,
            "type": "guideline_exited",
            "guideline_id": "guideline:uspstf-statin-2022",
            "recommendations_emitted": 1,
        },
        {
            "seq": 5,
            "type": "guideline_entered",
            "guideline_id": "guideline:acc-aha-cholesterol-2018",
            "guideline_title": "ACC/AHA 2018 Cholesterol",
        },
        {
            "seq": 6,
            "type": "recommendation_emitted",
            "guideline_id": "guideline:acc-aha-cholesterol-2018",
            "recommendation_id": "rec:accaha-statin-primary-prevention",
            "status": "due",
            "evidence_grade": "COR I, LOE A",
            "reason": "Patient eligible",
            "offered_strategies": [],
        },
        {
            "seq": 7,
            "type": "guideline_exited",
            "guideline_id": "guideline:acc-aha-cholesterol-2018",
            "recommendations_emitted": 1,
        },
        # USPSTF rec preempted by ACC/AHA
        {
            "seq": 8,
            "type": "preemption_resolved",
            "guideline_id": None,
            "preempted_recommendation_id": "rec:statin-initiate-grade-b",
            "preempting_recommendation_id": "rec:accaha-statin-primary-prevention",
            "edge_priority": 200,
            "reason": "ACC/AHA more specific",
        },
        {"seq": 9, "type": "evaluation_completed", "guideline_id": None},
    ],
}


class TestSerializeNegativeEvidence:
    """Tests for serialize_negative_evidence (F50)."""

    def test_guideline_entered_zero_recs(self):
        """A guideline that entered but emitted zero recs → one entry."""
        result = serialize_negative_evidence(NEGATIVE_EVIDENCE_TRACE_ZERO_RECS)
        assert len(result) == 1
        assert result[0]["guideline_id"] == "guideline:uspstf-statin-2022"
        assert result[0]["guideline_label"] == "USPSTF 2022 Statin"
        assert "out_of_scope_age_below_range" in result[0]["reason"]

    def test_all_recs_preempted(self):
        """A guideline whose recs were all preempted → one entry."""
        result = serialize_negative_evidence(NEGATIVE_EVIDENCE_TRACE_ALL_PREEMPTED)
        assert len(result) == 1
        assert result[0]["guideline_id"] == "guideline:uspstf-statin-2022"
        assert "preempted" in result[0]["reason"].lower()
        assert "ACC/AHA 2018 Cholesterol" in result[0]["reason"]

    def test_all_guidelines_produced_recs(self):
        """When all guidelines produce non-preempted recs → empty list."""
        result = serialize_negative_evidence(MULTI_GUIDELINE_TRACE)
        assert result == []

    def test_single_guideline_trace(self):
        """Single-guideline trace where USPSTF fires → empty list."""
        result = serialize_negative_evidence(SAMPLE_TRACE)
        assert result == []

    def test_empty_trace(self):
        result = serialize_negative_evidence({"events": []})
        assert result == []

    def test_guideline_entered_no_exits_no_recs(self):
        """Guideline entered with no exits and no recs → 'No eligible recommendations'."""
        trace = {
            "events": [
                {
                    "seq": 1,
                    "type": "guideline_entered",
                    "guideline_id": "guideline:test",
                    "guideline_title": "Test Guideline",
                },
                {
                    "seq": 2,
                    "type": "guideline_exited",
                    "guideline_id": "guideline:test",
                    "recommendations_emitted": 0,
                },
            ],
        }
        result = serialize_negative_evidence(trace)
        assert len(result) == 1
        assert result[0]["reason"] == "No eligible recommendations"

    def test_build_arm_c_context_includes_negative_evidence(self):
        """build_arm_c_context should include the negative_evidence key."""
        ctx = build_arm_c_context(NEGATIVE_EVIDENCE_TRACE_ZERO_RECS)
        assert "negative_evidence" in ctx
        assert len(ctx["negative_evidence"]) == 1


class TestBuildNegativeEvidenceSection:
    """Tests for _build_negative_evidence_section rendering (F50)."""

    def test_renders_section_when_present(self):
        ne = [{"guideline_label": "USPSTF 2022 Statin", "reason": "ASCVD 6.8% below threshold"}]
        text = _build_negative_evidence_section(ne)
        assert "### Guidelines Evaluated Without Recommendations" in text
        assert "USPSTF 2022 Statin" in text
        assert "ASCVD 6.8% below threshold" in text
        assert "clinically significant" in text

    def test_empty_returns_empty_string(self):
        assert _build_negative_evidence_section([]) == ""


class TestBuildOutputFormatInstruction:
    """Tests for _build_output_format_instruction (F50)."""

    def test_no_interactions_no_negative(self):
        """Without interactions or negative evidence, use simple format."""
        text = _build_output_format_instruction(False, False)
        assert "Respond with a JSON object containing your recommended actions" in text
        assert "cross_guideline_resolutions" not in text

    def test_with_interactions(self):
        text = _build_output_format_instruction(True, False)
        assert "cross_guideline_resolutions" in text
        assert "guidelines_without_recommendations" not in text

    def test_with_negative_evidence(self):
        text = _build_output_format_instruction(False, True)
        assert "guidelines_without_recommendations" in text
        assert "cross_guideline_resolutions" not in text

    def test_with_both(self):
        text = _build_output_format_instruction(True, True)
        assert "cross_guideline_resolutions" in text
        assert "guidelines_without_recommendations" in text


class TestPromptIntegration:
    """Integration tests verifying the full prompt renders correctly (F50)."""

    def test_multi_guideline_with_negative_evidence(self):
        """Negative evidence section renders in multi-guideline trace."""
        ctx = build_arm_c_context(NEGATIVE_EVIDENCE_TRACE_ZERO_RECS)
        prompt = get_prompt({"demographics": {"age": 35}}, ctx)
        assert "Guidelines Evaluated Without Recommendations" in prompt
        assert "USPSTF 2022 Statin" in prompt
        assert "guidelines_without_recommendations" in prompt

    def test_single_guideline_no_negative_section(self):
        """Single-guideline trace should NOT have negative evidence section."""
        ctx = build_arm_c_context(SAMPLE_TRACE)
        prompt = get_prompt({"demographics": {"age": 55}}, ctx)
        assert "Guidelines Evaluated Without Recommendations" not in prompt
        assert "cross_guideline_resolutions" not in prompt

    def test_completeness_licensing_present(self):
        """Completeness licensing paragraph present in all prompts."""
        ctx = build_arm_c_context(SAMPLE_TRACE)
        prompt = get_prompt({"demographics": {"age": 55}}, ctx)
        assert "lifestyle modifications" in prompt.lower()
        assert "smoking cessation" in prompt.lower()
        assert "Do not limit your recommendations to only what the graph covers" in prompt

    def test_preemption_triggers_extended_schema(self):
        """Trace with preemption events should request cross_guideline_resolutions."""
        ctx = build_arm_c_context(NEGATIVE_EVIDENCE_TRACE_ALL_PREEMPTED)
        prompt = get_prompt({"demographics": {"age": 55}}, ctx)
        assert "cross_guideline_resolutions" in prompt

    def test_satisfied_strategies_still_renders(self):
        """F49 satisfied strategies section should still render."""
        ctx = build_arm_c_context(SATISFIED_STRATEGY_TRACE)
        prompt = get_prompt({"demographics": {"age": 60}}, ctx)
        assert "Currently Satisfied Strategies" in prompt


# --- F57: Serialization scoping tests ---

# 4-guideline trace where USPSTF and ACC/AHA are relevant (emit recs),
# KDIGO has an exit condition (relevant), and ADA is irrelevant
# (entered, all recs not_applicable, no exit, no cross-match).
FOUR_GUIDELINE_SCOPING_TRACE = {
    "envelope": {"spec_tag": "test", "graph_version": "test", "evaluator_version": "test"},
    "events": [
        {"seq": 1, "type": "evaluation_started", "guideline_id": None},
        # USPSTF — relevant (rec emitted with status=due)
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
            "type": "recommendation_emitted",
            "guideline_id": "guideline:uspstf-statin-2022",
            "recommendation_id": "rec:statin-initiate-grade-b",
            "status": "due",
            "evidence_grade": "B",
            "reason": "Patient eligible",
            "offered_strategies": [],
        },
        {
            "seq": 5,
            "type": "guideline_exited",
            "guideline_id": "guideline:uspstf-statin-2022",
            "recommendations_emitted": 1,
        },
        # ACC/AHA — relevant (rec emitted with status=up_to_date)
        {
            "seq": 6,
            "type": "guideline_entered",
            "guideline_id": "guideline:acc-aha-cholesterol-2018",
            "guideline_title": "ACC/AHA 2018 Cholesterol",
        },
        {
            "seq": 7,
            "type": "recommendation_emitted",
            "guideline_id": "guideline:acc-aha-cholesterol-2018",
            "recommendation_id": "rec:accaha-statin-primary-prevention",
            "status": "up_to_date",
            "evidence_grade": "COR I, LOE A",
            "reason": "Already on statin",
            "satisfying_strategy": "strategy:accaha-moderate-intensity",
            "offered_strategies": [],
        },
        {
            "seq": 8,
            "type": "guideline_exited",
            "guideline_id": "guideline:acc-aha-cholesterol-2018",
            "recommendations_emitted": 1,
        },
        # KDIGO — relevant (exit condition triggered)
        {
            "seq": 9,
            "type": "guideline_entered",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "guideline_title": "KDIGO 2024 CKD",
        },
        {
            "seq": 10,
            "type": "exit_condition_triggered",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "recommendation_id": "rec:kdigo-statin-for-ckd",
            "exit": "no_ckd_diagnosis",
            "rationale": "Patient does not have CKD",
        },
        {
            "seq": 11,
            "type": "guideline_exited",
            "guideline_id": "guideline:kdigo-ckd-2024",
            "recommendations_emitted": 0,
        },
        # ADA — irrelevant (entered, rec not_applicable, no exit, no cross-match)
        {
            "seq": 12,
            "type": "guideline_entered",
            "guideline_id": "guideline:ada-diabetes-2024",
            "guideline_title": "ADA 2024 Diabetes",
        },
        {
            "seq": 13,
            "type": "recommendation_considered",
            "guideline_id": "guideline:ada-diabetes-2024",
            "recommendation_id": "rec:ada-statin-diabetes",
            "recommendation_title": "Statin for diabetes",
            "evidence_grade": "A",
            "intent": "treatment",
            "trigger": "patient_state",
        },
        {
            "seq": 14,
            "type": "recommendation_emitted",
            "guideline_id": "guideline:ada-diabetes-2024",
            "recommendation_id": "rec:ada-statin-diabetes",
            "status": "not_applicable",
            "evidence_grade": "A",
            "reason": "Patient does not have diabetes",
            "offered_strategies": [],
        },
        {
            "seq": 15,
            "type": "guideline_exited",
            "guideline_id": "guideline:ada-diabetes-2024",
            "recommendations_emitted": 1,
        },
        {"seq": 16, "type": "evaluation_completed", "guideline_id": None},
    ],
}


class TestClassifyGuidelineRelevance:
    """Tests for classify_guideline_relevance (F57)."""

    def test_four_guidelines_two_irrelevant(self):
        """ADA is irrelevant (all recs not_applicable). Others are relevant."""
        result = classify_guideline_relevance(FOUR_GUIDELINE_SCOPING_TRACE)
        assert "guideline:uspstf-statin-2022" in result["relevant"]
        assert "guideline:acc-aha-cholesterol-2018" in result["relevant"]
        assert "guideline:kdigo-ckd-2024" in result["relevant"]
        assert "guideline:ada-diabetes-2024" in result["irrelevant"]

    def test_exit_condition_is_relevant(self):
        """A guideline with exit_condition_triggered but no rec emitted is relevant."""
        trace = {
            "events": [
                {
                    "seq": 1,
                    "type": "guideline_entered",
                    "guideline_id": "guideline:kdigo-ckd-2024",
                    "guideline_title": "KDIGO 2024 CKD",
                },
                {
                    "seq": 2,
                    "type": "exit_condition_triggered",
                    "guideline_id": "guideline:kdigo-ckd-2024",
                    "recommendation_id": "rec:kdigo-statin-for-ckd",
                    "exit": "no_ckd_diagnosis",
                    "rationale": "Patient does not have CKD",
                },
            ]
        }
        result = classify_guideline_relevance(trace)
        assert "guideline:kdigo-ckd-2024" in result["relevant"]
        assert "guideline:kdigo-ckd-2024" not in result["irrelevant"]

    def test_cross_guideline_match_keeps_both_relevant(self):
        """A guideline in a cross_guideline_match is never filtered out."""
        trace = {
            "events": [
                {
                    "seq": 1,
                    "type": "guideline_entered",
                    "guideline_id": "guideline:ada-diabetes-2024",
                    "guideline_title": "ADA 2024 Diabetes",
                },
                # ADA has no recs emitted (would be irrelevant)
                # But it appears in a cross_guideline_match
                {
                    "seq": 2,
                    "type": "cross_guideline_match",
                    "guideline_id": "guideline:ada-diabetes-2024",
                    "source_guideline_id": "guideline:ada-diabetes-2024",
                    "target_guideline_id": "guideline:acc-aha-cholesterol-2018",
                    "nature": "reinforcing",
                    "note": "Both recommend statins",
                },
            ]
        }
        result = classify_guideline_relevance(trace)
        assert "guideline:ada-diabetes-2024" in result["relevant"]
        assert "guideline:acc-aha-cholesterol-2018" in result["relevant"]

    def test_not_applicable_only_is_irrelevant(self):
        """A guideline with only not_applicable recs is irrelevant."""
        trace = {
            "events": [
                {
                    "seq": 1,
                    "type": "guideline_entered",
                    "guideline_id": "guideline:ada-diabetes-2024",
                    "guideline_title": "ADA 2024 Diabetes",
                },
                {
                    "seq": 2,
                    "type": "recommendation_emitted",
                    "guideline_id": "guideline:ada-diabetes-2024",
                    "recommendation_id": "rec:ada-statin-diabetes",
                    "status": "not_applicable",
                    "evidence_grade": "A",
                    "reason": "No diabetes",
                    "offered_strategies": [],
                },
            ]
        }
        result = classify_guideline_relevance(trace)
        assert "guideline:ada-diabetes-2024" in result["irrelevant"]

    def test_empty_trace(self):
        result = classify_guideline_relevance({"events": []})
        assert result["relevant"] == set()
        assert result["irrelevant"] == set()

    def test_all_relevant_no_irrelevant(self):
        """When all guidelines fire, irrelevant set is empty."""
        result = classify_guideline_relevance(MULTI_GUIDELINE_TRACE)
        assert len(result["irrelevant"]) == 0


class TestFilterTraceByRelevance:
    """Tests for _filter_trace_by_relevance (F57)."""

    def test_cross_guideline_event_preserved_for_irrelevant_guideline(self):
        """A preemption_resolved event referencing an irrelevant guideline
        should still pass through the filter (always_keep behavior)."""
        trace = {
            "events": [
                {"seq": 1, "type": "evaluation_started", "guideline_id": None},
                {
                    "seq": 2,
                    "type": "guideline_entered",
                    "guideline_id": "guideline:ada-diabetes-2024",
                    "guideline_title": "ADA 2024 Diabetes",
                },
                # ADA rec (would be filtered)
                {
                    "seq": 3,
                    "type": "recommendation_emitted",
                    "guideline_id": "guideline:ada-diabetes-2024",
                    "recommendation_id": "rec:ada-statin-diabetes",
                    "status": "not_applicable",
                    "evidence_grade": "A",
                    "reason": "No diabetes",
                    "offered_strategies": [],
                },
                # Preemption event with ADA's guideline_id — must be preserved
                {
                    "seq": 4,
                    "type": "preemption_resolved",
                    "guideline_id": "guideline:ada-diabetes-2024",
                    "preempted_recommendation_id": "rec:ada-statin-diabetes",
                    "preempting_recommendation_id": "rec:accaha-statin-primary-prevention",
                    "edge_priority": 200,
                    "reason": "ACC/AHA more specific",
                },
                {"seq": 5, "type": "evaluation_completed", "guideline_id": None},
            ]
        }
        irrelevant = {"guideline:ada-diabetes-2024"}
        filtered = _filter_trace_by_relevance(trace, irrelevant)

        event_types = [e["type"] for e in filtered["events"]]
        # preemption_resolved should be preserved
        assert "preemption_resolved" in event_types
        # recommendation_emitted from ADA should be filtered
        assert "recommendation_emitted" not in event_types
        # bookend events preserved
        assert "evaluation_started" in event_types
        assert "evaluation_completed" in event_types

    def test_cross_guideline_match_preserved_for_irrelevant_guideline(self):
        """A cross_guideline_match event should be preserved even if its
        guideline_id is in the irrelevant set."""
        trace = {
            "events": [
                {"seq": 1, "type": "evaluation_started", "guideline_id": None},
                {
                    "seq": 2,
                    "type": "cross_guideline_match",
                    "guideline_id": "guideline:ada-diabetes-2024",
                    "source_guideline_id": "guideline:ada-diabetes-2024",
                    "target_guideline_id": "guideline:acc-aha-cholesterol-2018",
                    "nature": "reinforcing",
                    "note": "test",
                },
                {"seq": 3, "type": "evaluation_completed", "guideline_id": None},
            ]
        }
        irrelevant = {"guideline:ada-diabetes-2024"}
        filtered = _filter_trace_by_relevance(trace, irrelevant)
        event_types = [e["type"] for e in filtered["events"]]
        assert "cross_guideline_match" in event_types

    def test_empty_irrelevant_returns_unchanged(self):
        """No irrelevant guidelines → trace returned unchanged."""
        trace = {"events": [{"seq": 1, "type": "evaluation_started", "guideline_id": None}]}
        filtered = _filter_trace_by_relevance(trace, set())
        assert filtered is trace  # Same object, not a copy

    def test_guideline_entered_filtered_for_irrelevant(self):
        """guideline_entered event should be dropped for irrelevant guidelines."""
        trace = {
            "events": [
                {"seq": 1, "type": "evaluation_started", "guideline_id": None},
                {
                    "seq": 2,
                    "type": "guideline_entered",
                    "guideline_id": "guideline:ada-diabetes-2024",
                    "guideline_title": "ADA 2024 Diabetes",
                },
                {"seq": 3, "type": "evaluation_completed", "guideline_id": None},
            ]
        }
        irrelevant = {"guideline:ada-diabetes-2024"}
        filtered = _filter_trace_by_relevance(trace, irrelevant)
        event_types = [e["type"] for e in filtered["events"]]
        assert "guideline_entered" not in event_types


class TestSerializationScoping:
    """Tests for build_arm_c_context with scoping (F57)."""

    def test_irrelevant_guideline_filtered_from_context(self):
        """build_arm_c_context should exclude ADA from serialized context
        when ADA is irrelevant (all recs not_applicable)."""
        ctx = build_arm_c_context(FOUR_GUIDELINE_SCOPING_TRACE)

        # ADA should NOT appear in rendered prose
        prose = ctx["subgraph"]["rendered_prose"]
        assert "ADA 2024" not in prose

        # ADA recs should not be in matched_recs
        rec_guidelines = {
            r.get("guideline_id") for r in ctx["trace_summary"]["matched_recs"]
        }
        assert "guideline:ada-diabetes-2024" not in rec_guidelines

        # ADA should not appear in negative evidence
        neg_guidelines = {
            n["guideline_id"] for n in ctx["negative_evidence"]
        }
        assert "guideline:ada-diabetes-2024" not in neg_guidelines

    def test_relevant_guidelines_preserved(self):
        """USPSTF, ACC/AHA, and KDIGO should all still appear in context."""
        ctx = build_arm_c_context(FOUR_GUIDELINE_SCOPING_TRACE)
        prose = ctx["subgraph"]["rendered_prose"]

        assert "USPSTF 2022" in prose
        # KDIGO exit should appear
        assert "no_ckd_diagnosis" in prose

    def test_context_mentions_only_relevant_guidelines(self):
        """The full prompt should only reference relevant guidelines."""
        ctx = build_arm_c_context(FOUR_GUIDELINE_SCOPING_TRACE)
        prompt = get_prompt({"demographics": {"age": 55}}, ctx)

        assert "USPSTF" in prompt
        # ADA content should be absent from the prompt
        assert "ADA 2024 Diabetes" not in prompt

    def test_no_filtering_when_all_relevant(self):
        """When all guidelines are relevant, context is unchanged."""
        ctx_unscoped = build_arm_c_context(MULTI_GUIDELINE_TRACE)
        # All 3 guidelines fire recs, so none should be filtered
        rec_count = len(ctx_unscoped["trace_summary"]["matched_recs"])
        assert rec_count == 4  # 1 USPSTF + 1 ACC/AHA + 2 KDIGO

    def test_deterministic(self):
        """Same trace = same scoped context."""
        ctx1 = build_arm_c_context(FOUR_GUIDELINE_SCOPING_TRACE)
        ctx2 = build_arm_c_context(FOUR_GUIDELINE_SCOPING_TRACE)
        assert ctx1 == ctx2
