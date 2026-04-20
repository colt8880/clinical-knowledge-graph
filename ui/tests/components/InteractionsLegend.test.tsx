import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import InteractionsLegend from "@/components/InteractionsLegend";
import type { InteractionsResponse } from "@/lib/api/client";

afterEach(() => {
  cleanup();
});

const MOCK_DATA: InteractionsResponse = {
  guidelines: [
    { id: "uspstf-statin-2022", domain: "USPSTF", title: "USPSTF" },
    { id: "acc-aha-cholesterol-2018", domain: "ACC/AHA", title: "ACC/AHA" },
  ],
  recommendations: [
    {
      id: "rec:a",
      title: "Rec A",
      domain: "USPSTF",
      evidence_grade: "B",
      has_preemption_in: false,
      has_preemption_out: true,
      modifier_count: 0,
    },
    {
      id: "rec:b",
      title: "Rec B",
      domain: "ACC/AHA",
      evidence_grade: null,
      has_preemption_in: true,
      has_preemption_out: false,
      modifier_count: 0,
    },
  ],
  shared_entities: [],
  edges: [
    {
      type: "PREEMPTED_BY",
      source: "rec:a",
      target: "rec:b",
      edge_priority: 200,
      reason: "Test",
    },
  ],
};

describe("InteractionsLegend", () => {
  it("renders edge type filter buttons", () => {
    const onEdgeTypeChange = vi.fn();
    render(
      <InteractionsLegend
        data={MOCK_DATA}
        edgeTypeFilter="both"
        onEdgeTypeChange={onEdgeTypeChange}
        excludedPairs={new Set()}
        onTogglePair={vi.fn()}
      />,
    );

    expect(screen.getByTestId("edge-type-both")).toBeDefined();
    expect(screen.getByTestId("edge-type-preemption")).toBeDefined();
    expect(screen.getByTestId("edge-type-modifier")).toBeDefined();
  });

  it("calls onEdgeTypeChange when filter is clicked", () => {
    const onEdgeTypeChange = vi.fn();
    render(
      <InteractionsLegend
        data={MOCK_DATA}
        edgeTypeFilter="both"
        onEdgeTypeChange={onEdgeTypeChange}
        excludedPairs={new Set()}
        onTogglePair={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByTestId("edge-type-preemption"));
    expect(onEdgeTypeChange).toHaveBeenCalledWith("preemption");
  });

  it("renders summary counts", () => {
    render(
      <InteractionsLegend
        data={MOCK_DATA}
        edgeTypeFilter="both"
        onEdgeTypeChange={vi.fn()}
        excludedPairs={new Set()}
        onTogglePair={vi.fn()}
      />,
    );

    const summary = screen.getByTestId("interactions-summary");
    expect(summary.textContent).toContain("1 preemption");
    expect(summary.textContent).toContain("0 modifiers");
  });

  it("has proper accessibility roles", () => {
    render(
      <InteractionsLegend
        data={MOCK_DATA}
        edgeTypeFilter="both"
        onEdgeTypeChange={vi.fn()}
        excludedPairs={new Set()}
        onTogglePair={vi.fn()}
      />,
    );

    expect(screen.getByRole("radiogroup")).toBeDefined();
  });
});
