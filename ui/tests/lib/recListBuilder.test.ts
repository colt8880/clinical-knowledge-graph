import { describe, it, expect } from "vitest";
import { buildRecList, getDomain, getGuidelineTitle } from "@/lib/recListBuilder";
import type { EvalTrace } from "@/lib/eval/trace-nav";

// ── Helpers ────────────────────────────────────────────────────────

function makeTrace(overrides: Partial<EvalTrace> = {}): EvalTrace {
  return {
    envelope: {
      spec_tag: "test",
      graph_version: "test",
      evaluator_version: "test",
      evaluation_time: "2026-01-01T00:00:00Z",
      patient_fingerprint: "abc",
    },
    events: [],
    recommendations: [],
    recommendations_by_guideline: {},
    $defs: {} as EvalTrace["$defs"],
    ...overrides,
  };
}

// ── Tests ──────────────────────────────────────────────────────────

describe("buildRecList", () => {
  it("returns empty array for no recommendations", () => {
    const trace = makeTrace();
    expect(buildRecList(trace)).toEqual([]);
  });

  it("orders by guideline priority descending", () => {
    const trace = makeTrace({
      recommendations: [
        {
          recommendation_id: "rec:uspstf-1",
          guideline_id: "guideline:uspstf-statin-2022",
          status: "due",
          evidence_grade: "B",
          reason: "USPSTF rec",
          modifiers: [],
        },
        {
          recommendation_id: "rec:accaha-1",
          guideline_id: "guideline:acc-aha-cholesterol-2018",
          status: "due",
          evidence_grade: "B",
          reason: "ACC/AHA rec",
          modifiers: [],
        },
      ],
    });

    const cards = buildRecList(trace);
    // ACC/AHA (priority 200) should come before USPSTF (priority 100)
    expect(cards[0].guideline_id).toBe("guideline:acc-aha-cholesterol-2018");
    expect(cards[1].guideline_id).toBe("guideline:uspstf-statin-2022");
  });

  it("orders by evidence grade within same guideline priority", () => {
    const trace = makeTrace({
      recommendations: [
        {
          recommendation_id: "rec:low-grade",
          guideline_id: "guideline:uspstf-statin-2022",
          status: "due",
          evidence_grade: "C",
          reason: "Grade C",
          modifiers: [],
        },
        {
          recommendation_id: "rec:high-grade",
          guideline_id: "guideline:uspstf-statin-2022",
          status: "due",
          evidence_grade: "B",
          reason: "Grade B",
          modifiers: [],
        },
      ],
    });

    const cards = buildRecList(trace);
    expect(cards[0].recommendation_id).toBe("rec:high-grade");
    expect(cards[1].recommendation_id).toBe("rec:low-grade");
  });

  it("falls back to rec id for determinism", () => {
    const trace = makeTrace({
      recommendations: [
        {
          recommendation_id: "rec:zzz",
          guideline_id: "guideline:uspstf-statin-2022",
          status: "due",
          evidence_grade: "B",
          reason: "Z",
          modifiers: [],
        },
        {
          recommendation_id: "rec:aaa",
          guideline_id: "guideline:uspstf-statin-2022",
          status: "due",
          evidence_grade: "B",
          reason: "A",
          modifiers: [],
        },
      ],
    });

    const cards = buildRecList(trace);
    expect(cards[0].recommendation_id).toBe("rec:aaa");
    expect(cards[1].recommendation_id).toBe("rec:zzz");
  });

  it("detects convergence when two guidelines target the same entity", () => {
    const trace = makeTrace({
      events: [
        {
          seq: 1,
          type: "action_checked",
          guideline_id: "guideline:uspstf-statin-2022",
          recommendation_id: "rec:uspstf-1",
          strategy_id: "strat:u1",
          action_node_id: "med:atorvastatin",
          action_entity_type: "Medication",
          satisfied: false,
          cadence: null,
          lookback: null,
          inputs_read: [],
          note: null,
        },
        {
          seq: 2,
          type: "action_checked",
          guideline_id: "guideline:acc-aha-cholesterol-2018",
          recommendation_id: "rec:accaha-1",
          strategy_id: "strat:a1",
          action_node_id: "med:atorvastatin",
          action_entity_type: "Medication",
          satisfied: false,
          cadence: null,
          lookback: null,
          inputs_read: [],
          note: null,
        },
      ] as EvalTrace["events"],
      recommendations: [
        {
          recommendation_id: "rec:uspstf-1",
          guideline_id: "guideline:uspstf-statin-2022",
          status: "due",
          evidence_grade: "B",
          reason: "Start statin",
          modifiers: [],
        },
        {
          recommendation_id: "rec:accaha-1",
          guideline_id: "guideline:acc-aha-cholesterol-2018",
          status: "due",
          evidence_grade: "COR I",
          reason: "Start statin",
          modifiers: [],
        },
      ],
    });

    const cards = buildRecList(trace);
    // Both cards should have convergence entries
    const uspstfCard = cards.find((c) => c.recommendation_id === "rec:uspstf-1");
    const accahaCard = cards.find((c) => c.recommendation_id === "rec:accaha-1");

    expect(uspstfCard!.convergence).toHaveLength(1);
    expect(uspstfCard!.convergence[0].entity_id).toBe("med:atorvastatin");
    expect(uspstfCard!.convergence[0].recommended_by).toHaveLength(2);

    expect(accahaCard!.convergence).toHaveLength(1);
    expect(accahaCard!.convergence[0].entity_id).toBe("med:atorvastatin");
  });

  it("does not show convergence for single-guideline fixtures", () => {
    const trace = makeTrace({
      events: [
        {
          seq: 1,
          type: "action_checked",
          guideline_id: "guideline:uspstf-statin-2022",
          recommendation_id: "rec:uspstf-1",
          strategy_id: "strat:u1",
          action_node_id: "med:atorvastatin",
          action_entity_type: "Medication",
          satisfied: false,
          cadence: null,
          lookback: null,
          inputs_read: [],
          note: null,
        },
      ] as EvalTrace["events"],
      recommendations: [
        {
          recommendation_id: "rec:uspstf-1",
          guideline_id: "guideline:uspstf-statin-2022",
          status: "due",
          evidence_grade: "B",
          reason: "Start statin",
          modifiers: [],
        },
      ],
    });

    const cards = buildRecList(trace);
    expect(cards[0].convergence).toHaveLength(0);
  });

  it("excludes preempted recs from convergence detection", () => {
    const trace = makeTrace({
      events: [
        {
          seq: 1,
          type: "action_checked",
          guideline_id: "guideline:uspstf-statin-2022",
          recommendation_id: "rec:uspstf-1",
          strategy_id: "strat:u1",
          action_node_id: "med:atorvastatin",
          action_entity_type: "Medication",
          satisfied: false,
          cadence: null,
          lookback: null,
          inputs_read: [],
          note: null,
        },
        {
          seq: 2,
          type: "action_checked",
          guideline_id: "guideline:acc-aha-cholesterol-2018",
          recommendation_id: "rec:accaha-preempted",
          strategy_id: "strat:a1",
          action_node_id: "med:atorvastatin",
          action_entity_type: "Medication",
          satisfied: false,
          cadence: null,
          lookback: null,
          inputs_read: [],
          note: null,
        },
      ] as EvalTrace["events"],
      recommendations: [
        {
          recommendation_id: "rec:uspstf-1",
          guideline_id: "guideline:uspstf-statin-2022",
          status: "due",
          evidence_grade: "B",
          reason: "Start statin",
          modifiers: [],
        },
        {
          recommendation_id: "rec:accaha-preempted",
          guideline_id: "guideline:acc-aha-cholesterol-2018",
          status: "due",
          evidence_grade: "COR I",
          reason: "Preempted",
          modifiers: [],
          preempted_by: "rec:uspstf-1",
        },
      ],
    });

    const cards = buildRecList(trace);
    // No convergence because the ACC/AHA rec is preempted
    for (const card of cards) {
      expect(card.convergence).toHaveLength(0);
    }
  });

  it("builds action summary from trace events", () => {
    const trace = makeTrace({
      events: [
        {
          seq: 1,
          type: "action_checked",
          guideline_id: "guideline:uspstf-statin-2022",
          recommendation_id: "rec:uspstf-1",
          strategy_id: "strat:u1",
          action_node_id: "med:atorvastatin",
          action_entity_type: "Medication",
          satisfied: false,
          cadence: null,
          lookback: null,
          inputs_read: [],
          note: null,
        },
        {
          seq: 2,
          type: "action_checked",
          guideline_id: "guideline:uspstf-statin-2022",
          recommendation_id: "rec:uspstf-1",
          strategy_id: "strat:u1",
          action_node_id: "med:rosuvastatin",
          action_entity_type: "Medication",
          satisfied: false,
          cadence: null,
          lookback: null,
          inputs_read: [],
          note: null,
        },
      ] as EvalTrace["events"],
      recommendations: [
        {
          recommendation_id: "rec:uspstf-1",
          guideline_id: "guideline:uspstf-statin-2022",
          status: "due",
          evidence_grade: "B",
          reason: "Start statin",
          modifiers: [],
        },
      ],
    });

    const cards = buildRecList(trace);
    expect(cards[0].action_summary).toContain("Atorvastatin");
    expect(cards[0].action_summary).toContain("Rosuvastatin");
  });
});

describe("getDomain", () => {
  it("maps known guideline ids", () => {
    expect(getDomain("guideline:uspstf-statin-2022")).toBe("USPSTF");
    expect(getDomain("guideline:acc-aha-cholesterol-2018")).toBe("ACC_AHA");
    expect(getDomain("guideline:kdigo-ckd-2024")).toBe("KDIGO");
  });

  it("returns UNKNOWN for unmapped ids", () => {
    expect(getDomain("guideline:unknown")).toBe("UNKNOWN");
  });
});

describe("getGuidelineTitle", () => {
  it("maps known guideline ids", () => {
    expect(getGuidelineTitle("guideline:uspstf-statin-2022")).toBe("USPSTF 2022 Statin");
  });

  it("falls back to raw id for unknown guidelines", () => {
    expect(getGuidelineTitle("guideline:unknown")).toBe("guideline:unknown");
  });
});
