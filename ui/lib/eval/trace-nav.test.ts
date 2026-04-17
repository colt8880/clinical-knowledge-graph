import { describe, it, expect } from "vitest";
import {
  highlightedNodeIds,
  eventSummary,
  eventTypeLabel,
  clampIndex,
  deriveRecommendations,
  subgraphFetchIds,
  visibleNodeIds,
} from "./trace-nav";
import type { EvalTrace, TraceEvent } from "./trace-nav";

describe("highlightedNodeIds", () => {
  it("returns empty for evaluation_started", () => {
    const event = {
      seq: 1,
      type: "evaluation_started" as const,
      patient_age_years: 55,
      patient_sex: "male",
      guidelines_in_scope: ["guideline:uspstf-statin-2022"],
    } as unknown as TraceEvent;
    expect(highlightedNodeIds(event)).toEqual([]);
  });

  it("returns guideline_id for guideline_entered", () => {
    const event = {
      seq: 2,
      type: "guideline_entered" as const,
      guideline_id: "guideline:uspstf-statin-2022",
      guideline_title: "USPSTF Statin 2022",
    } as unknown as TraceEvent;
    expect(highlightedNodeIds(event)).toEqual(["guideline:uspstf-statin-2022"]);
  });

  it("returns recommendation_id for recommendation_considered", () => {
    const event = {
      seq: 3,
      type: "recommendation_considered" as const,
      recommendation_id: "rec:statin-initiate-grade-b",
      recommendation_title: "Grade B",
      evidence_grade: "B",
      intent: "initiate",
      trigger: "primary_prevention",
    } as unknown as TraceEvent;
    expect(highlightedNodeIds(event)).toEqual(["rec:statin-initiate-grade-b"]);
  });

  it("returns action_node_id for action_checked", () => {
    const event = {
      seq: 10,
      type: "action_checked" as const,
      recommendation_id: "rec:statin-initiate-grade-b",
      strategy_id: "strategy:statin-moderate-intensity",
      action_node_id: "med:atorvastatin",
      action_entity_type: "Medication" as const,
      inputs_read: [],
      satisfied: false,
    } as unknown as TraceEvent;
    expect(highlightedNodeIds(event)).toEqual(["med:atorvastatin"]);
  });

  it("returns strategy_id for strategy_considered", () => {
    const event = {
      seq: 8,
      type: "strategy_considered" as const,
      recommendation_id: "rec:statin-initiate-grade-b",
      strategy_id: "strategy:statin-moderate-intensity",
      strategy_name: "Moderate Intensity Statin",
    } as unknown as TraceEvent;
    expect(highlightedNodeIds(event)).toEqual([
      "strategy:statin-moderate-intensity",
    ]);
  });

  it("returns recommendation_id for exit_condition_triggered", () => {
    const event = {
      seq: 5,
      type: "exit_condition_triggered" as const,
      recommendation_id: "rec:statin-initiate-grade-b",
      exit: "out_of_scope_age_below_range",
      rationale: "Patient is 35, below minimum age 40",
    } as unknown as TraceEvent;
    expect(highlightedNodeIds(event)).toEqual(["rec:statin-initiate-grade-b"]);
  });

  it("returns empty for evaluation_completed", () => {
    const event = {
      seq: 20,
      type: "evaluation_completed" as const,
      recommendations_emitted: 1,
      duration_ms: 42,
    } as unknown as TraceEvent;
    expect(highlightedNodeIds(event)).toEqual([]);
  });

  it("returns both rec IDs for preemption_resolved", () => {
    const event = {
      seq: 30,
      type: "preemption_resolved" as const,
      guideline_id: null,
      preempted_recommendation_id: "rec:statin-selective-grade-c",
      preempting_recommendation_id: "rec:accaha-statin-primary-prevention",
      edge_priority: 200,
      reason: "ACC/AHA takes precedence",
    } as unknown as TraceEvent;
    expect(highlightedNodeIds(event)).toEqual([
      "rec:statin-selective-grade-c",
      "rec:accaha-statin-primary-prevention",
    ]);
  });

  it("returns both rec IDs for cross_guideline_match", () => {
    const event = {
      seq: 31,
      type: "cross_guideline_match" as const,
      guideline_id: null,
      source_rec_id: "rec:kdigo-statin-for-ckd",
      target_rec_id: "rec:accaha-statin-secondary-prevention",
      nature: "intensity_reduction" as const,
      note: "KDIGO modifies intensity",
      source_guideline_id: "guideline:kdigo-ckd-2024",
      target_guideline_id: "guideline:acc-aha-cholesterol-2018",
    } as unknown as TraceEvent;
    expect(highlightedNodeIds(event)).toEqual([
      "rec:kdigo-statin-for-ckd",
      "rec:accaha-statin-secondary-prevention",
    ]);
  });
});

