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
  it("renders guideline selection chips", () => {
    render(
      <InteractionsLegend
        data={MOCK_DATA}
        edgeTypeFilter="both"
        onEdgeTypeChange={vi.fn()}
        selectedGuidelines={new Set()}
        onToggleGuideline={vi.fn()}
      />,
    );

    expect(screen.getByTestId("guideline-chip-USPSTF")).toBeDefined();
    expect(screen.getByTestId("guideline-chip-ACC/AHA")).toBeDefined();
    expect(screen.getByTestId("guideline-chip-KDIGO")).toBeDefined();
  });

  it("hides edge type filter until 2+ guidelines selected", () => {
    render(
      <InteractionsLegend
        data={MOCK_DATA}
        edgeTypeFilter="both"
        onEdgeTypeChange={vi.fn()}
        selectedGuidelines={new Set(["USPSTF"])}
        onToggleGuideline={vi.fn()}
      />,
    );

    expect(screen.queryByTestId("edge-type-both")).toBeNull();
  });

  it("shows edge type filter when 2+ guidelines selected", () => {
    render(
      <InteractionsLegend
        data={MOCK_DATA}
        edgeTypeFilter="both"
        onEdgeTypeChange={vi.fn()}
        selectedGuidelines={new Set(["USPSTF", "ACC/AHA"])}
        onToggleGuideline={vi.fn()}
      />,
    );

    expect(screen.getByTestId("edge-type-both")).toBeDefined();
    expect(screen.getByTestId("edge-type-preemption")).toBeDefined();
    expect(screen.getByTestId("edge-type-modifier")).toBeDefined();
  });

  it("calls onToggleGuideline when a chip is clicked", () => {
    const onToggle = vi.fn();
    render(
      <InteractionsLegend
        data={MOCK_DATA}
        edgeTypeFilter="both"
        onEdgeTypeChange={vi.fn()}
        selectedGuidelines={new Set()}
        onToggleGuideline={onToggle}
      />,
    );

    fireEvent.click(screen.getByTestId("guideline-chip-USPSTF"));
    expect(onToggle).toHaveBeenCalledWith("USPSTF");
  });

  it("has proper accessibility roles", () => {
    render(
      <InteractionsLegend
        data={MOCK_DATA}
        edgeTypeFilter="both"
        onEdgeTypeChange={vi.fn()}
        selectedGuidelines={new Set(["USPSTF", "ACC/AHA"])}
        onToggleGuideline={vi.fn()}
      />,
    );

    expect(screen.getByRole("radiogroup")).toBeDefined();
    expect(screen.getByRole("group")).toBeDefined();
  });
});
