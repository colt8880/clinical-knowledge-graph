import { describe, it, expect } from "vitest";
import {
  highlightedNodeIds,
  eventSummary,
  eventTypeLabel,
  clampIndex,
  deriveRecommendations,
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
    } as TraceEvent;
    expect(highlightedNodeIds(event)).toEqual([]);
  });

  it("returns guideline_id for guideline_entered", () => {
    const event = {
      seq: 2,
      type: "guideline_entered" as const,
      guideline_id: "guideline:uspstf-statin-2022",
      guideline_title: "USPSTF Statin 2022",
    } as TraceEvent;
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
    } as TraceEvent;
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
    } as TraceEvent;
    expect(highlightedNodeIds(event)).toEqual(["med:atorvastatin"]);
  });

  it("returns strategy_id for strategy_considered", () => {
    const event = {
      seq: 8,
      type: "strategy_considered" as const,
      recommendation_id: "rec:statin-initiate-grade-b",
      strategy_id: "strategy:statin-moderate-intensity",
      strategy_name: "Moderate Intensity Statin",
    } as TraceEvent;
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
    } as TraceEvent;
    expect(highlightedNodeIds(event)).toEqual(["rec:statin-initiate-grade-b"]);
  });

  it("returns empty for evaluation_completed", () => {
    const event = {
      seq: 20,
      type: "evaluation_completed" as const,
      recommendations_emitted: 1,
      duration_ms: 42,
    } as TraceEvent;
    expect(highlightedNodeIds(event)).toEqual([]);
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
    } as TraceEvent;
    expect(eventSummary(event)).toBe("55M");
  });

  it("formats female sex", () => {
    const event = {
      seq: 1,
      type: "evaluation_started" as const,
      patient_age_years: 78,
      patient_sex: "female",
      guidelines_in_scope: [],
    } as TraceEvent;
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
    } as TraceEvent;
    expect(eventSummary(event)).toBe("age_between → true");
  });

  it("formats risk_score_lookup with supplied value", () => {
    const event = {
      seq: 7,
      type: "risk_score_lookup" as const,
      score_name: "ascvd_10yr",
      resolution: "supplied" as const,
      supplied_value: 18.2,
    } as TraceEvent;
    expect(eventSummary(event)).toBe("ascvd_10yr: supplied (18.2)");
  });
});

describe("eventTypeLabel", () => {
  it("returns human-readable labels", () => {
    expect(eventTypeLabel("predicate_evaluated")).toBe("Predicate Evaluated");
    expect(eventTypeLabel("recommendation_emitted")).toBe(
      "Recommendation Emitted",
    );
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