describe("eventSummary", () => {
  it("formats evaluation_started", () => {
    const event = {
      seq: 1,
      type: "evaluation_started" as const,
      patient_age_years: 55,
      patient_sex: "male",
      guidelines_in_scope: [],
    } as unknown as TraceEvent;
    expect(eventSummary(event)).toBe("55M");
  });

  it("formats female sex", () => {
    const event = {
      seq: 1,
      type: "evaluation_started" as const,
      patient_age_years: 78,
      patient_sex: "female",
      guidelines_in_scope: [],
    } as unknown as TraceEvent;
    expect(eventSummary(event)).toBe("78F");
  });

  it("formats predicate_evaluated", () => {
    const event = {
      seq: 5,
      type: "predicate_evaluated" as const,
      recommendation_id: "rec:test",
      path: ["all_of", 0],
      predicate: "age_between",
      args: { min: 40, max: 75 },
      inputs_read: [],
      result: "true" as const,
    } as unknown as TraceEvent;
    expect(eventSummary(event)).toBe("age_between → true");
  });

  it("formats risk_score_lookup with supplied value", () => {
    const event = {
      seq: 7,
      type: "risk_score_lookup" as const,
      score_name: "ascvd_10yr",
      resolution: "supplied" as const,
      supplied_value: 18.2,
    } as unknown as TraceEvent;
    expect(eventSummary(event)).toBe("ascvd_10yr: supplied (18.2)");
  });

  it("formats preemption_resolved", () => {
    const event = {
      seq: 30,
      type: "preemption_resolved" as const,
      guideline_id: null,
      preempted_recommendation_id: "rec:grade-c",
      preempting_recommendation_id: "rec:accaha-primary",
      edge_priority: 200,
      reason: "ACC/AHA wins",
    } as unknown as TraceEvent;
    expect(eventSummary(event)).toBe("rec:grade-c preempted by rec:accaha-primary");
  });

  it("formats cross_guideline_match", () => {
    const event = {
      seq: 31,
      type: "cross_guideline_match" as const,
      guideline_id: null,
      source_rec_id: "rec:kdigo-statin",
      target_rec_id: "rec:accaha-secondary",
      nature: "intensity_reduction" as const,
      note: "KDIGO modifies",
      source_guideline_id: "guideline:kdigo-ckd-2024",
      target_guideline_id: "guideline:acc-aha-cholesterol-2018",
    } as unknown as TraceEvent;
    expect(eventSummary(event)).toBe(
      "rec:kdigo-statin modifies rec:accaha-secondary (intensity_reduction)",
    );
  });
});

describe("eventTypeLabel", () => {
  it("returns human-readable labels", () => {
    expect(eventTypeLabel("predicate_evaluated")).toBe("Predicate Evaluated");
    expect(eventTypeLabel("recommendation_emitted")).toBe(
      "Recommendation Emitted",
    );
  });

  it("returns labels for cross-guideline event types", () => {
    expect(eventTypeLabel("preemption_resolved")).toBe("Preemption Resolved");
    expect(eventTypeLabel("cross_guideline_match")).toBe("Cross-Guideline Match");
    expect(eventTypeLabel("guideline_exited")).toBe("Guideline Exited");
  });

  it("returns raw type for unknown types", () => {
    expect(eventTypeLabel("unknown_type")).toBe("unknown_type");
  });
});

describe("clampIndex", () => {
  it("clamps below 0", () => {
    expect(clampIndex(-1, 10)).toBe(0);
  });

  it("clamps above max", () => {
    expect(clampIndex(15, 10)).toBe(9);
  });

  it("passes through valid index", () => {
    expect(clampIndex(5, 10)).toBe(5);
  });

  it("returns 0 for empty events", () => {
    expect(clampIndex(3, 0)).toBe(0);
  });
});

describe("deriveRecommendations", () => {
  it("returns the trace recommendations array", () => {
    const trace = {
      envelope: {
        spec_tag: "test",
        graph_version: "test",
        evaluator_version: "test",
        evaluation_time: "2026-01-01T00:00:00Z",
        patient_fingerprint: "abc",
      },
      events: [],
      recommendations: [
        {
          recommendation_id: "rec:test",
          status: "due" as const,
          evidence_grade: "B",
          reason: "test reason",
        },
      ],
    } as unknown as EvalTrace;
    const recs = deriveRecommendations(trace);
    expect(recs).toHaveLength(1);
    expect(recs[0].recommendation_id).toBe("rec:test");
  });

  it("returns empty for trace with no recommendations", () => {
    const trace = {
      envelope: {
        spec_tag: "test",
        graph_version: "test",
        evaluator_version: "test",
        evaluation_time: "2026-01-01T00:00:00Z",
        patient_fingerprint: "abc",
      },
      events: [],
      recommendations: [],
    } as unknown as EvalTrace;
    expect(deriveRecommendations(trace)).toEqual([]);
  });
});

