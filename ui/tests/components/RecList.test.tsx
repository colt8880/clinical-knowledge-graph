import { describe, it, expect, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import RecList from "@/components/Eval/RecList";
import type { EvalTrace } from "@/lib/eval/trace-nav";

afterEach(() => {
  cleanup();
});

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

describe("RecList", () => {
  it("shows empty message when no recs", () => {
    render(<RecList trace={makeTrace()} />);
    expect(screen.getByTestId("rec-list").textContent).toContain("No recommendations emitted");
  });

  it("renders rec cards for each recommendation", () => {
    const trace = makeTrace({
      recommendations: [
        {
          recommendation_id: "rec:a",
          guideline_id: "guideline:uspstf-statin-2022",
          status: "due",
          evidence_grade: "B",
          reason: "Rec A",
          modifiers: [],
        },
        {
          recommendation_id: "rec:b",
          guideline_id: "guideline:uspstf-statin-2022",
          status: "up_to_date",
          evidence_grade: "C",
          reason: "Rec B",
          modifiers: [],
        },
      ],
    });

    render(<RecList trace={trace} />);
    const cards = screen.getAllByTestId("rec-card");
    expect(cards).toHaveLength(2);
  });

  it("shows guideline count for multi-guideline traces", () => {
    const trace = makeTrace({
      recommendations: [
        {
          recommendation_id: "rec:uspstf-1",
          guideline_id: "guideline:uspstf-statin-2022",
          status: "due",
          evidence_grade: "B",
          reason: "USPSTF",
          modifiers: [],
        },
        {
          recommendation_id: "rec:accaha-1",
          guideline_id: "guideline:acc-aha-cholesterol-2018",
          status: "due",
          evidence_grade: "COR I",
          reason: "ACC/AHA",
          modifiers: [],
        },
      ],
    });

    render(<RecList trace={trace} />);
    expect(screen.getByTestId("rec-list").textContent).toContain("2 guidelines");
  });

  it("shows convergence detected label when convergence exists", () => {
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
          reason: "USPSTF",
          modifiers: [],
        },
        {
          recommendation_id: "rec:accaha-1",
          guideline_id: "guideline:acc-aha-cholesterol-2018",
          status: "due",
          evidence_grade: "COR I",
          reason: "ACC/AHA",
          modifiers: [],
        },
      ],
    });

    render(<RecList trace={trace} />);
    expect(screen.getByTestId("rec-list").textContent).toContain("Convergence detected");
  });

  it("highlights related cards on convergence badge click", () => {
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
          reason: "USPSTF",
          modifiers: [],
        },
        {
          recommendation_id: "rec:accaha-1",
          guideline_id: "guideline:acc-aha-cholesterol-2018",
          status: "due",
          evidence_grade: "COR I",
          reason: "ACC/AHA",
          modifiers: [],
        },
      ],
    });

    render(<RecList trace={trace} />);

    // Click convergence badge on one of the cards
    const badges = screen.getAllByTestId("convergence-badge");
    expect(badges.length).toBeGreaterThan(0);
    fireEvent.click(badges[0]);

    // After clicking, one of the other cards should have the highlight ring
    const cards = screen.getAllByTestId("rec-card");
    const highlighted = cards.filter((c) => c.className.includes("ring-amber-400"));
    expect(highlighted.length).toBeGreaterThan(0);
  });
});
