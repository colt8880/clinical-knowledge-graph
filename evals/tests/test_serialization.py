"""Unit tests for Arm C serialization."""

import pytest

from harness.serialization import (
    build_arm_c_context,
    serialize_convergence_summary,
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