// ── Dynamic subgraph expansion ──────────────────────────────────────

const G = "guideline:uspstf-statin-2022";

const sampleEvents = [
  {
    seq: 1,
    type: "evaluation_started",
    guideline_id: null,
    patient_age_years: 55,
    patient_sex: "male",
    guidelines_in_scope: [G],
  },
  {
    seq: 2,
    type: "guideline_entered",
    guideline_id: G,
    guideline_title: "USPSTF Statin 2022",
  },
  {
    seq: 3,
    type: "recommendation_considered",
    guideline_id: G,
    recommendation_id: "rec:statin-initiate-grade-b",
    recommendation_title: "Grade B",
    evidence_grade: "B",
    intent: "initiate",
    trigger: "primary_prevention",
  },
  {
    seq: 8,
    type: "strategy_considered",
    guideline_id: G,
    recommendation_id: "rec:statin-initiate-grade-b",
    strategy_id: "strategy:statin-moderate-intensity",
    strategy_name: "Moderate Intensity Statin",
  },
  {
    seq: 9,
    type: "action_checked",
    guideline_id: G,
    recommendation_id: "rec:statin-initiate-grade-b",
    strategy_id: "strategy:statin-moderate-intensity",
    action_node_id: "med:atorvastatin",
    action_entity_type: "Medication" as const,
    inputs_read: [],
    satisfied: false,
  },
  {
    seq: 10,
    type: "action_checked",
    guideline_id: G,
    recommendation_id: "rec:statin-initiate-grade-b",
    strategy_id: "strategy:statin-moderate-intensity",
    action_node_id: "med:rosuvastatin",
    action_entity_type: "Medication" as const,
    inputs_read: [],
    satisfied: false,
  },
] as unknown as TraceEvent[];

describe("subgraphFetchIds", () => {
  it("extracts unique rec and strategy IDs from full trace", () => {
    const { recIds, strategyIds } = subgraphFetchIds(sampleEvents);
    expect(recIds).toEqual(["rec:statin-initiate-grade-b"]);
    expect(strategyIds).toEqual(["strategy:statin-moderate-intensity"]);
  });

  it("returns empty for trace with no recs/strategies", () => {
    const { recIds, strategyIds } = subgraphFetchIds([sampleEvents[0]]);
    expect(recIds).toEqual([]);
    expect(strategyIds).toEqual([]);
  });
});

describe("visibleNodeIds", () => {
  it("shows only guideline at step 0", () => {
    const visible = visibleNodeIds(sampleEvents, 0);
    expect(visible.recIds.size).toBe(0);
    expect(visible.strategyIds.size).toBe(0);
    expect(visible.actionIds.size).toBe(0);
  });

  it("shows rec after recommendation_considered", () => {
    const { recIds, strategyIds, actionIds } = visibleNodeIds(sampleEvents, 2);
    expect(recIds.has("rec:statin-initiate-grade-b")).toBe(true);
    expect(strategyIds.size).toBe(0);
    expect(actionIds.size).toBe(0);
  });

  it("shows strategy after strategy_considered", () => {
    const { recIds, strategyIds, actionIds } = visibleNodeIds(sampleEvents, 3);
    expect(recIds.has("rec:statin-initiate-grade-b")).toBe(true);
    expect(strategyIds.has("strategy:statin-moderate-intensity")).toBe(true);
    expect(actionIds.size).toBe(0);
  });

  it("shows actions after action_checked", () => {
    const visible = visibleNodeIds(sampleEvents, 4);
    expect(visible.actionIds.has("med:atorvastatin")).toBe(true);
    expect(visible.actionIds.has("med:rosuvastatin")).toBe(false);
  });

  it("accumulates actions as more are checked", () => {
    const { actionIds } = visibleNodeIds(sampleEvents, 5);
    expect(actionIds.has("med:atorvastatin")).toBe(true);
    expect(actionIds.has("med:rosuvastatin")).toBe(true);
  });

  it("collapses back when stepping backward", () => {
    // At step 3 (strategy_considered), actions should not be visible.
    const { actionIds } = visibleNodeIds(sampleEvents, 3);
    expect(actionIds.size).toBe(0);
  });
});
