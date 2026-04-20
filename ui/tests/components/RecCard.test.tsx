import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import RecCard from "@/components/Eval/RecCard";
import type { RecCardData } from "@/lib/recListBuilder";

afterEach(() => {
  cleanup();
});

function makeCard(overrides: Partial<RecCardData> = {}): RecCardData {
  return {
    recommendation_id: "rec:test-1",
    guideline_id: "guideline:uspstf-statin-2022",
    domain: "USPSTF",
    guideline_title: "USPSTF 2022 Statin",
    status: "due",
    evidence_grade: "B",
    reason: "Start moderate-intensity statin therapy.",
    modifiers: [],
    action_summary: "Start Atorvastatin",
    actions: [],
    convergence: [],
    ...overrides,
  };
}

describe("RecCard", () => {
  it("renders domain badge", () => {
    render(
      <RecCard card={makeCard()} isHighlighted={false} onConvergenceClick={vi.fn()} />,
    );
    const badge = screen.getByTestId("domain-badge");
    expect(badge.textContent).toContain("USPSTF");
  });

  it("renders evidence grade pill", () => {
    render(
      <RecCard card={makeCard()} isHighlighted={false} onConvergenceClick={vi.fn()} />,
    );
    const pill = screen.getByTestId("grade-pill");
    expect(pill.textContent).toContain("Grade B");
  });

  it("renders ACC/AHA grade in COR format", () => {
    render(
      <RecCard
        card={makeCard({
          domain: "ACC_AHA",
          evidence_grade: "COR I",
        })}
        isHighlighted={false}
        onConvergenceClick={vi.fn()}
      />,
    );
    const pill = screen.getByTestId("grade-pill");
    expect(pill.textContent).toBe("COR I");
  });

  it("renders KDIGO grade without prefix", () => {
    render(
      <RecCard
        card={makeCard({
          domain: "KDIGO",
          evidence_grade: "1B",
        })}
        isHighlighted={false}
        onConvergenceClick={vi.fn()}
      />,
    );
    const pill = screen.getByTestId("grade-pill");
    expect(pill.textContent).toBe("1B");
  });

  it("renders action summary", () => {
    render(
      <RecCard
        card={makeCard({ action_summary: "Start Atorvastatin" })}
        isHighlighted={false}
        onConvergenceClick={vi.fn()}
      />,
    );
    expect(screen.getByText("Start Atorvastatin")).toBeDefined();
  });

  it("shows convergence badge when convergence entries exist", () => {
    const card = makeCard({
      convergence: [
        {
          entity_id: "med:atorvastatin",
          entity_type: "Medication",
          recommended_by: [
            { rec_id: "rec:test-1", guideline: "USPSTF 2022 Statin", domain: "USPSTF" },
            { rec_id: "rec:accaha-1", guideline: "ACC/AHA 2018 Cholesterol", domain: "ACC_AHA" },
          ],
        },
      ],
    });

    render(
      <RecCard card={card} isHighlighted={false} onConvergenceClick={vi.fn()} />,
    );
    const badge = screen.getByTestId("convergence-badge");
    expect(badge).toBeDefined();
    expect(badge.textContent).toContain("Also recommended by:");
    expect(badge.textContent).toContain("ACC/AHA 2018 Cholesterol");
  });

  it("does not show convergence badge when no convergence", () => {
    render(
      <RecCard card={makeCard()} isHighlighted={false} onConvergenceClick={vi.fn()} />,
    );
    expect(screen.queryByTestId("convergence-badge")).toBeNull();
  });

  it("calls onConvergenceClick with related rec IDs", () => {
    const handler = vi.fn();
    const card = makeCard({
      convergence: [
        {
          entity_id: "med:atorvastatin",
          entity_type: "Medication",
          recommended_by: [
            { rec_id: "rec:test-1", guideline: "USPSTF 2022 Statin", domain: "USPSTF" },
            { rec_id: "rec:accaha-1", guideline: "ACC/AHA 2018 Cholesterol", domain: "ACC_AHA" },
          ],
        },
      ],
    });

    render(
      <RecCard card={card} isHighlighted={false} onConvergenceClick={handler} />,
    );
    fireEvent.click(screen.getByTestId("convergence-badge"));
    expect(handler).toHaveBeenCalledWith(["rec:accaha-1"]);
  });

  it("applies highlight ring when isHighlighted is true", () => {
    render(
      <RecCard card={makeCard()} isHighlighted={true} onConvergenceClick={vi.fn()} />,
    );
    const el = screen.getByTestId("rec-card");
    expect(el.className).toContain("ring-amber-400");
  });

  it("expands actions on click", () => {
    const card = makeCard({
      actions: [
        { action_node_id: "med:atorvastatin", entity_type: "Medication", satisfied: false },
        { action_node_id: "med:rosuvastatin", entity_type: "Medication", satisfied: true },
      ],
    });

    render(
      <RecCard card={card} isHighlighted={false} onConvergenceClick={vi.fn()} />,
    );

    const expandBtn = screen.getByTestId("expand-actions");
    expect(expandBtn.textContent).toContain("Show 2 actions");

    fireEvent.click(expandBtn);
    const list = screen.getByTestId("action-list");
    expect(list.children).toHaveLength(2);
  });
});
